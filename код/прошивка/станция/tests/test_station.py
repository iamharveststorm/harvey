"""Маяк станции: расписание пачек двух светодиодов — по требованиям TSOP382 и так, как их различает Харви."""
import sys
from pathlib import Path

import pytest


def _dir(rel):
    for base in (Path(__file__).absolute(), Path(__file__).resolve()):
        for parent in base.parents:
            if (parent / rel).exists():
                return parent / rel
    raise FileNotFoundError(rel)


sys.path.insert(0, str(_dir("код/прошивка/станция")))
sys.path.insert(1, str(_dir("код/прошивка/rp2350")))
import beacon  # noqa: E402 — как Харви различает пачки
import beacon_station as bs  # noqa: E402

PERIOD_US = 1e6 / bs.CARRIER_HZ


class Led:
    def __init__(self, name, log, clock):
        self.name, self.log, self.clock = name, log, clock

    def duty_u16(self, d):
        self.log.append((self.clock[0], self.name, d))


def timeline(cycles=3):
    clock, log = [0], []
    leds = {n: Led(n, log, clock) for n in "LR"}

    def sleep_us(us):
        clock[0] += us
    bs.run(leds, sleep_us, cycles=cycles)
    return log, clock[0]


def test_left_and_right_take_turns_with_their_own_burst_length():
    log, _ = timeline()
    pulses = []
    start = {}
    for t, n, d in log:
        if d:
            start[n] = t
        else:
            pulses.append((n, t - start.pop(n)))
    assert [n for n, _ in pulses] == ["L", "R"] * 3
    assert all(beacon.code_of(w) == n for n, w in pulses)


def test_never_both_leds_at_once():
    log, _ = timeline()
    lit = set()
    for _, n, d in log:
        lit = lit | {n} if d else lit - {n}
        assert len(lit) <= 1


def test_tsop382_limits():
    # TSOP382: пачка ≥ 10 периодов, пауза ≥ 12 периодов, не больше 1700 пачек в секунду (документы/TSOP382 — даташит Vishay.pdf)
    log, total = timeline(cycles=10)
    assert all(on / PERIOD_US >= 10 and off / PERIOD_US >= 12 for _, on, off in bs.SCHEDULE)
    assert 20 / (total / 1e6) <= 1700


def test_each_led_sends_enough_bursts_per_robot_window():
    per_s = 1e6 / sum(on + off for _, on, off in bs.SCHEDULE)
    assert per_s * 0.1 >= 3 * beacon.SEEN_CODE                       # окно счёта Харви — 100 мс


def test_carrier_is_38_khz_at_a_third():
    assert bs.CARRIER_HZ == 38000 and bs.DUTY == pytest.approx(65535 / 3, abs=1)
