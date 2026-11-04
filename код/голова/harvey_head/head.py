"""Голова целиком: события от «спинного мозга», касаний и ПК → настроение → глаза; телеметрия → ПК.

Устройства передаются снаружи (main.py собирает настоящие, тесты — имитацию). Без ПК голова живёт сама:
реагирует на край, руки, поглаживание, батарею и засыпает от скуки.
"""
from __future__ import annotations

from .eyes import Animator, render, to_rgb565
from .mood import Mood
from .touch import TouchDetector

SPINE_EVENTS = {"edge", "fall", "shock", "tip", "lifted", "bat_low", "bat_critical", "docked"}
FORWARD_TO_SPINE = {"j", "relax", "hold", "cal"}         # команды ПК, которые голова передаёт RP2350 как есть


class Head:
    def __init__(self, spine, eyes: dict | None = None, brain=None, audio=None, now: float = 0.0, seed: int | None = None,
                 telemetry_hz: float = 5.0, body=None, fps: float = 30.0):
        self.spine, self.eyes, self.brain, self.audio, self.body = spine, eyes or {}, brain, audio, body
        self.eye_period, self.t_eyes = 1.0 / fps, None
        self.mood = Mood(now)
        self.anim = Animator(seed)
        self.touch = TouchDetector()
        self.tel_period = 1.0 / telemetry_hz
        self.t_tel = now
        self.last_tel: dict = {}
        self.expression = "neutral"
        self.log: list[str] = []

    # ---------- входы ----------
    def on_spine(self, msg: dict, now: float) -> None:
        if self.body is not None:
            self.body.on_spine(msg, now)
        t = msg.get("t")
        if t == "ev":
            self._spine_event(msg, now)
        elif t == "tel":
            self._telemetry(msg, now)
        elif t in ("hello", "err", "link"):
            self.log.append(f"spine: {msg}")

    def _spine_event(self, msg: dict, now: float) -> None:
        name = msg.get("ev")
        if name in SPINE_EVENTS:
            self.mood.event(name, now)
            self._to_brain({"t": "ev", "ev": name, "info": msg.get("info"), "from": "spine"})

    def _telemetry(self, msg: dict, now: float) -> None:
        self.last_tel = msg
        bat = msg.get("bat") or [0, 0]
        if self.mood.docked and len(bat) > 1 and bat[1] > 0:
            self.mood.undock()                                   # ток снова на разряд — сошли со станции
        if now - self.t_tel >= self.tel_period:
            self._to_brain(msg)
            self.t_tel = now

    def on_touch(self, pad: int, pressed: bool, now: float) -> None:
        for name in self.touch.update(pad, pressed, now):
            self._touch_event(name, now)

    def _touch_event(self, name: str, now: float) -> None:
        self.mood.event(name, now)
        self._to_brain({"t": "ev", "ev": name, "from": "touch"})

    def on_brain(self, msg: dict, now: float) -> None:
        t = msg.get("t")
        if t == "emote":
            self.mood.emote(msg.get("name", "neutral"), float(msg.get("s", 2.0)), now)
        elif t == "look":
            self.anim.look_at(float(msg.get("x", 0)), float(msg.get("y", 0)))
        elif t == "goal" and self.body is not None:
            self.body.request(msg.get("goal", "idle"), now)
        elif t == "play" and self.audio is not None:
            self.audio.play(msg["path"])
        elif t in FORWARD_TO_SPINE:
            self.spine.send(msg)
        elif t == "link":
            self.log.append(f"brain: {msg}")

    def _to_brain(self, msg: dict) -> None:
        if self.brain is not None:
            self.brain.offer(msg)

    # ---------- один кадр ----------
    def tick(self, now: float) -> dict:
        for msg in self.spine.poll(now):
            self.on_spine(msg, now)
        for name in self.touch.tick(now):
            self._touch_event(name, now)
        if self.body is not None:
            self.body.tick(now)
        self.expression = self.mood.expression(now)
        self.anim.set(self.expression, now)
        look = self.anim.frame(now)
        if self.t_eyes is None or now - self.t_eyes >= self.eye_period - 1e-9:
            self.t_eyes = now
            for side, display in self.eyes.items():
                display.show(to_rgb565(render(look, side)))
        return {"expression": self.expression, "look": look}
