"""Имитация шины с приводами Feetech — чтобы прогнать скрипт стенда без железа.
Физика упрощённая: скорость по паспорту, упор, нагрузка, нагрев корпуса. Для мини — нога из трёх приводов,
которая давит стопой в весы (FakeLegBus)."""
from __future__ import annotations

import math
import random
import time

from . import sts

# размеры регистров, которые имитация отдаёт при блочном чтении
_REG_SIZE = {r[0]: r[1] for r in (sts.MODEL, sts.ID, sts.TORQUE_ENABLE, sts.ACCEL, sts.GOAL_POS, sts.GOAL_SPEED,
                                  sts.TORQUE_LIMIT, sts.LOCK, sts.PRESENT_POS, sts.PRESENT_SPEED, sts.PRESENT_LOAD,
                                  sts.PRESENT_VOLT, sts.PRESENT_TEMP, sts.MOVING, sts.PRESENT_CURRENT)}


class FakeServo:
    def __init__(self, sid: int, clock, profile: sts.Profile = sts.PROFILES["sts3215"]):
        self.id, self.clock, self.p = sid, clock, profile
        model = profile.model if profile.model is not None else 2312          # «неизвестная» модель для мини
        self.mem = {sts.MODEL[0]: model, sts.TORQUE_ENABLE[0]: 0, sts.TORQUE_LIMIT[0]: 1000,
                    sts.GOAL_POS[0]: 2048, sts.GOAL_SPEED[0]: 0, sts.ACCEL[0]: 0, sts.LOCK[0]: 1}
        self.raw, self.t, self.temp = 2048.0 + random.uniform(-300, 300), clock(), 26.0
        self.offset = 0.0                         # поправка середины (адрес 40 ← 128)
        self.volt = profile.volt
        self.block_at: int | None = None          # упор (рычаг на весах)
        self.ext_load_frac = 0.0                  # постоянная внешняя нагрузка (груз на рычаге), доля от упора
        self.load_frac = 0.0
        self.contact_frac = 0.0                   # нагрузка от упора стопы в весы (ставит FakeLegBus)
        self.vmax_free = 60.0 / profile.t90_spec * 90.0 / 60.0 / sts.DEG_PER_STEP     # шагов/с без нагрузки

    @property
    def pos(self) -> float:
        return self.raw - self.offset

    @pos.setter
    def pos(self, v: float) -> None:
        self.raw = v + self.offset

    def current(self) -> float:
        if not self.mem[sts.TORQUE_ENABLE[0]]:
            return 0.006
        return self.p.idle_a + self.load_frac * self.p.stall_a

    def step(self) -> None:
        now = self.clock()
        dt, self.t = now - self.t, now
        if dt <= 0:
            return
        load = max(self.ext_load_frac, self.contact_frac if self.mem[sts.TORQUE_ENABLE[0]] else 0.0)
        if self.mem[sts.TORQUE_ENABLE[0]]:
            goal = self.mem[sts.GOAL_POS[0]]
            vmax = self.vmax_free * self.volt / self.p.volt * max(0.0, 1.0 - load)
            sp = self.mem[sts.GOAL_SPEED[0]]
            if sp:
                vmax = min(vmax, sp)
            d = goal - self.pos
            step = max(-vmax * dt, min(vmax * dt, d))
            new = self.pos + step
            if self.block_at is not None and ((self.pos <= self.block_at <= new) or (new <= self.block_at <= self.pos)):
                new = float(self.block_at)
            if self.block_at is not None and abs(new - self.block_at) < 0.5 and abs(goal - new) > 2:
                load = self.mem[sts.TORQUE_LIMIT[0]] / 1000.0            # упёрся — давит с пределом момента
            self.pos = new
        self.load_frac = min(1.0, load)
        cur = self.current()
        self.temp += dt * (0.12 * (cur / self.p.stall_a * 2.7) ** 2 - (self.temp - 26.0) / 300.0)

    def reg(self, addr: int) -> int:
        if addr == sts.PRESENT_POS[0]:
            v = int(round(self.pos + random.uniform(-0.6, 0.6)))
            return v if v >= 0 else (1 << 15) | -v
        if addr == sts.PRESENT_SPEED[0]:
            return 0
        if addr == sts.PRESENT_LOAD[0]:
            return int(self.load_frac * 1000)
        if addr == sts.PRESENT_VOLT[0]:
            return int(round(self.volt * 10 - self.load_frac * 3 * self.p.volt / 12))
        if addr == sts.PRESENT_TEMP[0]:
            return int(self.temp)
        if addr == sts.PRESENT_CURRENT[0]:
            if not self.p.current_sensor:
                return 0
            return int(round(self.current() * random.uniform(0.97, 1.03) / sts.CURRENT_LSB_A))
        return self.mem.get(addr, 0)

    def read(self, addr: int, n: int) -> bytes:
        self.step()
        out = bytearray()
        a = addr
        while len(out) < n:
            size = _REG_SIZE.get(a, 1)
            v = self.reg(a)
            out += bytes([v & 0xFF]) if size == 1 else sts.le16(v)
            a += size
        return bytes(out[:n])

    def write(self, addr: int, value: int) -> None:
        self.step()
        if addr == sts.TORQUE_ENABLE[0] and value == sts.CALIBRATE_MIDDLE:
            self.offset += self.pos - sts.MIDDLE                 # текущая позиция становится 2048
            self.mem[sts.GOAL_POS[0]] = sts.MIDDLE
            return
        self.mem[addr] = value


class FakeBus:
    def __init__(self, ids=(1,), speedup: float = 1.0, profile: sts.Profile = sts.PROFILES["sts3215"]):
        t0 = time.monotonic()
        self.speedup = speedup
        self.clock = lambda: t0 + (time.monotonic() - t0) * self.speedup
        self.servos = {i: FakeServo(i, self.clock, profile) for i in ids}

    def close(self) -> None:
        pass

    def ping(self, sid: int) -> bool:
        return sid in self.servos

    def read(self, sid: int, reg) -> bytes:
        if sid not in self.servos:
            raise sts.BusError(f"привод {sid} не ответил")
        self.tick()
        return self.servos[sid].read(*reg)

    def write(self, sid: int, reg, value: int) -> None:
        if sid == sts.BROADCAST:
            for s in self.servos.values():
                s.write(reg[0], value)
            return
        if sid not in self.servos:
            raise sts.BusError(f"привод {sid} не ответил")
        s = self.servos[sid]
        if reg == sts.ID and s.mem[sts.LOCK[0]] == 0:
            del self.servos[sid]
            s.id = value
            self.servos[value] = s
            return
        s.write(reg[0], value)
        self.tick()

    def sync_write(self, reg, values: dict) -> None:
        for sid, v in values.items():
            self.write(sid, reg, v)

    def tick(self) -> None:
        """Общая физика шины (у простой шины её нет)."""


class FakeLegBus(FakeBus):
    """Нога мини на стенде: 1 — поворот, 2 — бедро, 3 — колено. Приводы собраны как в инструкции:
    после калибровки середины 2048 — поза «Г» (бедро горизонтально, голень вниз), направления «+» совпадают.
    Под стопой — весы на уровне стола: стопа не проходит сквозь них, бедро давит с силой по ошибке позиции."""

    def __init__(self, geometry, speedup: float = 1.0):
        super().__init__(ids=(1, 2, 3), speedup=speedup, profile=sts.PROFILES["sts3032"])
        self.g = geometry
        self.force_n = 0.0
        self.table = True                                 # под стопой стол с весами (False — нога за краем стола)

    def tick(self) -> None:
        cx, fm, kn = (self.servos.get(i) for i in (1, 2, 3))
        if not (cx and fm and kn):
            return
        for s in (cx, fm, kn):
            s.step()
        g = self.g
        q = lambda s, ref: math.radians(ref + (s.pos - sts.MIDDLE) * sts.DEG_PER_STEP)
        qf, qk = q(fm, 0.0), q(kn, -90.0)
        _, h = g.foot(qf, qk)
        surface = -g.zj
        if self.table and h < surface:                                   # стопа ушла бы в весы: бедро упирается
            qf_c = g.femur_for_height(qk, surface, qf)
            goal = fm.mem[sts.GOAL_POS[0]]
            fm.pos = sts.MIDDLE + math.degrees(qf_c) / sts.DEG_PER_STEP
            err = abs(goal - fm.pos)
            lim = fm.mem[sts.TORQUE_LIMIT[0]] / 1000.0
            frac = min(lim, err / 40.0) if fm.mem[sts.TORQUE_ENABLE[0]] else 0.0      # 40 шагов (3,5°) — полный момент
            fm.contact_frac = frac
            fm.load_frac = max(fm.load_frac, frac)
            r = max(g.horizontal(qf_c, qk), 5.0) / 1000.0
            self.force_n = frac * fm.p.stall_nm / r
        else:
            fm.contact_frac = 0.0
            self.force_n = 0.0

    def scale_grams(self) -> float:
        return self.force_n / 9.81 * 1000.0
