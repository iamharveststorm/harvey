"""Датчики и шины «Компакт мини» в MuJoCo — для настоящей прошивки RP2350 (код/прошивка/rp2350).

Имитации повторяют интерфейсы устройств, которые ждёт `Spine`: датчик края — как драйвер VL53L4CD для `EdgeArray(make=…)`,
IMU — `read() → (ускорение g, вращение °/с)`, INA226 — `volts()/amps()`, маяк — `take() → (слева, справа)`, шины —
`sync_write / release_all`. Так в симуляции работают edge.py, reflex.py, beacon.py, imu_events.py и link.py без правок.

Числа — из документы/:
- TSAL6200: сила излучения 72 мВт/ср (тип.) при 100 мА, угол половинной силы ±17° (стр. 2);
- TSOP382: порог 0,25 мВт/м² (NEC, макс.), предел 30 Вт/м², половинная дальность ±45° (стр. 2–3);
- маяк: пик 105 мА, 508 пачек/с (схемы/README.md, «Станция»).
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
IE_MW_SR = 72.0 * 105 / 100                         # сила излучения при пике 105 мА, мВт/ср
N_LED = math.log(0.5) / math.log(math.cos(math.radians(17)))   # cos^n: половина силы на ±17°
N_RX = 4                                            # чувствительность ∝ cos⁴: половинная дальность на ±45° (дальность ∝ √E)
EE_MIN, EE_MAX = 0.25, 30000.0                      # мВт/м²
BURSTS = round(508 * 0.1)                           # пачек за окно 100 мс
LED = (0.144, 0.0, 0.049)                           # ИК-светодиод в стенке башенки от центра площадки (CAD: DOCK_LED)
IR_Y, IR_Z, IR_SPLAY = 0.022, -0.006, math.radians(30)   # как ir_axis в модели/мини/harvey_mini_parts.py


def led_world(dock_pos):
    return np.array([dock_pos[0] + LED[0], dock_pos[1] + LED[1], LED[2]])


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
    a = sg * IR_SPLAY
    return (hm.BX1 + 0.002 + 0.0048 * math.cos(a), sg * IR_Y + 0.0048 * math.sin(a), IR_Z), (math.cos(a), math.sin(a), 0.0)


class SimBeacon:
    def __init__(self, sim, led):
        self.sim, self.led = sim, np.asarray(led)

    def _sees(self, sg):
        p, ax = _body_ray(self.sim, *receivers(sg))
        to_led = self.led - p
        r = float(np.linalg.norm(to_led))
        dist, _ = _ray(self.sim, p, to_led / r, SOLID, -1)
        if 0 <= dist < r - 0.006:                       # луч упёрся во что-то раньше светодиода (светодиод в стенке 4 мм)
            return False
        phi = math.acos(max(-1.0, min(1.0, float(np.dot(to_led / r, ax)))))
        return receiver_sees(irradiance(self.led, p), phi)

    def take(self):
        return tuple(BURSTS if self._sees(sg) else 0 for sg in (1, -1))


# ---------- шины приводов ----------
LEG_LIMB = {"LF": 1, "LM": 2, "LB": 3, "RF": 4, "RM": 5, "RB": 6}       # схемы/README.md «Номера приводов»
SERVO_IDS = {f"{n}_{j}": 10 * k + i for n, k in LEG_LIMB.items() for i, j in enumerate("cfk", 1)}
SERVO_IDS.update({f"{s}_{j}": 10 * k + i for s, k in (("L", 7), ("R", 8)) for i, j in enumerate("ypeg", 1)})
SERVO_IDS.update({"L_s": 91, "R_s": 92})
JOINT_OF = {v: k for k, v in SERVO_IDS.items()}
STEPS = 4096                                        # позиций на оборот; 2048 — ноль сустава (предварительно: нули задаются при сборке)


def to_pos(rad):
    return round(2048 + rad * STEPS / (2 * math.pi))


def to_rad(pos):
    return (pos - 2048) * 2 * math.pi / STEPS


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


# метка AprilTag 30 × 30 мм в окне башенки (CAD dock_tower: окно x 139,5…141, y ±16, z 14…46 от центра площадки);
# смотрит по −x. Предварительно: читается, если камера видит её не круче 70° к нормали; точность позы не моделируется
TAG = (0.140, 0.0, 0.030)
TAG_MAX_ANGLE = math.radians(70)


def see_tag(sim, dock_pos):
    """{"x_mm", "y_mm", "yaw_deg"} — где корпус в системе станции (0 — над контактами, x — к башенке), если метка в кадре."""
    target = np.array([dock_pos[0] + TAG[0], dock_pos[1] + TAG[1], TAG[2]])
    seen = _in_frame(sim, target)
    if seen is None:
        return None
    to_cam = seen[2] - target
    if -to_cam[0] / np.linalg.norm(to_cam) < math.cos(TAG_MAX_ANGLE):
        return None
    if _first_body(sim, seen[2], target, seen[1]) not in (None, 0):          # 0 — мир: станция вкопана в мир
        return None
    tb = sim.d.body("torso"); q = tb.xquat
    yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
    return {"x_mm": round((tb.xpos[0] - dock_pos[0]) * 1000, 1), "y_mm": round((tb.xpos[1] - dock_pos[1]) * 1000, 1),
            "yaw_deg": round(math.degrees(yaw), 1)}


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
