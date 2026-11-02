"""Драйвер круглого дисплея GC9D01 (160 × 160, 4-проводной SPI) для Pi: два глаза на одной шине SPI0, CE0 и CE1.

Команды — документы/GC9D01N — даташит Galaxycore.pdf: 2Ah Column Address Set (разд. 5.2.11), 2Bh Row Address Set
(5.2.12), 2Ch Memory Write (5.2.13), 36h Memory Access Control (5.2.18), 3Ah COLMOD, 05h — 16 бит (5.2.22);
после 11h Sleep Out — ждать ≥ 5 мс (5.2.4). Последовательность запуска панели — от производителя модуля:
документы/GC9D01 — код запуска Waveshare 0.71.txt (демо Waveshare 0.71inch LCD Module). DC: 0 — команда, 1 — данные.
"""
from __future__ import annotations

import time

def load_vendor_init(text: str) -> list[tuple[int, bytes, int]]:
    """Разбор кода запуска производителя (SPI_WriteComm / SPI_WriteData / Delay) в список команд."""
    import re

    seq: list[list] = []
    for line in text.splitlines():
        if m := re.search(r"WriteComm\(0x([0-9A-Fa-f]+)\)", line):
            seq.append([int(m.group(1), 16), bytearray(), 0])
        elif (m := re.search(r"WriteData\(0x([0-9A-Fa-f]+)\)", line)) and seq:
            seq[-1][1].append(int(m.group(1), 16))
        elif (m := re.search(r"Delay\w*\((\d+)\)", line)) and seq:
            seq[-1][2] += int(m.group(1))
    return [(c, bytes(d), ms) for c, d, ms in seq]


CASET, RASET, RAMWR, MADCTL, SLPOUT, DISPON = 0x2A, 0x2B, 0x2C, 0x36, 0x11, 0x29
CHUNK = 4096                                         # spidev по умолчанию передаёт не больше 4096 байт за раз


class GC9D01:
    def __init__(self, spi, dc, init: list[tuple[int, bytes, int]], madctl: int = 0x08, size: int = 160,
                 sleep=time.sleep):
        self.spi, self.dc, self.size, self.sleep = spi, dc, size, sleep
        for cmd, data, ms in init:
            if cmd == MADCTL:
                data = bytes([madctl])
            self.command(cmd, data)
            if cmd == SLPOUT:
                ms = max(ms, 5)
            if ms:
                self.sleep(ms / 1000)

    def command(self, cmd: int, data: bytes = b"") -> None:
        self.dc.off()
        self.spi.writebytes([cmd])
        if data:
            self.dc.on()
            self._data(data)

    def _data(self, data: bytes) -> None:
        for i in range(0, len(data), CHUNK):
            self.spi.writebytes2(data[i:i + CHUNK])

    def window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.command(CASET, bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        self.command(RASET, bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))

    def show(self, rgb565: bytes) -> None:
        n = self.size * self.size * 2
        if len(rgb565) != n:
            raise ValueError(f"кадр {len(rgb565)} байт, нужно {n}")
        self.window(0, 0, self.size - 1, self.size - 1)
        self.command(RAMWR, rgb565)


def open_eyes(cfg, init_text: str):
    """Настоящие дисплеи на Pi: общий сброс, затем каждый глаз на своём CE. Возвращает {"left": GC9D01, "right": …}."""
    import spidev
    from gpiozero import DigitalOutputDevice, PWMOutputDevice

    dc, rst = DigitalOutputDevice(cfg.EYE_DC), DigitalOutputDevice(cfg.EYE_RST, initial_value=True)
    rst.off()
    time.sleep(0.01)
    rst.on()
    time.sleep(0.12)
    init = load_vendor_init(init_text)
    eyes = {}
    for side, ce in cfg.EYE_CE.items():
        spi = spidev.SpiDev()
        spi.open(cfg.SPI_BUS, ce)
        spi.max_speed_hz, spi.mode = cfg.SPI_HZ, 0
        eyes[side] = GC9D01(spi, dc, init, cfg.EYE_MADCTL[side], cfg.EYE_SIZE)
    backlight = PWMOutputDevice(cfg.EYE_BL, frequency=1000, initial_value=0.8)
    return eyes, backlight
