"""Тело Харви на голове: поведение (behavior.py) + походка (gait.py) → цели всех суставов на RP2350.

Телеметрия и события RP2350 и «зрение» (камера — метка станции) идут в поведение; его команда — в походку; углы — в
сообщение `j` 50 раз в секунду. Рефлексы края и «подняли» решает RP2350: если движение запрещено, он `j` не пропустит.
Через CAL_AFTER_S после первой телеметрии Харви уже стоит — RP2350 запоминает расстояние до стола (`cal`).
"""
from __future__ import annotations

from . import servos

HZ = 50
CAL_AFTER_S = 1.5


class Body:
    def __init__(self, spine, behavior, gait, vision=None, now: float = 0.0, hz: float = HZ, cal=None):
        self.spine, self.behavior, self.gait, self.vision = spine, behavior, gait, vision
        self.cal = cal or servos.Calibration()             # нули и направления приводов (servo_calib.json)
        self.period = 1.0 / hz
        self.tel: dict = {}
        self.events: list[str] = []
        self.t_last = now
        self.t_first_tel: float | None = None
        self.calibrated = False

    def on_spine(self, msg: dict, now: float) -> None:
        if msg.get("t") == "tel":
            self.tel = msg
            if self.t_first_tel is None:
                self.t_first_tel = now
        elif msg.get("t") == "ev":
            self.events.append(msg.get("ev"))

    def request(self, goal: str, now: float) -> None:
        self.behavior.request(goal, now)

    def tick(self, now: float) -> dict | None:
        """Раз в period: команда поведения → углы → `j`. До первой телеметрии RP2350 молчим: он ещё не готов."""
        if self.t_first_tel is None or now - self.t_last < self.period - 1e-9:
            return None
        dt, self.t_last = now - self.t_last, now
        seen = self.vision(now) if self.vision else {}
        cmd = self.behavior.update(self.tel, self.events, seen, now)
        self.events = []
        self.spine.send(servos.message(self.gait.step(cmd, min(dt, 2 * self.period)), self.gait.velocity(), self.cal))
        if not self.calibrated and now - self.t_first_tel >= CAL_AFTER_S:
            self.spine.send({"t": "cal"})
            self.calibrated = True
        return cmd
