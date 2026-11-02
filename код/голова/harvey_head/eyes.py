"""Глаза Харви: рисование круглого глаза 160 × 160 по выражению, моргание, взгляд и плавные переходы.

Выражение — набор чисел (раскрытие век, наклон век, размер зрачка, цвет радужки), поэтому новое выражение —
одна строка в EXPRESSIONS. Картинку для дисплея даёт to_rgb565 (GC9D01, COLMOD 05h — 16 бит на точку,
R[4:0] G[5:0] B[4:0], старший байт первым — документы/GC9D01N — даташит Galaxycore.pdf, разд. 5.2.22 и 5.2.13).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace

import numpy as np
from PIL import Image, ImageDraw

SIZE = 160
SCLERA = (238, 240, 236)
LID = (24, 30, 34)                 # веко и фон вне глаза — цвет корпуса


@dataclass(frozen=True)
class Look:
    openness: float = 1.0          # 0 — закрыт, 1 — открыт
    lid_tilt: float = 0.0          # наклон верхнего века: + — внешний угол ниже (грусть), − — внутренний ниже (тревога)
    lower: float = 0.0             # подъём нижнего века 0…1 (улыбка глазами)
    pupil: float = 0.42            # радиус зрачка относительно радужки
    iris: tuple = (38, 120, 200)   # цвет радужки
    x: float = 0.0                 # взгляд −1 … 1: + — к правому боку Харви (для того, кто стоит напротив, — влево)
    y: float = 0.0                 # −1 (вниз) … 1 (вверх)


EXPRESSIONS = {
    "neutral": Look(),
    "happy": Look(openness=0.9, lower=0.45, pupil=0.5, iris=(40, 150, 210)),
    "sad": Look(openness=0.7, lid_tilt=0.35, pupil=0.4, y=-0.3, iris=(60, 100, 170)),
    "sleepy": Look(openness=0.35, pupil=0.4, y=-0.2),
    "asleep": Look(openness=0.0),
    "surprised": Look(openness=1.0, pupil=0.25, iris=(60, 140, 220)),
    "curious": Look(openness=1.0, pupil=0.55, x=0.25, y=0.15),
    "alarm": Look(openness=1.0, lid_tilt=-0.3, pupil=0.22, iris=(220, 80, 40)),
    "tired": Look(openness=0.55, lid_tilt=0.15, pupil=0.38, iris=(90, 110, 140)),
    "love": Look(openness=0.85, lower=0.35, pupil=0.62, iris=(220, 90, 140)),
}


def lerp(a, b, k):
    return a + (b - a) * k


def blend(a: Look, b: Look, k: float) -> Look:
    """Промежуточное выражение: k = 0 — a, 1 — b."""
    k = max(0.0, min(1.0, k))
    return Look(openness=lerp(a.openness, b.openness, k), lid_tilt=lerp(a.lid_tilt, b.lid_tilt, k),
                lower=lerp(a.lower, b.lower, k), pupil=lerp(a.pupil, b.pupil, k),
                iris=tuple(int(round(lerp(p, q, k))) for p, q in zip(a.iris, b.iris)),
                x=lerp(a.x, b.x, k), y=lerp(a.y, b.y, k))


def render(look: Look, side: str = "left", size: int = SIZE) -> Image.Image:
    """Один глаз, каким его видит человек напротив Харви. side — бок робота. Веки правого глаза зеркальны левому
    (внутренний угол — к середине головы), а взгляд и блик у обоих глаз в одну сторону."""
    s = size / SIZE
    mirror = side == "right"
    img = Image.new("RGB", (size, size), LID)
    d = ImageDraw.Draw(img)
    c = size / 2
    r_eye = 74 * s
    d.ellipse((c - r_eye, c - r_eye, c + r_eye, c + r_eye), fill=SCLERA)
    r_iris = 36 * s
    gx = look.x if mirror else -look.x                    # картинку правого глаза потом отразят — взгляд отражаем заранее
    ix, iy = c + gx * 30 * s, c - look.y * 26 * s
    d.ellipse((ix - r_iris, iy - r_iris, ix + r_iris, iy + r_iris), fill=look.iris)
    r_p = r_iris * look.pupil
    d.ellipse((ix - r_p, iy - r_p, ix + r_p, iy + r_p), fill=(8, 10, 12))
    hx = ix + (r_iris * 0.45 if mirror else -r_iris * 0.45)
    hl = 8 * s
    d.ellipse((hx - hl, iy - r_iris * 0.45 - hl, hx + hl, iy - r_iris * 0.45 + hl), fill=(255, 255, 255))
    _lids(d, look, c, r_eye, size)
    return img.transpose(Image.FLIP_LEFT_RIGHT) if mirror else img


def _lids(d: ImageDraw.ImageDraw, look: Look, c: float, r: float, size: int) -> None:
    """Верхнее веко опускается до края глаза при openness = 0; нижнее поднимается на lower.
    Рисуется левый глаз: напротив Харви его внутренний угол — слева на картинке, внешний — справа."""
    edge = c - r + (1.0 - look.openness) * 2 * r                     # высота края века в середине
    tilt = look.lid_tilt * r * 0.6
    d.polygon([(0, 0), (size, 0), (size, edge + tilt), (0, edge - tilt)], fill=LID)
    if look.openness < 0.05:                                         # закрыт: линия ресниц, чтобы глаз не пропадал
        d.arc((c - r * 0.8, c - r * 0.5, c + r * 0.8, c + r * 0.4), 20, 160, fill=(120, 130, 140), width=max(2, size // 40))
    if look.lower > 0:
        top = c + r - look.lower * r
        d.ellipse((c - r * 1.3, top, c + r * 1.3, top + 2 * r), fill=LID)


def to_rgb565(img: Image.Image) -> bytes:
    a = np.asarray(img.convert("RGB"), dtype=np.uint16)
    v = ((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)
    return v.astype(">u2").tobytes()


class Animator:
    """Живые глаза: плавный переход к выражению (0,25 с), моргание раз в 2–6 с и небольшие движения взгляда."""

    BLINK_S, MOVE_S = 0.16, 0.25

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.target = self.current = self.start = EXPRESSIONS["neutral"]
        self.t_change = 0.0
        self.next_blink = self.rng.uniform(2, 6)
        self.blink_at = None
        self.gaze = (0.0, 0.0)
        self.next_glance = self.rng.uniform(1, 4)

    def set(self, name_or_look, now: float) -> None:
        look = EXPRESSIONS[name_or_look] if isinstance(name_or_look, str) else name_or_look
        if look != self.target:
            self.start, self.target, self.t_change = self.current, look, now

    def look_at(self, x: float, y: float) -> None:
        self.gaze = (max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))

    def frame(self, now: float) -> Look:
        k = (now - self.t_change) / self.MOVE_S
        self.current = blend(self.start, self.target, k)
        look = replace(self.current, x=max(-1.0, min(1.0, self.current.x + self.gaze[0])),
                       y=max(-1.0, min(1.0, self.current.y + self.gaze[1])))
        if now >= self.next_glance:
            self.gaze = (self.rng.uniform(-0.3, 0.3), self.rng.uniform(-0.2, 0.2))
            self.next_glance = now + self.rng.uniform(1, 4)
        return replace(look, openness=look.openness * self._blink(now))

    def _blink(self, now: float) -> float:
        if self.blink_at is None and now >= self.next_blink and self.target.openness > 0:
            self.blink_at = now
        if self.blink_at is None:
            return 1.0
        p = (now - self.blink_at) / self.BLINK_S
        if p >= 1.0:
            self.blink_at = None
            self.next_blink = now + self.rng.uniform(2, 6)
            return 1.0
        return abs(math.cos(math.pi * p))                             # открыт → закрыт → открыт
