"""Датчики и шины «Компакт мини» в MuJoCo — для настоящей прошивки RP2350 (код/прошивка/rp2350).

Имитации повторяют интерфейсы устройств, которые ждёт `Spine`: датчик края — как драйвер VL53L4CD для `EdgeArray(make=…)`,
IMU — `read() → (ускорение g, вращение °/с)`, INA226 — `volts()/amps()`, маяк — `take() → (слева, справа)`, шины —
`sync_write / release_all`. Так в симуляции работают edge.py, reflex.py, beacon.py, imu_events.py и link.py без правок.

Числа — из документы/:
- TSAL6200: сила излучения 72 мВт/ср (тип.) при 100 мА, угол половинной силы ±17° (стр. 2);
- TSOP382: порог 0,25 мВт/м² (NEC, макс.), предел 30 Вт/м², половинная дальность ±45° (стр. 2–3);
- маяк: два светодиода по очереди, 333 пачки/с каждый (код/прошивка/станция/beacon_station.py); пик ~110 мА.
ПРЕДВАРИТЕЛЬНО: угловые кривые — cos^n по этим точкам, а не по рисункам даташитов; сила излучения при 105 мА — линейно
от 100 мА. Датчик края — один луч, а у VL53L4CD конус 18°. Проверить на стенде.
"""
import math
import sys
from pathlib import Path

import mujoco
import numpy as np

import harvey_mini as hm


def _firmware_dir():
    for base in (Path(__file__).absolute(), Path(__file__).resolve()):
        p = base.parents[2] / "прошивка" / "rp2350"
        if (p / "spine.py").exists():
            return p
    raise FileNotFoundError("не найдена код/прошивка/rp2350")


FIRMWARE = _firmware_dir()
if str(FIRMWARE) not in sys.path:
    sys.path.insert(0, str(FIRMWARE))
import vl53l4cd  # noqa: E402

SOLID = np.array([1, 1, 0, 0, 0, 0], np.uint8)       # лучи видят группы 0 (мир) и 1 (физика робота и станции); 2 — только картинка

# ---------- датчики края VL53L4CD (порядок pins.EDGE_NAMES: FL, FR, BL, BR, L, R) ----------
# как в harvey_mini_teleop.edge_seen: у дна, передние и задние смотрят вниз 2,3 : 1, боковые положе — 3,5 : 1
_ZS = hm.BZ0 + 0.0065
EDGE_RAYS = [((hm.BX1 + 0.002, 0.009, _ZS), (2.3, 0, -1)), ((hm.BX1 + 0.002, -0.009, _ZS), (2.3, 0, -1)),
             ((hm.BX0 - 0.002, 0.009, _ZS), (-2.3, 0, -1)), ((hm.BX0 - 0.002, -0.009, _ZS), (-2.3, 0, -1)),
             ((-0.020, hm.BY1 + 0.002, _ZS), (0, 3.5, -1)), ((-0.020, hm.BY0 - 0.002, _ZS), (0, -3.5, -1))]
TOF_RANGE = 1.3                                    # м: VL53L4CD — до 1300 мм (даташит, стр. 1)


def _body_ray(sim, o, v):
    tb = sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
    return tb.xpos + R @ np.array(o), R @ (np.array(v, float) / np.linalg.norm(v))


def _ray(sim, o, v, groups=SOLID, exclude=None):
    gid = np.zeros(1, np.int32)
    ex = sim.m.body("torso").id if exclude is None else exclude
    return mujoco.mj_ray(sim.m, sim.d, o, v, groups, 1, ex, gid), int(gid[0])


class SimTof:
    def __init__(self, sim, index):
        self.sim, self.index, self.addr = sim, index, vl53l4cd.DEFAULT_ADDR

    def set_address(self, a):
        self.addr = a

    def init(self, budget_ms=20):
        pass

    def start(self):
        pass

    def ready(self):
        return True

    def measure(self):
        o, v = _body_ray(self.sim, *EDGE_RAYS[self.index])
        dist, _ = _ray(self.sim, o, v)
        if dist < 0 or dist > TOF_RANGE:
            return 0, vl53l4cd.SIGNAL_TOO_WEAK
        return round(dist * 1000), vl53l4cd.VALID


def tof_factory(sim):
    """make для EdgeArray: каждый вызов — следующий датчик по порядку EDGE_RAYS."""
    made = []

    def make(_i2c):
        made.append(SimTof(sim, len(made) % len(EDGE_RAYS)))
        return made[-1]
    return make


# ---------- IMU BMI270 (в центре корпуса — предварительно, место на плате ещё не выбрано) ----------
class SimImu:
    def __init__(self, sim):
        self.sim = sim

    def read(self):
        d = self.sim.d
        acc = d.sensor("acc").data / 9.81
        gyr = np.degrees(d.sensor("gyr").data)
        return tuple(float(a) for a in acc), tuple(float(g) for g in gyr)


# ---------- INA226: батарея (предварительно: 7,4 В; разряд +1 А, заряд −0,5 А) ----------
class SimIna:
    def __init__(self, charging):
        self.charging = charging

    def volts(self):
        return 7.4

    def amps(self):
        return -0.5 if self.charging() else 1.0


# ---------- ИК-маяк: TSAL6200 на станции, 2 × TSOP38238 у передней стенки ----------
IE_MW_SR = 72.0 * 110 / 100                         # сила излучения при пике ~110 мА, мВт/ср
N_LED = math.log(0.5) / math.log(math.cos(math.radians(17)))   # cos^n: половина силы на ±17°
N_RX = 4                                            # чувствительность ∝ cos⁴: половинная дальность на ±45° (дальность ∝ √E)
EE_MIN, EE_MAX = 0.25, 30000.0                      # мВт/м²
BURSTS = round(333 * 0.1)                           # пачек одного светодиода за окно 100 мс
# светодиоды в стенке башенки у самого низа, по бокам перегородки (от центра площадки, м): левый — +y
LEDS = {"L": (0.144, 0.0035, 0.012), "R": (0.144, -0.0035, 0.012)}   # CAD: DOCK_LEDS
IR_Y, IR_Z, IR_SPLAY = 0.022, -0.006, math.radians(30)   # как ir_axis в модели/мини/harvey_mini_parts.py
IR_C_Z = 0.0                                        # центральный приёмник — под объективом камеры (CAD: IR_C_Z)


def leds_world(dock_pos):
    return {k: np.array([dock_pos[0] + v[0], dock_pos[1] + v[1], v[2]]) for k, v in LEDS.items()}


def receiver_sees(ee, phi):
    """Приёмник видит пачки: облучённость с учётом угла phi к его оси выше порога и не выше предела."""
    if abs(phi) >= math.pi / 2:
        return False
    return EE_MIN <= ee * math.cos(phi) ** N_RX and ee <= EE_MAX


def irradiance(led, p):
    """Облучённость, мВт/м², от светодиода (смотрит по −x, к роботу) в точке p."""
    v = np.asarray(p) - led
    r = float(np.linalg.norm(v))
    cos_t = -v[0] / r
    return 0.0 if cos_t <= 0 else IE_MW_SR * cos_t ** N_LED / (r * r)


def receivers(sg):
    """(точка, ось) приёмника: sg = 1 — слева, 0 — по центру (под камерой, смотрит вперёд), −1 — справа."""
    if sg == 0:
        return (hm.BX1 + 0.002 + 0.0048, 0.0, IR_C_Z), (1.0, 0.0, 0.0)
    a = sg * IR_SPLAY
    return (hm.BX1 + 0.002 + 0.0048 * math.cos(a), sg * IR_Y + 0.0048 * math.sin(a), IR_Z), (math.cos(a), math.sin(a), 0.0)


class SimBeacon:
    """Два светодиода станции и три приёмника Харви; тень перегородки и всего прочего — лучом MuJoCo."""

    def __init__(self, sim, dock_pos):
        self.sim, self.leds = sim, leds_world(dock_pos)

    def _sees(self, sg, led):
        p, ax = _body_ray(self.sim, *receivers(sg))
        to_led = led - p
        r = float(np.linalg.norm(to_led))
        dist, _ = _ray(self.sim, p, to_led / r, SOLID, -1)
        if 0 <= dist < r - 0.006:                       # луч упёрся во что-то раньше светодиода (светодиод в стенке 4 мм)
            return False
        phi = math.acos(max(-1.0, min(1.0, float(np.dot(to_led / r, ax)))))
        return receiver_sees(irradiance(led, p), phi)

    def take(self):
        """((слева L, R), (по центру L, R), (справа L, R)) — как Beacon.take в прошивке."""
        return tuple(tuple(BURSTS if self._sees(sg, self.leds[k]) else 0 for k in "LR") for sg in (1, 0, -1))


# ---------- шины приводов ----------
from harvey_head.servos import JOINT_OF, SERVO_IDS, to_pos, to_rad  # noqa: E402,F401 — номера и позиции — как у головы


class SimBus:
    """Одна шина на все ID. Запись цели снова включает момент — так считает Spine (relaxed = False); проверить на стенде."""

    def __init__(self, sim):
        self.sim = sim

    def sync_write(self, reg, values):
        if reg[0] != 42:
            return
        for sid, pos in values.items():
            self.sim.q[JOINT_OF[sid]] = to_rad(pos)
        self.sim.relaxed = False

    def release_all(self):
        self.sim.relaxed = True


# ---------- «зрение»: где рука в кадре камеры (заглушка ПК) ----------
CAM = (0.0662, 0.0, 0.0085)                         # harvey_mini.CAMERA
CAM_HALF_H, CAM_HALF_V, CAM_RANGE = math.radians(50), math.radians(33.5), 0.6


def _in_frame(sim, target):
    """Точка target (мир) в кадре камеры и ближе CAM_RANGE: (направление в кадре °, угол места °, расстояние м, камера)."""
    tb = sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
    cam = tb.xpos + R @ np.array(CAM)
    rel = R.T @ (np.asarray(target) - cam)
    r = float(np.linalg.norm(rel))
    bearing, elev = math.atan2(rel[1], rel[0]), math.atan2(rel[2], math.hypot(rel[0], rel[1]))
    if rel[0] <= 0 or abs(bearing) > CAM_HALF_H or abs(elev) > CAM_HALF_V or r > CAM_RANGE:
        return None
    return bearing, r, cam


def _first_body(sim, cam, target, r):
    _, gid = _ray(sim, cam, (np.asarray(target) - cam) / r, SOLID)
    return sim.m.geom_bodyid[gid] if gid >= 0 else None


def see_hand(sim, body="hand"):
    """{"bearing_deg": + — слева, "dist_mm"} руки, если она в кадре, ближе 60 см и ничем не закрыта; иначе None."""
    target = sim.d.body(body).xpos
    seen = _in_frame(sim, target)
    if seen is None or _first_body(sim, seen[2], target, seen[1]) != sim.m.body(body).id:
        return None
    return {"bearing_deg": round(math.degrees(seen[0]), 1), "dist_mm": round(seen[1] * 1000)}


# метка AprilTag 30 × 30 мм в окне башенки (над перегородкой маяка); смотрит по −x.
# Предварительно: читается, если камера видит её не круче 70° к нормали. Как и harvey_head/dock_tag.py, даёт только
# направление и расстояние: угол, под которым видна маленькая метка, камера на деле не различает
TAG = (0.140, 0.0, 0.048)                           # CAD: окно метки z 33…63 мм
TAG_MAX_ANGLE = math.radians(70)


def see_tag(sim, dock_pos):
    """{"bearing_deg": + — слева, "dist_mm": по столу от центра корпуса} до метки, если она в кадре и видна; иначе None."""
    target = np.array([dock_pos[0] + TAG[0], dock_pos[1] + TAG[1], TAG[2]])
    seen = _in_frame(sim, target)
    if seen is None:
        return None
    to_cam = seen[2] - target
    if -to_cam[0] / np.linalg.norm(to_cam) < math.cos(TAG_MAX_ANGLE):
        return None
    if _first_body(sim, seen[2], target, seen[1]) not in (None, 0):          # 0 — мир: станция вкопана в мир
        return None
    if _ray(sim, seen[2], (target - seen[2]) / seen[1], SOLID)[0] < seen[1] - 0.005:   # перегородка или что-то ещё
        return None
    rel = sim.to_body(target)
    return {"bearing_deg": round(math.degrees(math.atan2(rel[1], rel[0])), 2), "dist_mm": round(math.hypot(rel[0], rel[1]) * 1000, 1)}


# ---------- мир ----------
IMU_XML = '<site name="imu" pos="0 0 0" size="0.002"/>'
SENSORS_XML = '<sensor><accelerometer name="acc" site="imu"/><gyro name="gyr" site="imu"/></sensor>'


def hand_xml(pos):
    """Ладонь на столе: 90 × 80 × 25 мм, двигается тестом (mocap)."""
    return (f'<body name="hand" mocap="true" pos="{pos[0]} {pos[1]} 0.0125">'
            f'<geom name="hand_g" type="box" size="0.045 0.04 0.0125" rgba=".9 .75 .65 1"/></body>')


def world_xml(table, dock_pos=None, hand_pos=None):
    world = hm.table_xml(*table) + (hand_xml(hand_pos) if hand_pos is not None else "")
    xml = hm.build_xml(visual=False, world_xml=world, dock=dock_pos is not None, dock_pos=dock_pos)
    xml = xml.replace('<geom name="body" type="box"', IMU_XML + '<geom name="body" type="box"', 1)
    return xml.replace("</actuator>", "</actuator>" + SENSORS_XML, 1)


def place(sim, x, y, yaw_deg):
    """Поставить корпус в (x, y) с курсом yaw_deg, не меняя высоты и суставов."""
    m, d = sim.m, sim.d
    j = m.body("torso").jntadr[0]
    qa, va = m.jnt_qposadr[j], m.jnt_dofadr[j]
    h = math.radians(yaw_deg)
    d.qpos[qa:qa + 2] = (x, y)
    d.qpos[qa + 3:qa + 7] = (math.cos(h / 2), 0, 0, math.sin(h / 2))
    d.qvel[va:va + 6] = 0
    mujoco.mj_forward(m, d)
