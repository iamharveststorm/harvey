# Харви — стенд без приводов: самопроверка платы RP2350 (Pico 2 H или RP2350-Zero) до сборки.
# Запуск с ПК: python bench_pc.py selftest (или Thonny → selftest.py). Каждая проверка печатает строку JSON.
#
# Перемычки (Pico 2 H, выводы — по pins.py):
#   GP0 → GP1    шина A, UART0 TX → RX
#   GP4 → GP5    шина B, UART1 TX → RX
#   GP8 → GP9    шина C, UART на PIO TX → RX (1 Мбит/с; приём — очередь всего 4 байта)
#   GP16 → GP14, GP28, GP15   «приёмник TSOP»: GP16 шлёт пачки маяка станции (0,6 / 1,2 мс), как выход TSOP38238
#   датчики I2C (если уже есть) — на GP12 SDA / GP13 SCL, питание 3,3 В
# Без перемычки проверка честно скажет «нет»: так видно, что не так с выводом.

import json

from beacon_station import SCHEDULE
from compat import sleep_ms, sleep_us, ticks_diff, ticks_us

TSOP_OUT = 16                                 # Pico 2 H: свободный вывод — изображает выход приёмника
PATTERN = bytes(range(64)) + b"\x55\xaa\xff\x00"
KNOWN = {0x29: "VL53L4CD (адрес по умолчанию)", 0x40: "INA226", 0x68: "BMI270"}
KNOWN.update({0x30 + i: "VL53L4CD №%d" % (i + 1) for i in range(6)})


def emit(check, result):
    print(json.dumps(dict({"check": check}, **result), separators=(",", ":")))


def uart_loopback(uart, sleep_us=sleep_us, wait_us=200):
    """Перемычка TX → RX: каждый байт уходит и должен вернуться тем же."""
    while uart.any():
        uart.read()
    got = bytearray()
    for b in PATTERN:
        uart.write(bytes([b]))
        sleep_us(wait_us)
        got += uart.read() or b""
    bad = sum(1 for a, b in zip(PATTERN, got) if a != b)
    return {"ok": bytes(got) == PATTERN, "sent": len(PATTERN), "got": len(got), "bad": bad}


def pio_burst(pio, n=64, tick=lambda: None, limit=100000):
    """PIO-UART сплошным потоком на полной скорости: класть в передачу, пока есть место, и сразу забирать принятое.
    Так приходит ответ привода (~20 байт подряд, байт каждые 10 мкс): очередь приёма 4 байта, опоздали — байт пропал."""
    while pio.rx.rx_fifo():
        pio.rx.get()
    sent, got = 0, bytearray()
    for _ in range(limit):
        if sent < n and pio.tx.tx_fifo() < 4:
            pio.tx.put(sent & 0xFF)
            sent += 1
        tick()
        while pio.rx.rx_fifo():
            got.append(pio.rx.get() >> 24)
        if sent == n and not pio.tx.tx_fifo() and len(got) >= n:
            break
    bad = sum(1 for i, b in enumerate(got) if b != (i & 0xFF))
    return {"ok": len(got) == n and bad == 0, "sent": sent, "got": len(got), "bad": bad}


def emulate_tsop(pin, cycles, sleep_us=sleep_us):
    """Выход TSOP38238: 0 на время пачки, 1 в паузе — расписание маяка станции."""
    for _ in range(cycles):
        for _name, on, off in SCHEDULE:
            pin.value(0)
            sleep_us(on)
            pin.value(1)
            sleep_us(off)


def beacon_loopback(beacon, pin, sleep_us=sleep_us, cycles=30):
    """Пачки с «приёмника» на проводе: каждый вход маяка должен насчитать cycles пачек левого и правого светодиода."""
    beacon.take()
    emulate_tsop(pin, cycles, sleep_us)
    counts = [list(c) for c in beacon.take()]
    names = ("left", "center", "right")
    silent = [n for n, c in zip(names, counts) if c == [0, 0]]
    ok = all(abs(c[0] - cycles) <= 2 and abs(c[1] - cycles) <= 2 for c in counts)
    return {"ok": ok, "counts": counts, "expect": cycles, "silent": silent}


def i2c_scan(i2c):
    found = {"0x%02x" % a: KNOWN.get(a, "неизвестное устройство") for a in sorted(i2c.scan())}
    return {"ok": True, "found": found}


def sensors(i2c, shunt_ohm, current_lsb_a, bmi_config=None):
    """Прочитать то, что нашлось: расстояние VL53L4CD, напряжение INA226, ускорение BMI270 (должно быть ~1 g)."""
    out, addrs = {"ok": True}, set(i2c.scan())
    if 0x29 in addrs:
        from vl53l4cd import VL53L4CD
        dev = VL53L4CD(i2c)
        dev.init(20)
        dev.start()
        dev.wait_ready()
        out["vl53l4cd_mm"], out["vl53l4cd_status"] = dev.measure()
    if 0x40 in addrs:
        from ina226 import INA226
        out["ina226_v"] = round(INA226(i2c, shunt_ohm=shunt_ohm, current_lsb_a=current_lsb_a).volts(), 3)
    if 0x68 in addrs and bmi_config is not None:
        from bmi270 import BMI270
        acc, _ = BMI270(i2c, bmi_config).read()
        out["bmi270"] = {"acc_g": [round(a, 3) for a in acc], "magnitude": round(sum(a * a for a in acc) ** 0.5, 3)}
    return out


class _NullPort:
    def read(self):
        return b""

    def write(self, data):
        pass


def loop_time(n=200, ticks_us=ticks_us):
    """Средний проход главного цикла Spine без устройств, мкс (бюджет — 5 мс)."""
    from spine import Spine
    sp = Spine(_NullPort(), {}, cfg={"telemetry_ms": 50})
    t0 = ticks_us()
    for _ in range(n):
        sp.step()
    us = ticks_diff(ticks_us(), t0) / n
    return {"ok": us < 5000, "step_us": round(us)}


def run():
    """Все проверки на плате (только MicroPython)."""
    import rp2  # noqa: F401 — проверка, что это RP2350, а не ПК
    from machine import I2C, UART, Pin

    import pins
    from beacon import Beacon
    from pio_uart import PioUart

    for name, bus in (("uart_a", pins.BUS_A), ("uart_b", pins.BUS_B)):
        emit(name, uart_loopback(UART(bus["uart"], baudrate=pins.BUS_BAUD, tx=Pin(bus["tx"]), rx=Pin(bus["rx"]), rxbuf=512)))
    pio = PioUart(pins.BUS_C["pio"], pins.BUS_C["tx"], pins.BUS_C["rx"], pins.BUS_BAUD)
    emit("pio_bytes", uart_loopback(pio))
    emit("pio_burst", pio_burst(pio))
    out = Pin(TSOP_OUT, Pin.OUT, value=1)
    emit("beacon", beacon_loopback(Beacon(*(Pin(p, Pin.IN, Pin.PULL_UP) for p in (pins.IR_LEFT, pins.IR_CENTER, pins.IR_RIGHT))), out))
    i2c = I2C(pins.I2C_ID, sda=Pin(pins.SDA), scl=Pin(pins.SCL), freq=pins.I2C_HZ)
    emit("i2c", i2c_scan(i2c))
    try:
        with open("bmi270_config.bin", "rb") as f:
            cfg = f.read()
    except OSError:
        cfg = None
    try:
        emit("sensors", sensors(i2c, pins.SHUNT_OHM, pins.CURRENT_LSB_A, cfg))
    except Exception as e:                             # датчик ответил, но не так — это и есть находка
        emit("sensors", {"ok": False, "error": repr(e)})
    emit("loop", loop_time())
    sleep_ms(10)
    emit("done", {"ok": True})


if __name__ == "__main__":
    run()
