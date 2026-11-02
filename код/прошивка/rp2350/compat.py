# Харви — то, чем MicroPython отличается от обычного Python: время и const.
# На RP2350 берутся встроенные функции, на ПК (тесты) — их замена. Остальные файлы прошивки импортируют отсюда.

import time

try:
    from micropython import const
except ImportError:                                  # ПК
    def const(x):
        return x

try:
    sleep_ms, sleep_us = time.sleep_ms, time.sleep_us
    ticks_ms, ticks_diff = time.ticks_ms, time.ticks_diff
except AttributeError:                               # ПК
    def sleep_ms(ms):
        time.sleep(ms / 1000)

    def sleep_us(us):
        time.sleep(us / 1000000)

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b
