"""Запуск головы на Pi Zero 2 W:  python -m harvey_head.main
Без дисплеев и RP2350 (на ПК):     python -m harvey_head.main --sim   — глаза пишутся в eyes_sim.png раз в секунду.
"""
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from . import config
from .behavior import Behavior
from .body import Body
from .eyes import render
from .gait import Gait
from .head import Head
from .links import BrainLink, SpineLink

INIT_FILE = Path(__file__).absolute().parents[3] / "документы" / "GC9D01 — код запуска Waveshare 0.71.txt"


class NoSpine:
    def poll(self, now):
        return []

    def send(self, msg):
        return False


def hardware(cfg):
    import serial
    from gpiozero import Button, DigitalOutputDevice

    from . import dock_tag
    from .audio import Audio
    from .camera import DockCamera, picamera
    from .gc9d01 import open_eyes

    eyes, backlight = open_eyes(cfg, INIT_FILE.read_text(encoding="utf-8"))
    spine = SpineLink(lambda: serial.Serial(cfg.SPINE_PORT, cfg.SPINE_BAUD, timeout=0))
    pads = [Button(p, pull_up=False) for p in cfg.TOUCH_PADS]            # TTP223: 1 — касание
    audio = Audio(DigitalOutputDevice(cfg.AMP_SD), cfg.ALSA_DEVICE)
    camera = DockCamera(picamera(), dock_tag.camera_matrix(*dock_tag.FRAME), every_s=cfg.CAMERA_EVERY_S)
    return eyes, spine, pads, audio, backlight, camera


async def run(sim: bool) -> None:
    brain = BrainLink(config.BRAIN_HOST, config.BRAIN_PORT)
    if sim:
        eyes, spine, pads, audio, camera = {}, NoSpine(), [], None, None
    else:
        eyes, spine, pads, audio, _backlight, camera = hardware(config)
    now = time.monotonic()
    body = Body(spine, Behavior(now), Gait(), vision=camera.vision if camera else None, now=now, hz=config.LOOP_HZ)
    head = Head(spine, eyes, brain, audio, now=now, telemetry_hz=config.TELEMETRY_TO_BRAIN_HZ, body=body, fps=config.FPS)
    stop = asyncio.Event()
    brain_task = asyncio.ensure_future(brain.run(stop))
    pressed = [False] * len(pads)
    last_png = 0.0
    try:
        while True:
            now = time.monotonic()
            while not brain.inbox.empty():
                head.on_brain(brain.inbox.get_nowait(), now)
            for i, pad in enumerate(pads):
                if pad.is_pressed != pressed[i]:
                    pressed[i] = pad.is_pressed
                    head.on_touch(i, pressed[i], now)
            state = head.tick(now)
            if sim and now - last_png >= 1.0:
                render(state["look"], "left").save("eyes_sim.png")
                last_png = now
            await asyncio.sleep(1 / config.LOOP_HZ)
    finally:
        stop.set()
        brain_task.cancel()


def main() -> None:
    ap = argparse.ArgumentParser(description="Голова Харви на Pi Zero 2 W")
    ap.add_argument("--sim", action="store_true", help="без дисплеев, RP2350 и кнопок")
    asyncio.run(run(ap.parse_args().sim))


if __name__ == "__main__":
    main()
