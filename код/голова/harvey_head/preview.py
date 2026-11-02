"""Посмотреть глаза без Pi: лист всех выражений и анимация моргания и взгляда.

    python -m harvey_head.preview            # → глаза_выражения.png и глаза_анимация.gif в папке код/голова
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .eyes import EXPRESSIONS, Animator, render

OUT = Path(__file__).absolute().parents[1]


def sheet(path: Path = OUT / "глаза_выражения.png") -> Path:
    names = list(EXPRESSIONS)
    cols, cell = 5, 340
    img = Image.new("RGB", (cols * cell, ((len(names) + cols - 1) // cols) * 200), (16, 18, 20))
    d = ImageDraw.Draw(img)
    for i, name in enumerate(names):
        x, y = (i % cols) * cell, (i // cols) * 200
        img.paste(render(EXPRESSIONS[name], "right"), (x + 8, y + 8))          # напротив Харви: правый глаз — слева
        img.paste(render(EXPRESSIONS[name], "left"), (x + 172, y + 8))
        d.text((x + 10, y + 176), name, fill=(220, 220, 220))
    img.save(path)
    return path


def animation(path: Path = OUT / "глаза_анимация.gif", seconds: float = 6.0, fps: int = 20) -> Path:
    anim = Animator(seed=3)
    frames = []
    plan = [(0.0, "neutral"), (1.5, "curious"), (3.0, "happy"), (4.5, "sleepy")]
    for k in range(int(seconds * fps)):
        t = k / fps
        anim.set([n for t0, n in plan if t >= t0][-1], t)
        look = anim.frame(t)
        pair = Image.new("RGB", (330, 160), (16, 18, 20))
        pair.paste(render(look, "right"), (0, 0))
        pair.paste(render(look, "left"), (170, 0))
        frames.append(pair)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=1000 // fps, loop=0)
    return path


if __name__ == "__main__":
    print(sheet(), animation())
