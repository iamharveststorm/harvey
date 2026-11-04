"""Камера головы → метка станции для поведения: {"dock": {"bearing_deg", "dist_mm"} | None}.

Кадр берётся не чаще every_s (разбор 1280 × 720 на Pi Zero 2 W небыстрый — скорость проверить на стенде), между
кадрами поведение получает последний ответ. На роботе grab — Picamera2: яркость (плоскость Y кадра YUV420).
"""
from __future__ import annotations

from . import dock_tag


class DockCamera:
    def __init__(self, grab, K, dist=None, every_s: float = 0.2):
        self.grab, self.K, self.dist, self.every = grab, K, dist, every_s
        self.t_last: float | None = None
        self.last: dict = {"dock": None}

    def vision(self, now: float) -> dict:
        if self.t_last is None or now - self.t_last >= self.every - 1e-9:
            self.t_last = now
            self.last = {"dock": dock_tag.locate(self.grab(), self.K, self.dist)}
        return self.last


def picamera(size=dock_tag.FRAME):
    """Camera Module 3 Wide через Picamera2: функция «дай кадр яркости» (только на Pi)."""
    from picamera2 import Picamera2
    cam = Picamera2()
    cam.configure(cam.create_video_configuration(main={"size": size, "format": "YUV420"}))
    cam.start()
    return lambda: cam.capture_array("main")[:size[1], :size[0]]
