"""Границы порогов и точность переноса драйверов — то, что нашёл mutator."""
import struct

import pytest

import beacon
import imu_events
import link
import reflex
import vl53l4cd
from fakes import FakeI2C, FakePin, FakeVL53L4CD


# ---------- IMU: ровно на пороге — ещё не событие ----------
def test_magnitude():
    assert imu_events.magnitude((1, 2, 2)) == 3 and imu_events.magnitude((-3, 0, 4)) == 5


def test_thresholds_are_strict():
    ev = imu_events.ImuEvents()
    assert ev.update((0, 0, 0.35), (0, 0, 0), 50)[0] == []           # ровно 0,35 g — не падение
    assert ev.update((0, 0, 2.5), (0, 0, 0), 10)[0] == []            # ровно 2,5 g — не удар
    assert ev.update((0, 0, 1), (0, 0, 300), 10)[0] == []
    s, c = 0.573576, 0.819152                                         # sin / cos 35°
    assert ev.update((0, s, c), (0, 0, 0), 10)[0] == []              # ровно 35° — ещё стоит
    assert ev.update((0, 0.58, 0.81), (0, 0, 0), 10)[0] == ["tip"]
    assert imu_events.ImuEvents().fall_ms == 0


# ---------- рефлексы: ровно 5 мм/с — стоим ----------
@pytest.mark.parametrize("v", [(5, 0, 0), (-5, 0, 0), (0, 5, 0), (0, -5, 0), (0, 0, 5), (0, 0, -5), (0, 0, 0)])
def test_deadband_is_standing(v):
    assert not reflex.blocked(v, [True] * 5 + [True])


def test_right_side():
    far = [False] * 5 + [True]
    assert reflex.blocked((0, -6, 0), far) and not reflex.blocked((0, 6, 0), far) and not reflex.blocked((6, 0, 0), far)


@pytest.mark.parametrize("volts, level", [(0.5, "unknown"), (0.51, "critical"), (6.4, "low"), (6.8, "ok")])
def test_battery_boundaries(volts, level):
    assert reflex.battery_level(volts, 6.8, 6.4) == level


# ---------- протокол ----------
@pytest.mark.parametrize("line", [b'"t"', b"[\"t\"]", b"{}", b'{"x":1}'])
def test_decode_needs_object_with_type(line):
    assert link.decode(line) is None


def test_line_of_exactly_max_length_is_kept():
    r = link.LineReader()
    r.feed(b"x" * link.MAX_LINE)
    assert len(r.buf) == link.MAX_LINE


# ---------- маяк ----------
def test_beacon_visible_from_exactly_seen_min():
    assert beacon.bearing(20, 0) == "left" and beacon.bearing(0, 20) == "right" and beacon.bearing(19, 19) == "none"


# ---------- VL53L4CD: перенос пересчёта времени замера ----------
def adafruit_range_config(val, osc_freq):
    """Эталон: сеттер timing_budget из Adafruit CircuitPython_VL53L4CD (непрерывный режим), как есть."""
    timing_budget_us = val * 1000
    macro_period_us = int(2304 * (1073741824.0 / osc_freq)) >> 6
    timing_budget_us -= 2500
    out = []
    timing_budget_us <<= 12
    for mult in (16, 12):
        ms_byte = 0
        tmp = macro_period_us * mult
        ls_byte = int(((timing_budget_us + ((tmp >> 6) >> 1)) / (tmp >> 6)) - 1)
        while (ls_byte >> 8) & 0xFFFFFF > 0:
            ls_byte >>= 1
            ms_byte += 1
        out.append((ms_byte << 8) + (ls_byte & 0xFF))
    return tuple(out)


@pytest.mark.parametrize("budget", [10, 20, 33, 50, 100, 200])
@pytest.mark.parametrize("osc", [0x64, 0x1F4, 0xC8, 0x3E8])
def test_range_config_equals_adafruit(budget, osc):
    assert vl53l4cd.range_config(budget, osc) == adafruit_range_config(budget, osc)


def test_init_sets_continuous_mode_and_timing():
    dev = FakeVL53L4CD(FakePin(1))
    s = vl53l4cd.VL53L4CD(FakeI2C(dev))
    s.init(20)
    w = dict(dev.writes)
    a, b = adafruit_range_config(20, 0x0064)
    assert w[vl53l4cd.INTERMEASUREMENT_MS] == b"\x00\x00\x00\x00"
    assert w[vl53l4cd.RANGE_CONFIG_A] == struct.pack(">H", a) and w[vl53l4cd.RANGE_CONFIG_B] == struct.pack(">H", b)
    assert w[vl53l4cd.VHV_TIMEOUT_LOOP_BOUND] == b"\x09" and w[0x0024] == b"\x05\x00"


@pytest.mark.parametrize("mux", [0x11, 0x01])                        # прерывание активным 0 и активным 1
def test_ready_follows_interrupt_polarity(mux):
    dev = FakeVL53L4CD(FakePin(1))
    s = vl53l4cd.VL53L4CD(FakeI2C(dev))
    dev.mem[vl53l4cd.GPIO_HV_MUX_CTRL] = mux
    assert not s.ready()
    s.start()
    assert s.ready()
    s.measure()
    dev.pending = False
    assert not s.ready()


def test_wait_ready_times_out():
    dev = FakeVL53L4CD(FakePin(1))
    with pytest.raises(OSError):
        vl53l4cd.VL53L4CD(FakeI2C(dev)).wait_ready(timeout_ms=3)
