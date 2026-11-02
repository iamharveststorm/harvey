"""Звук головы: 2 × INMP441 (I2S, стерео — левый и правый микрофон) и усилитель MAX98357A с динамиком 20 мм.

Звуковая карта I2S включается в /boot/firmware/config.txt (см. README головы); здесь — только запуск aplay / arecord
из alsa-utils и вывод SD усилителя (0 — тишина, чтобы динамик не шипел). ПРЕДВАРИТЕЛЬНО: имя устройства ALSA
и уровень записи проверить на стенде (`arecord -l`, `aplay -l`).
"""
from __future__ import annotations

import subprocess


def play_cmd(path: str, device: str = "default") -> list[str]:
    return ["aplay", "-q", "-D", device, path]


def record_cmd(path: str, seconds: float, device: str = "default", rate: int = 16000) -> list[str]:
    """Стерео 16 кГц, 32 бита — так INMP441 отдаёт данные (24 бита в 32-битном слове)."""
    return ["arecord", "-q", "-D", device, "-c", "2", "-r", str(rate), "-f", "S32_LE", "-d", str(max(1, round(seconds))),
            path]


class Audio:
    def __init__(self, amp=None, device: str = "default", run=subprocess.run):
        self.amp, self.device, self.run = amp, device, run      # amp — вывод SD (gpiozero DigitalOutputDevice)

    def play(self, path: str) -> bool:
        if self.amp is not None:
            self.amp.on()
        try:
            return self.run(play_cmd(path, self.device), check=False).returncode == 0
        finally:
            if self.amp is not None:
                self.amp.off()

    def record(self, path: str, seconds: float) -> bool:
        return self.run(record_cmd(path, seconds, self.device), check=False).returncode == 0
