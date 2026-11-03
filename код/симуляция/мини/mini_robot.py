"""Харви «Компакт мини» в симуляции целиком — так, как его увидит голова (Pi Zero 2 W).

Голова шлёт команду корпусу {"v": (вперёд мм/с, влево мм/с, поворот °/с), "pose": "stand" | "lie"}. Походка (`Walker`)
считает цели суставов и отправляет их сообщением `j` протокола link.py в настоящий `Spine` прошивки RP2350. Spine читает
имитации датчиков (mini_sensors), решает рефлексами, пускать ли движение, пишет цели на шины — и шлёт телеметрию.
Походка здесь заменяет будущий модуль походки головы.
"""
import math
from types import SimpleNamespace

import numpy as np

import harvey_mini as hm
import mini_sensors as ms
import edge  # noqa: E402 — из прошивки (ms.FIRMWARE)
import link
import pins
from spine import Spine

TABLE = (-0.30, 0.30, -0.30, 0.30)                 # столешница 60 × 60 см
TICK = 0.005                                       # проход главного цикла Spine ~5 мс (код/прошивка/rp2350/README.md)
SUB = round(TICK / hm.DT)
LIE_DZ = hm.CAD["rest_drop"] * hm.mm               # лечь: корпус ниже на 13 мм — пластины брюха на контакты
# латунные пластины на брюхе 40 × 12 мм (модели/мини/harvey_mini_parts.py: x −20…20, y = BELLY_Y ± 6), контакт Ø5:
# середина контакта должна быть не ближе 2,5 мм к краю пластины
PLATE_X, PLATE_Y = 20 - 2.5, 6 - 2.5
CFG = {"bat_low": pins.BAT_LOW_V, "bat_critical": pins.BAT_CRITICAL_V, "telemetry_ms": pins.TELEMETRY_MS,
       "edge_names": pins.EDGE_NAMES}


class Port:
    """USB между головой и RP2350: в одну сторону — команды, в другую — телеметрия."""

    def __init__(self):
        self.to_spine, self.from_spine = b"", bytearray()

    def read(self):
        data, self.to_spine = self.to_spine, b""
        return data

    def write(self, data):
        self.from_spine += data


class Pin:
    def __init__(self):
        self.level = 0

    def value(self, v=None):
        if v is None:
            return self.level
        self.level = v


class SimRobot:
    def __init__(self, table=TABLE, dock_pos=None, start=(0.0, 0.0, 0.0), hand=None):
        self.sim = hm.Mini(xml=ms.world_xml(table, dock_pos, hand))
        self.has_hand, self.dock_pos = hand is not None, dock_pos
        ms.place(self.sim, *start)
        self.sim.run(0.4, record=False)
        self.t, self.dz = 0.0, 0.0
        self.targets = SimpleNamespace(q=dict(self.sim.q))     # цели суставов головы; Spine решает, дойдут ли они до шин
        self.walker = hm.Walker(self.targets)
        self.port, self.reader = Port(), link.LineReader()
        self.tel, self.events, self.lift_events = {}, [], []
        bus = ms.SimBus(self.sim)
        tof = edge.EdgeArray(None, [Pin() for _ in pins.EDGE_NAMES], pins.EDGE_NAMES, pins.EDGE_ADDR0,
                             make=ms.tof_factory(self.sim))
        beacon = ms.SimBeacon(self.sim, ms.led_world(dock_pos)) if dock_pos is not None else None
        self.spine = Spine(self.port, {"A": bus, "B": bus, "C": bus}, edge=tof, imu=ms.SimImu(self.sim),
                           ina=ms.SimIna(self.charging), beacon=beacon, cfg=CFG, clock=lambda: round(self.t * 1000))
        self._send({"t": "cal"})
        self._tick()

    # ---------- голова ↔ RP2350 ----------
    def _send(self, msg):
        self.port.to_spine += link.encode(msg)

    def _tick(self):
        self.spine.step()
        self.events = []
        for msg in self.reader.feed(bytes(self.port.from_spine)):
            if msg["t"] == "tel":
                self.tel = msg
            elif msg["t"] == "ev":
                self.events.append(msg["ev"])
        self.port.from_spine.clear()

    def step(self, cmd):
        """Один проход 5 мс: походка → `j` → Spine → физика."""
        vx, vy, wz = cmd.get("v", (0, 0, 0))
        dz_t = LIE_DZ if cmd.get("pose") == "lie" else 0.0
        v = np.array([vx / 1000, vy / 1000, math.radians(wz)])
        for _ in range(SUB):
            self.dz += float(np.clip(dz_t - self.dz, -0.02 * hm.DT, 0.02 * hm.DT))
            self.walker.step(v, self.dz)
        vel = self.walker.vel
        q = {ms.SERVO_IDS[k]: ms.to_pos(a) for k, a in self.targets.q.items()}
        self._send(link.joints(q, (vel[0] * 1000, vel[1] * 1000, math.degrees(vel[2]))))
        for _ in range(SUB):
            self.sim.step(False)
        self.t += TICK
        self._tick()

    # ---------- что видит голова кроме RP2350 ----------
    def vision(self):
        """Что нашла бы камера: рука и метка станции (заглушка разбора кадра на ПК или голове)."""
        return {"hand": ms.see_hand(self.sim) if self.has_hand else None,
                "dock": ms.see_tag(self.sim, self.dock_pos) if self.dock_pos is not None else None}

    def charging(self):
        """Оба контакта прижаты к брюху и каждый — под своей латунной пластиной (касание пластикового дна не заряжает)."""
        if self.dock_pos is None:
            return False
        m, d = self.sim.m, self.sim.d
        for k, y in enumerate(hm.CAD["belly_y"]):
            pogo = m.geom(f"pogo{k}").id
            px, py, _ = self.sim.to_body(d.geom_xpos[pogo]) * 1000
            if abs(px) > PLATE_X or abs(py - y) > PLATE_Y or hm.contact_force(m, d, m.geom("body").id, pogo) <= 0.3:
                return False
        return True

    # ---------- для проверок ----------
    def pose(self):
        tb = self.sim.d.body("torso")
        q = tb.xquat
        yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
        return float(tb.xpos[0]), float(tb.xpos[1]), math.degrees(yaw)

    def on_table(self):
        d = self.sim.d
        return all(d.geom(f"{n}_foot").xpos[2] > -0.01 for n in hm.MOUNTS) and d.body("torso").xpos[2] > 0

    def lift(self, sec):
        """Поднять рукой: сила вверх за корпус 1,5 веса робота."""
        tid = self.sim.m.body("torso").id
        self.sim.d.xfrc_applied[tid, 2] = 1.5 * float(sum(self.sim.m.body_mass)) * 9.81
        self.lift_events = []
        for _ in range(int(sec / TICK)):
            self.step({"v": (0, 0, 0), "pose": "stand"})
            self.lift_events += self.events
        self.sim.d.xfrc_applied[tid, 2] = 0.0
