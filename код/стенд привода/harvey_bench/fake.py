"""Имитация шины с приводами STS3215 — чтобы прогнать скрипт стенда без железа.
Физика упрощённая: скорость по паспорту, упор, ток от нагрузки, нагрев корпуса."""
from __future__ import annotations

import random
import time

from . import sts


class FakeServo:
    def __init__(self, sid: int, clock):
        self.id, self.clock = sid, clock
        self.mem = {sts.MODEL[0]: sts.MODEL_STS3215, sts.TORQUE_ENABLE[0]: 0, sts.TORQUE_LIMIT[0]: 1000,
                    sts.GOAL_POS[0]: 2048, sts.GOAL_SPEED[0]: 0, sts.ACCEL[0]: 0, sts.LOCK[0]: 1}
        self.pos, self.t, self.temp = 2048.0, clock(), 26.0
        self.volt = 12.0
        self.block_at: int | None = None          # упор (рычаг на весах)
        self.ext_load_frac = 0.0                  # постоянная внешняя нагрузка (груз на рычаге), доля от упора
        self.load_frac = 0.0

    def step(self) -> None:
        now = self.clock()
        dt, self.t = now - self.t, now
        if dt <= 0:
            return
        load = self.ext_load_frac
        if self.mem[sts.TORQUE_ENABLE[0]]:
            goal = self.mem[sts.GOAL_POS[0]]
            vmax = 3075.0 * self.volt / 12.0 * max(0.0, 1.0 - load)
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
        cur = 0.03 + self.load_frac * 2.7 if self.mem[sts.TORQUE_ENABLE[0]] else 0.006
        self.temp += dt * (0.12 * cur * cur - (self.temp - 26.0) / 300.0)

    def read(self, addr: int, n: int) -> bytes:
        self.step()
        if addr == sts.PRESENT_POS[0]:
            v = int(round(self.pos + random.uniform(-0.6, 0.6)))
        elif addr == sts.PRESENT_SPEED[0]:
            v = 0
        elif addr == sts.PRESENT_LOAD[0]:
            v = int(self.load_frac * 1000)
        elif addr == sts.PRESENT_VOLT[0]:
            v = int(round(self.volt * 10 - self.load_frac * 3))
        elif addr == sts.PRESENT_TEMP[0]:
            v = int(self.temp)
        elif addr == sts.PRESENT_CURRENT[0]:
            cur = 0.03 + self.load_frac * 2.7 if self.mem[sts.TORQUE_ENABLE[0]] else 0.006
            v = int(round(cur * random.uniform(0.97, 1.03) / sts.CURRENT_LSB_A))
        else:
            v = self.mem.get(addr, 0)
        return bytes([v & 0xFF]) if n == 1 else sts.le16(v)

    def write(self, addr: int, value: int) -> None:
        self.step()
        self.mem[addr] = value


class FakeBus:
    def __init__(self, ids=(1,), speedup: float = 1.0):
        t0 = time.monotonic()
        self.speedup = speedup
        self.clock = lambda: t0 + (time.monotonic() - t0) * self.speedup
        self.servos = {i: FakeServo(i, self.clock) for i in ids}

    def close(self) -> None:
        pass

    def ping(self, sid: int) -> bool:
        return sid in self.servos

    def read(self, sid: int, reg) -> bytes:
        if sid not in self.servos:
            raise sts.BusError(f"привод {sid} не ответил")
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

    def sync_write(self, reg, values: dict) -> None:
        for sid, v in values.items():
            self.write(sid, reg, v)
