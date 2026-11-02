"""Настроение Харви: события → выражение глаз. Добрый характер (ориентир — ВАЛЛ-И): пугается края и рук,
радуется поглаживанию, засыпает, когда скучно, устаёт, когда садится батарея.

Каждое событие даёт выражение на время; важное (испуг) не перебивается менее важным (скукой).
Без событий выражение по умолчанию зависит от того, как давно с Харви что-то происходило.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reaction:
    expression: str
    seconds: float
    priority: int


REACTIONS = {
    "fall": Reaction("alarm", 3.0, 9),
    "lifted": Reaction("surprised", 2.0, 8),
    "edge": Reaction("alarm", 1.5, 7),
    "shock": Reaction("surprised", 1.2, 6),
    "tip": Reaction("alarm", 2.0, 6),
    "bat_critical": Reaction("tired", 10.0, 5),
    "pet": Reaction("happy", 3.0, 4),
    "hold": Reaction("love", 3.0, 4),
    "tap": Reaction("curious", 1.5, 3),
    "voice": Reaction("curious", 2.0, 3),
    "docked": Reaction("sleepy", 4.0, 2),
    "bat_low": Reaction("tired", 4.0, 2),
}

SLEEPY_AFTER_S, ASLEEP_AFTER_S = 90.0, 300.0
ACTIVITY = {"fall", "lifted", "edge", "shock", "tip", "pet", "hold", "tap", "voice"}   # будят и сбивают скуку


class Mood:
    def __init__(self, now: float = 0.0):
        self.active: tuple[Reaction, float] | None = None      # (реакция, до какого времени)
        self.last_activity = now
        self.docked = False
        self.battery = "ok"

    def event(self, name: str, now: float) -> None:
        if name == "docked":
            self.docked = True
        elif name in ACTIVITY:
            self.last_activity = now
        if name in ("bat_low", "bat_critical"):
            self.battery = "low"
        r = REACTIONS.get(name)
        if r is None:
            return
        if self.active is None or now >= self.active[1] or r.priority >= self.active[0].priority:
            self.active = (r, now + r.seconds)

    def emote(self, expression: str, seconds: float, now: float) -> None:
        """Выражение по команде «большого мозга» (ПК) — как событие среднего веса."""
        self.active = (Reaction(expression, seconds, 5), now + seconds)
        self.last_activity = now

    def undock(self) -> None:
        self.docked = False

    def expression(self, now: float) -> str:
        if self.active is not None and now < self.active[1]:
            return self.active[0].expression
        self.active = None
        idle = now - self.last_activity
        if idle >= ASLEEP_AFTER_S or (self.docked and idle >= SLEEPY_AFTER_S):
            return "asleep"
        if idle >= SLEEPY_AFTER_S or self.docked:
            return "sleepy"
        return "tired" if self.battery == "low" else "neutral"
