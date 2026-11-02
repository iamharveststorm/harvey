"""Касания крышки: 4 кнопки TTP223 в ряд спереди назад. Погладить — провести по трём кнопкам подряд;
коснуться — короткое касание одной; подержать — ладонь дольше 1,5 с.

TTP223 по умолчанию даёт 1, пока к пластине прикасаются (режим «прямой выход, без защёлки») — проверить
перемычки модуля на стенде. Детектор — чистый: ему подают (кнопка, нажата, время), он отвечает событиями.
"""
from __future__ import annotations

STROKE_WINDOW_S = 1.2
STROKE_PADS = 3
TAP_MAX_S = 0.5
HOLD_S = 1.5


class TouchDetector:
    def __init__(self, pads: int = 4):
        self.down_at: list[float | None] = [None] * pads
        self.trail: list[tuple[int, float]] = []          # (кнопка, время) последних нажатий
        self.held = [False] * pads

    def update(self, pad: int, pressed: bool, now: float) -> list[str]:
        if pressed and self.down_at[pad] is None:
            return self._press(pad, now)
        if not pressed and self.down_at[pad] is not None:
            return self._release(pad, now)
        return []

    def _press(self, pad: int, now: float) -> list[str]:
        self.down_at[pad] = now
        self.trail = [(p, t) for p, t in self.trail if now - t <= STROKE_WINDOW_S] + [(pad, now)]
        if self._stroke():
            self.trail = []
            return ["pet"]
        return []

    def _release(self, pad: int, now: float) -> list[str]:
        tap = now - self.down_at[pad] <= TAP_MAX_S and not self.held[pad] and not self._others_down(pad)
        self.down_at[pad], self.held[pad] = None, False
        return ["tap"] if tap else []

    def tick(self, now: float) -> list[str]:
        """Подержать — проверяется по времени, даже если кнопки не менялись."""
        out = []
        for i, t in enumerate(self.down_at):
            if t is not None and not self.held[i] and now - t >= HOLD_S:
                self.held[i] = True
                out.append("hold")
        return out

    def _others_down(self, pad: int) -> bool:
        return any(t is not None for i, t in enumerate(self.down_at) if i != pad)

    def _stroke(self) -> bool:
        """Три разные соседние кнопки подряд в одну сторону."""
        pads = [p for p, _ in self.trail]
        if len(pads) < STROKE_PADS:
            return False
        last = pads[-STROKE_PADS:]
        steps = {b - a for a, b in zip(last, last[1:])}
        return steps == {1} or steps == {-1}
