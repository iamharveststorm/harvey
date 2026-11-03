"""«Спинной мозг» целиком на имитации: команды от Pi, рефлексы, телеметрия, события."""
import pytest

import edge
from fakes import FakeBus, FakeI2C, FakePin, FakePort, FakeVL53L4CD
from spine import GOAL_POS, Spine

NAMES = ("FL", "FR", "BL", "BR", "L", "R")
CFG = {"bat_low": 6.8, "bat_critical": 6.4, "telemetry_ms": 50, "edge_names": NAMES}


class Clock:
    def __init__(self):
        self.t = 1000

    def __call__(self):
        return self.t


class Imu:
    def __init__(self):
        self.acc, self.gyr = (0.0, 0.0, 1.0), (0.0, 0.0, 0.0)

    def read(self):
        return self.acc, self.gyr


class Ina:
    def __init__(self, volts=7.6, amps=0.8):
        self.v, self.a = volts, amps

    def volts(self):
        return self.v

    def amps(self):
        return self.a


class Beacon:
    def __init__(self):
        self.next = ((0, 0), (0, 0), (0, 0))

    def take(self):
        return self.next


def make(**kw):
    pins = [FakePin(0) for _ in NAMES]
    devs = [FakeVL53L4CD(p, dist=80) for p in pins]
    arr = edge.EdgeArray(FakeI2C(*devs), pins, NAMES)
    arr.calibrate(rounds=2, wait_ms=0)
    clock = Clock()
    parts = dict(port=FakePort(), buses={"A": FakeBus(), "B": FakeBus(), "C": FakeBus()}, edge=arr, imu=Imu(),
                 ina=Ina(), beacon=Beacon(), cfg=CFG, clock=clock)
    parts.update(kw)
    sp = Spine(**parts)
    return sp, parts, devs, clock


def step(sp, clock, ms=10, n=1):
    for _ in range(n):
        clock.t += ms
        sp.step()


def test_joint_targets_go_to_their_buses_and_are_clamped():
    sp, p, _, clock = make()
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 2000, "42": 5000, "91": -3, "7": 100}})
    step(sp, clock)
    assert p["buses"]["A"].sync == [(GOAL_POS, {11: 2000})]
    assert p["buses"]["B"].sync == [(GOAL_POS, {42: 4095})]
    assert p["buses"]["C"].sync == [(GOAL_POS, {91: 0})]


def test_edge_ahead_stops_forward_motion_once_and_allows_backing_off():
    sp, p, devs, clock = make()
    devs[0].dist = 200                                                # обрыв впереди-слева
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 2100}}, {"t": "j", "v": [40, 0, 0], "q": {"11": 2110}})
    step(sp, clock)
    assert p["buses"]["A"].sync == []
    assert [m["info"] for m in p["port"].of("ev", "edge")] == [["FL"]]  # событие одно, а не на каждую команду
    p["port"].push({"t": "j", "v": [-40, 0, 0], "q": {"11": 2050}})
    step(sp, clock)
    assert p["buses"]["A"].sync == [(GOAL_POS, {11: 2050})]


def test_lifted_robot_relaxes_all_buses():
    sp, p, devs, clock = make()
    for d in devs:
        d.status_raw = 23                                             # стол не видят все шесть
    step(sp, clock)
    assert all(b.released == 1 for b in p["buses"].values())
    assert len(p["port"].of("ev", "lifted")) == 1
    step(sp, clock)
    assert len(p["port"].of("ev", "lifted")) == 1 and p["buses"]["A"].released == 1


def test_free_fall_relaxes_and_reports():
    sp, p, _, clock = make()
    p["imu"].acc = (0.0, 0.0, 0.05)
    step(sp, clock, ms=20, n=3)
    assert p["port"].of("ev", "fall") and p["buses"]["B"].released == 1


def test_relax_survives_a_dead_bus():
    sp, p, _, clock = make(buses={"A": FakeBus(fail=True), "B": FakeBus()})
    p["port"].push({"t": "relax"})
    step(sp, clock)
    assert p["buses"]["B"].released == 1 and p["port"].of("err")


def test_battery_events_and_sitting_allows_only_standing_still():
    sp, p, _, clock = make(ina=Ina(volts=6.6))
    step(sp, clock, ms=100)
    assert p["port"].of("ev", "bat_low")[0]["info"] == 6.6
    p["ina"].v = 6.3
    step(sp, clock, ms=100)
    assert p["port"].of("ev", "bat_critical")
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 1}}, {"t": "j", "v": [0, 0, 0], "q": {"12": 2}})
    step(sp, clock)
    assert p["buses"]["A"].sync == [(GOAL_POS, {12: 2})]


def test_docking_is_reported_when_charge_current_flows():
    sp, p, _, clock = make(ina=Ina(amps=-1.4))
    step(sp, clock, ms=100)
    step(sp, clock, ms=100)
    assert [m["info"] for m in p["port"].of("ev", "docked")] == [-1.4]


def test_telemetry_twenty_times_a_second():
    sp, p, devs, clock = make()
    p["beacon"].next = ((20, 20), (25, 0), (5, 5))
    step(sp, clock, ms=10, n=30)                                      # 300 мс
    tel = p["port"].of("tel")
    assert len(tel) == 6
    last = tel[-1]
    assert last["edge"] == [80] * 6 and last["far"] == [0] * 6 and last["bat"] == [7.6, 0.8]
    assert last["beacon"] == "left" and last["ir"] == [[20, 20], [25, 0], [5, 5]] and last["tilt"] == [0.0, 0.0]
    assert last["axis"] == "left"


def test_hello_reports_missing_devices():
    sp, p, _, clock = make(imu=None, beacon=None)
    sp.handle({"t": "hello"})
    assert p["port"].of("hello")[0]["missing"] == ["imu", "beacon"]


def test_runs_with_no_sensors_at_all():
    port = FakePort()
    sp = Spine(port, {"A": FakeBus()}, cfg=CFG, clock=Clock())
    port.push({"t": "j", "v": [40, 0, 0], "q": {"11": 2048}}, {"t": "cal"})
    sp.clock.t += 100
    sp.step()
    assert sp.buses["A"].sync and port.of("tel")
    assert set(sp.missing()) == {"edge", "imu", "ina", "beacon"}


def test_cal_command_returns_new_baseline():
    sp, p, devs, clock = make()
    for d in devs:
        d.dist = 95
    p["port"].push({"t": "cal"})
    step(sp, clock)
    assert p["port"].of("cal")[0]["base"] == [95] * 6


@pytest.mark.parametrize("msg", [{"t": "unknown"}, {"t": "j"}])
def test_odd_messages_do_not_crash(msg):
    sp, p, _, clock = make()
    p["port"].push(msg)
    step(sp, clock)


def test_relaxed_flag_in_telemetry():
    sp, p, _, clock = make()
    p["port"].push({"t": "relax"})
    step(sp, clock, ms=60)
    assert p["port"].of("tel")[-1]["relaxed"] == 1
    p["port"].push({"t": "j", "v": [0, 0, 0], "q": {"11": 2048}})
    step(sp, clock, ms=60)
    assert p["port"].of("tel")[-1]["relaxed"] == 0


def test_battery_event_only_when_level_changes():
    sp, p, _, clock = make(ina=Ina(volts=6.6))
    step(sp, clock, ms=100, n=3)
    assert len(p["port"].of("ev", "bat_low")) == 1
    p["ina"].v = 7.5
    step(sp, clock, ms=100)
    p["ina"].v = 6.6
    step(sp, clock, ms=100)
    assert len(p["port"].of("ev", "bat_low")) == 2


def test_docked_needs_current_below_minus_50_ma():
    sp, p, _, clock = make(ina=Ina(amps=-0.05))
    step(sp, clock, ms=100)
    assert not p["port"].of("ev", "docked") and not sp.docked
    p["ina"].a = -0.06
    step(sp, clock, ms=100)
    p["ina"].a = 0.5
    step(sp, clock, ms=100)
    p["ina"].a = -0.5
    step(sp, clock, ms=100)
    assert len(p["port"].of("ev", "docked")) == 2                     # сошёл и снова встал на станцию


def test_edge_event_again_after_moving_freely():
    sp, p, devs, clock = make()
    devs[0].dist = 200
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 1}})
    step(sp, clock)
    devs[0].dist = 80
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 2}})
    step(sp, clock)
    devs[0].dist = 200
    p["port"].push({"t": "j", "v": [40, 0, 0], "q": {"11": 3}})
    step(sp, clock)
    assert len(p["port"].of("ev", "edge")) == 2


def test_sitting_allows_exactly_deadband():
    sp, p, _, clock = make(ina=Ina(volts=6.0))
    step(sp, clock, ms=100)
    p["port"].push({"t": "j", "v": [5, -5, 5], "q": {"11": 7}})
    step(sp, clock)
    assert p["buses"]["A"].sync == [(GOAL_POS, {11: 7})]


def test_missing_edge_sensors_are_named():
    sp, p, devs, clock = make()
    sp.edge.missing = ["BL"]
    assert sp.missing() == ["edge_BL"]


def test_acceleration_rounded_to_milli_g():
    sp, p, _, clock = make()
    p["imu"].acc = (0.12345, 0.0, 0.98765)
    step(sp, clock, ms=60)
    assert p["port"].of("tel")[-1]["acc"] == [0.123, 0.0, 0.988]


def test_rotation_rate_in_telemetry_for_turning_by_angle():
    sp, p, _, clock = make()
    p["imu"].gyr = (1.04, -2.0, 45.26)
    step(sp, clock, ms=60)
    assert p["port"].of("tel")[-1]["gyr"] == [1.0, -2.0, 45.3]


def test_beacon_ahead_when_each_side_sees_a_led_even_if_one_sees_both():
    sp, p, _, clock = make()
    p["beacon"].next = ((33, 33), (33, 33), (0, 33))                # левый видит оба светодиода, правый — один
    step(sp, clock, ms=10, n=12)
    assert p["port"].of("tel")[-1]["beacon"] == "ahead"
