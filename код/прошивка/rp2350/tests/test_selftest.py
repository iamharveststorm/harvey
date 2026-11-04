"""Стенд без приводов: самопроверка платы (петли UART, маяк через «приёмник» на проводе, I2C, время цикла)."""
import struct

import beacon
import selftest
import vl53l4cd
from fakes import FakeI2C, FakeINA226, FakePin, FakeVL53L4CD


class LoopUart:
    """UART с перемычкой TX → RX: что отправлено, то и пришло (порвана — ничего не приходит; шум — портит байт)."""

    def __init__(self, broken=False, flip=None):
        self.buf, self.broken, self.flip, self.n = bytearray(), broken, flip, 0

    def write(self, data):
        for b in data:
            self.n += 1
            if not self.broken:
                self.buf.append(b ^ 0x01 if self.n == self.flip else b)
        return len(data)

    def any(self):
        return len(self.buf)

    def read(self, n=None):
        out, self.buf = bytes(self.buf), bytearray()
        return out


def test_uart_loopback_ok():
    r = selftest.uart_loopback(LoopUart(), sleep_us=lambda us: None)
    assert r["ok"] and r["got"] == r["sent"] == len(selftest.PATTERN) and r["bad"] == 0


def test_uart_loopback_without_jumper():
    r = selftest.uart_loopback(LoopUart(broken=True), sleep_us=lambda us: None)
    assert not r["ok"] and r["got"] == 0


def test_uart_loopback_counts_bad_bytes():
    r = selftest.uart_loopback(LoopUart(flip=10), sleep_us=lambda us: None)
    assert not r["ok"] and r["bad"] == 1


class FifoSM:
    """Машина состояний PIO: очередь 4 слова."""

    def __init__(self):
        self.q = []

    def tx_fifo(self):
        return len(self.q)

    def rx_fifo(self):
        return len(self.q)

    def put(self, v):
        assert len(self.q) < 4, "очередь передачи переполнена — put заблокировал бы цикл"
        self.q.append(v)

    def get(self):
        return self.q.pop(0)


class FakePio:
    """PIO-UART с перемычкой: байт из очереди передачи попадает в очередь приёма (тоже 4 слова), лишнее теряется."""

    def __init__(self, slow_reader=False):
        self.tx, self.rx, self.lost, self.slow = FifoSM(), FifoSM(), 0, slow_reader

    def wire(self):
        while self.tx.q:
            b = self.tx.q.pop(0)
            if len(self.rx.q) < 4:
                self.rx.q.append(b << 24)
            else:
                self.lost += 1


def test_pio_burst_reads_while_sending_at_full_speed():
    pio = FakePio()
    r = selftest.pio_burst(pio, n=64, tick=pio.wire)
    assert r["ok"] and r["got"] == 64 and r["bad"] == 0


def test_pio_burst_notices_lost_bytes():
    pio = FakePio()
    sent = [0]

    def lossy():                                          # каждый 10-й байт пропал: программа не успела забрать
        while pio.tx.q:
            b = pio.tx.q.pop(0)
            sent[0] += 1
            if sent[0] % 10:
                pio.rx.q.append(b << 24)
    r = selftest.pio_burst(pio, n=64, tick=lossy)
    assert not r["ok"] and r["got"] < 64


# ---------- маяк: вывод платы изображает TSOP ----------
class Wire:
    """Перемычка от вывода-«приёмника» ко входам маяка: смена уровня — прерывание на каждом входе."""

    def __init__(self, *inputs):
        self.inputs = inputs

    def value(self, v):
        for p in self.inputs:
            p.level = v
            p.handler(p)


def test_beacon_loopback_counts_both_leds_on_every_receiver(monkeypatch):
    monkeypatch.setattr(beacon, "Pin", FakePin)
    clock = [0]
    pins_in = [FakePin(1) for _ in range(3)]
    b = beacon.Beacon(*pins_in, clock_us=lambda: clock[0])

    def sleep_us(us):
        clock[0] += us
    r = selftest.beacon_loopback(b, Wire(*pins_in), sleep_us, cycles=30)
    assert r["ok"] and r["counts"] == [[30, 30]] * 3


def test_beacon_loopback_reports_a_receiver_that_got_nothing(monkeypatch):
    monkeypatch.setattr(beacon, "Pin", FakePin)
    clock = [0]
    pins_in = [FakePin(1) for _ in range(3)]
    b = beacon.Beacon(*pins_in, clock_us=lambda: clock[0])

    def sleep_us(us):
        clock[0] += us
    r = selftest.beacon_loopback(b, Wire(pins_in[0], pins_in[2]), sleep_us, cycles=30)
    assert not r["ok"] and r["counts"][1] == [0, 0] and r["silent"] == ["center"]


# ---------- I2C ----------
def test_i2c_scan_names_the_known_devices():
    xshut = FakePin(1)
    i2c = FakeI2C(FakeVL53L4CD(xshut, dist=80), FakeINA226(volts=7.4))
    r = selftest.i2c_scan(i2c)
    assert r["found"] == {"0x29": "VL53L4CD (адрес по умолчанию)", "0x40": "INA226"} and r["ok"]


def test_sensors_read_what_is_there():
    xshut = FakePin(1)
    i2c = FakeI2C(FakeVL53L4CD(xshut, dist=80), FakeINA226(volts=7.4))
    r = selftest.sensors(i2c, shunt_ohm=0.010, current_lsb_a=0.00025)
    assert r["vl53l4cd_mm"] == 80 and abs(r["ina226_v"] - 7.4) < 0.01 and "bmi270" not in r


def test_empty_i2c_bus_is_not_an_error_but_is_said():
    r = selftest.i2c_scan(FakeI2C())
    assert r["ok"] and r["found"] == {}


def test_loop_time_of_the_spine_without_devices():
    times = iter(range(0, 100000, 2))
    r = selftest.loop_time(n=50, ticks_us=lambda: next(times))
    assert r["ok"] and r["step_us"] < 5000


def test_report_lines_are_json(capsys):
    selftest.emit("uart_a", {"ok": True, "got": 3})
    out = capsys.readouterr().out.strip()
    assert out == '{"check":"uart_a","ok":true,"got":3}'
    assert struct and vl53l4cd
