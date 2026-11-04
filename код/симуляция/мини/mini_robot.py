"""Харви «Компакт мини» в симуляции целиком — так, как его увидит голова (Pi Zero 2 W).

Голова шлёт цели суставов сообщением `j` протокола link.py в настоящий `Spine` прошивки RP2350. Spine читает имитации
датчиков (mini_sensors), решает рефлексами, пускать ли движение, пишет цели на шины — и шлёт телеметрию.
Два способа вести робота:
- `step(cmd)` — команда корпусу {"v": (мм/с, мм/с, °/с), "pose": …} → походка головы (harvey_head/gait.py) → `j`;
- `link()` — порт для настоящей головы (harvey_head/head.py: Head + Body), как USB на роботе; тогда `physics()`.
"""
import math

import harvey_mini as hm
import mini_sensors as ms
import edge  # noqa: E402 — из прошивки (ms.FIRMWARE)
import link
import pins
from harvey_head import servos
from spine import Spine

TABLE = (-0.30, 0.30, -0.30, 0.30)                 # столешница 60 × 60 см
TICK = 0.005                                       # проход главного цикла Spine ~5 мс (код/прошивка/rp2350/README.md)
SUB = round(TICK / hm.DT)
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


class HeadLink:
    """Как SpineLink головы (harvey_head/links.py): poll — сообщения RP2350, send — сообщение в RP2350."""

    def __init__(self, robot):
        self.robot = robot

    def poll(self, now):
        out, self.robot.inbox = self.robot.inbox, []
        return out

    def send(self, msg):
        self.robot._send(msg)
        return True


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
        self.t = 0.0
        self.gait = hm.HG.Gait(hm.GEO)
        self.port, self.reader = Port(), link.LineReader()
        self.tel, self.events, self.lift_events, self.inbox = {}, [], [], []
        bus = ms.SimBus(self.sim)
        tof = edge.EdgeArray(None, [Pin() for _ in pins.EDGE_NAMES], pins.EDGE_NAMES, pins.EDGE_ADDR0,
                             make=ms.tof_factory(self.sim), nominal=pins.EDGE_NOMINAL_MM)
        beacon = ms.SimBeacon(self.sim, dock_pos) if dock_pos is not None else None
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
            self.inbox.append(msg)
            if msg["t"] == "tel":
                self.tel = msg
            elif msg["t"] == "ev":
                self.events.append(msg["ev"])
        self.port.from_spine.clear()

    def step(self, cmd):
        """Один проход 5 мс: походка головы → `j` → Spine → физика."""
        self._send(servos.message(self.gait.step(cmd, TICK), self.gait.velocity()))
        self.physics()

    def physics(self):
        """5 мс физики и проход Spine."""
        for _ in range(SUB):
            self.sim.step(False)
        self.t += TICK
        self._tick()
        self.inbox = self.inbox[-200:]

    def link(self):
        return HeadLink(self)

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
        return bool(all(d.geom(f"{n}_foot").xpos[2] > -0.01 for n in hm.MOUNTS) and d.body("torso").xpos[2] > 0)

    def lift(self, sec):
        """Поднять рукой: сила вверх за корпус 1,5 веса робота."""
        tid = self.sim.m.body("torso").id
        self.sim.d.xfrc_applied[tid, 2] = 1.5 * float(sum(self.sim.m.body_mass)) * 9.81
        self.lift_events = []
        for _ in range(int(sec / TICK)):
            self.step({"v": (0, 0, 0), "pose": "stand"})
            self.lift_events += self.events
        self.sim.d.xfrc_applied[tid, 2] = 0.0
