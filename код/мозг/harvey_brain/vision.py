"""Зрение: лицо в кадре камеры головы (или ноутбука) -> куда смотреть глазам, когда здороваться, куда повернуться.

FaceFinder — детектор YuNet (OpenCV FaceDetectorYN); кто это — не узнаём, только «есть лицо». Остальное — чистая
геометрия и Watcher (состояние «видно / не видно» с задержкой, сглаживание, приветствие), без камеры и без модели.
Знаки углов — как у метки станции (harvey_head/dock_tag.py): азимут + — налево от Харви, лицо в правой половине
кадра — минус. Взгляд глаз (eyes.py): x + — вправо, y + — вверх.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from . import protocol  # noqa: F401  (кладёт код/голова в sys.path: матрица камеры головы берётся из dock_tag)

LOOK_PERIOD_S = 0.2                                        # глазам — не чаще 5 раз в секунду


@dataclass
class Face:
    x: float
    y: float
    w: float
    h: float
    score: float

    @property
    def area(self) -> float:
        return self.w * self.h

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2


class FaceFinder:
    """YuNet. Детектор один; размер входа подстраивается под каждый кадр."""

    def __init__(self, model_path: Path, score: float = 0.8):
        self._det = cv2.FaceDetectorYN.create(str(model_path), "", (320, 320), score)

    def find(self, img: np.ndarray) -> list[Face]:
        """Лица кадра (серого или цветного), от крупного к мелкому."""
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        self._det.setInputSize((img.shape[1], img.shape[0]))
        _, rows = self._det.detect(img)
        faces = [Face(*(float(v) for v in row[:4]), float(row[14])) for row in (rows if rows is not None else [])]
        return sorted(faces, key=lambda f: -f.area)


def decode(jpeg: bytes) -> np.ndarray | None:
    """JPEG головы -> массив как есть (серый 2-мерный или цветной); мусор -> None."""
    if not jpeg:
        return None
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_UNCHANGED)


def head_camera(width: int, height: int) -> tuple[np.ndarray, tuple[int, int]]:
    """(матрица камеры головы для кадра width × height, (width, height))."""
    from harvey_head.dock_tag import camera_matrix
    return camera_matrix(width, height), (width, height)


def direction(face: Face, K: np.ndarray) -> tuple[float, float]:
    """(азимут °, угол места °) центра лица: азимут + — налево от Харви, угол места + — вверх."""
    u, v = face.center
    nx, ny = (u - K[0, 2]) / K[0, 0], (v - K[1, 2]) / K[1, 1]
    return math.degrees(math.atan2(-nx, 1.0)), math.degrees(math.atan2(-ny, math.hypot(nx, 1.0)))


def gaze(face: Face, width: float, height: float) -> tuple[float, float]:
    """Куда смотреть глазам (сообщение `look`): x вправо, y вверх, оба в [-1, 1]."""
    u, v = face.center
    return _unit((u - width / 2) / (width / 2)), _unit(-(v - height / 2) / (height / 2))


def _unit(v: float) -> float:
    return max(-1.0, min(1.0, v))


class Watcher:
    """Лицо видно, пока оно было в кадре не позже lost_s назад (мигание в 1–2 кадра не в счёт).
    Приветствие — когда лицо появилось, а прошлый раз его видели ≥ away_s назад (или никогда)."""

    def __init__(self, away_s: float = 600.0, lost_s: float = 3.0, alpha: float = 0.5):
        self.away_s, self.lost_s, self.alpha = away_s, lost_s, alpha
        self._last_seen: float | None = None
        self._tracking = False
        self._smooth: tuple[float, float, float] = (0.0, 0.0, 0.0)    # взгляд x, y и азимут
        self._t_look = float("-inf")
        self._greet = False

    @property
    def appeared(self) -> bool:
        return self._greet

    def take_greeting(self) -> bool:
        greet, self._greet = self._greet, False
        return greet

    @property
    def bearing(self) -> float | None:
        """Азимут лица, за которым следим, или None, если лица нет."""
        return self._smooth[2] if self._tracking else None

    def update(self, faces: list[Face], now: float, K: np.ndarray, size: tuple[int, int]) -> list[dict]:
        """Новый кадр (faces — все лица кадра, может быть пусто) -> сообщения голове."""
        if faces:
            return self._seen(max(faces, key=lambda f: f.area), now, K, size)
        return self._missing(now)

    def _seen(self, face: Face, now: float, K, size) -> list[dict]:
        if self._last_seen is None or now - self._last_seen >= self.away_s:
            self._greet = True
        self._last_seen = now
        gx, gy = gaze(face, *size)
        new = (gx, gy, direction(face, K)[0])
        a = self.alpha
        self._smooth = tuple(a * n + (1 - a) * o for n, o in zip(new, self._smooth)) if self._tracking else new
        self._tracking = True
        if now - self._t_look < LOOK_PERIOD_S - 1e-9:
            return []
        self._t_look = now
        return [{"t": "look", "x": self._smooth[0], "y": self._smooth[1]}]

    def _missing(self, now: float) -> list[dict]:
        if not self._tracking or now - self._last_seen < self.lost_s:
            return []
        self._tracking = False
        return [{"t": "look", "x": 0.0, "y": 0.0}]


class HeadFrames:
    """Кадры камеры головы из MediaServer. Кадр старше max_age_s не считается: голова отключилась, а последний
    кадр так и лежит."""

    def __init__(self, media, max_age_s: float = 1.0, clock=time.time):
        self.media, self.max_age_s, self.clock = media, max_age_s, clock

    def read(self) -> np.ndarray | None:
        frame = self.media.latest_frame()
        if frame is None or self.clock() - frame[0] > self.max_age_s:
            return None
        return decode(frame[1])

    def close(self) -> None:
        pass


class WebcamFrames:
    """Камера ноутбука (--webcam). В тестах подставляется capture; настоящую камеру открывает только пользователь."""

    def __init__(self, index: int = 0, capture=cv2.VideoCapture):
        self._cap = capture(index)

    def read(self) -> np.ndarray | None:
        ok, img = self._cap.read()
        return img if ok else None

    def close(self) -> None:
        self._cap.release()


class Sight:
    """Один взгляд: кадр из источника -> лица, матрица камеры и размер кадра. Нет кадра — никого не видно."""

    def __init__(self, frames, finder):
        self.frames, self.finder = frames, finder
        self._cam: dict[tuple[int, int], tuple] = {}

    def look(self) -> tuple[list[Face], np.ndarray | None, tuple[int, int] | None]:
        img = self.frames.read()
        if img is None:
            return [], None, None
        height, width = img.shape[:2]
        if (width, height) not in self._cam:
            self._cam[(width, height)] = head_camera(width, height)
        k, size = self._cam[(width, height)]
        return self.finder.find(img), k, size

    def close(self) -> None:
        self.frames.close()
