"""Логика без железа: датчики края, события IMU, маяк, протокол, рефлексы."""
import pytest

import beacon
import edge
import imu_events
import link
import reflex
from fakes import FakeI2C, FakePin, FakeVL53L4CD

NAMES = ("FL", "FR", "BL", "BR", "L", "R")


# ---------- край ----------
@pytest.mark.parametrize("dist, status, base, flag", [
    (80, 0, 80, False), (105, 0, 80, False), (106, 0, 80, True),
    (0, 12, 80, True), (0, 255, 80, True), (120, 1, 80, False),      # предупреждение сигмы — не край
    (500, 0, None, False),                                            # до калибровки края нет
])
def test_is_edge(dist, status, base, flag):
    assert edge.is_edge(dist, status, base, 25) is flag


def test_baseline_median_of_valid():
    assert edge.baseline([(80, 0), (82, 0), (300, 12), (79, 0)]) == 80
    assert edge.baseline([(0, 12)]) is None


def six(dists=(80,) * 6):
    pins = [FakePin(0) for _ in NAMES]
    devs = [FakeVL53L4CD(p, dist=d) for p, d in zip(pins, dists)]
    return FakeI2C(*devs), pins, devs


def test_edge_array_gives_each_sensor_its_address():
    i2c, pins, devs = six()
    arr = edge.EdgeArray(i2c, pins, NAMES, addr0=0x30)
    assert [d.addr for d in devs] == [0x30, 0x31, 0x32, 0x33, 0x34, 0x35]
    assert arr.missing == [] and all(p.value() == 1 for p in pins)


def test_edge_array_skips_silent_sensor():
    i2c, pins, devs = six()
    i2c.devices.remove(devs[2])
    arr = edge.EdgeArray(i2c, pins, NAMES)
    assert arr.missing == ["BL"] and pins[2].value() == 0 and arr.sensors[2] is None
    assert len(arr.read()) == 6


def test_edge_array_calibrates_then_flags_the_drop():
    i2c, pins, devs = six((80, 81, 79, 80, 70, 71))
    arr = edge.EdgeArray(i2c, pins, NAMES, margin_mm=25)
    assert arr.calibrate(rounds=3, wait_ms=0) == [80, 81, 79, 80, 70, 71]
    devs[0].dist, devs[5].status_raw = 140, 23                        # впереди-слева — обрыв, справа — пусто
    arr.read()
    assert arr.flags() == [True, False, False, False, False, True]



def test_baseline_ignores_objects_far_from_the_expected_table():
    near_tower = [(39, 0), (40, 0), (39, 0)]
    assert edge.baseline(near_tower, nominal=72, tol=15) == 72            # перед предметом — расчётное расстояние
    assert edge.baseline([(70, 0), (39, 0), (71, 0)], nominal=72, tol=15) == 71


def test_edge_array_calibration_in_front_of_an_object_keeps_the_table_distance():
    i2c, pins, devs = six((40, 81, 79, 80, 70, 71))
    arr = edge.EdgeArray(i2c, pins, NAMES, margin_mm=25, nominal=(80, 80, 80, 80, 70, 70))
    assert arr.calibrate(rounds=3, wait_ms=0) == [80, 81, 79, 80, 70, 71]

# ---------- IMU ----------
def test_tilt():
    assert imu_events.tilt((0, 0, 1)) == pytest.approx((0, 0))
    assert imu_events.tilt((0, 1, 0))[0] == pytest.approx(90)
    assert imu_events.tilt((-0.5, 0, 0.866))[1] == pytest.approx(30, abs=0.1)


def test_freefall_needs_30_ms():
    ev = imu_events.ImuEvents()
    assert ev.update((0, 0, 0.1), (0, 0, 0), 20)[0] == []
    assert ev.update((0, 0, 0.1), (0, 0, 0), 10)[0] == ["fall"]
    assert ev.update((0, 0, 0.1), (0, 0, 0), 10)[0] == []           # о событии — один раз
    ev.update((0, 0, 1), (0, 0, 0), 10)
    assert ev.fall_ms == 0


def test_shock_and_tip():
    ev = imu_events.ImuEvents()
    assert ev.update((0, 0, 2.6), (0, 0, 0), 10)[0] == ["shock"]
    assert ev.update((0, 0, 1), (0, 0, 301), 10)[0] == []            # удар продолжается — событие уже было
    ev.update((0, 0, 1), (0, 0, 0), 10)
    assert ev.update((0, 0, 1), (0, 0, 301), 10)[0] == ["shock"]     # новый удар после спокойного замера
    assert ev.update((0, 0.7, 0.7), (0, 0, 0), 10)[0] == ["tip"]     # 45°
    assert ev.update((0, 0.5, 0.866), (0, 0, 0), 10)[0] == []        # 30° — ещё стоит


# ---------- маяк ----------
@pytest.mark.parametrize("left, right, where", [(0, 0, "none"), (19, 0, "none"), (50, 48, "ahead"),
                                                (50, 20, "left"), (10, 40, "right"), (30, 20, "ahead")])
def test_bearing(left, right, where):
    assert beacon.bearing(left, right) == where


@pytest.mark.parametrize("width, code", [(600, "L"), (470, "L"), (1200, "R"), (1330, "R"), (200, None), (2500, None)])
def test_burst_length_tells_the_led(width, code):
    assert beacon.code_of(width) == code              # TSOP382: tpo = tpi ± 5/f0 = ±132 мкс (стр. 3)


def test_beacon_counts_codes_per_receiver_per_window(monkeypatch):
    monkeypatch.setattr(beacon, "Pin", FakePin)
    clock = [0]
    lp, cp, rp = FakePin(1), FakePin(1), FakePin(1)
    b = beacon.Beacon(lp, cp, rp, clock_us=lambda: clock[0])
    for _ in range(5):
        lp.burst(clock, 600)
        lp.burst(clock, 1200)
        cp.burst(clock, 620)
    rp.burst(clock, 1180)
    rp.burst(clock, 3000)                               # помеха — не пачка маяка
    assert b.take() == ((5, 5), (5, 0), (0, 1)) and b.take() == ((0, 0), (0, 0), (0, 0))


@pytest.mark.parametrize("left, right, side", [(30, 30, "on"), (30, 0, "left"), (2, 30, "right"), (3, 4, "none")])
def test_center_receiver_tells_which_side_of_the_station_axis(left, right, side):
    assert beacon.axis_side(left, right) == side


# ---------- протокол ----------
def test_encode_decode_roundtrip():
    msg = link.joints({11: 2048.7, 92: 100}, (40, 0, 0))
    assert link.encode(msg).endswith(b"\n") and b" " not in link.encode(msg)
    assert link.LineReader().feed(link.encode(msg)) == [{"t": "j", "v": [40, 0, 0], "q": {"11": 2048, "92": 100}}]


def test_line_reader_joins_chunks_and_skips_garbage():
    r = link.LineReader()
    data = b"\x00\xff garbage\n" + link.encode({"t": "hello"}) + b"[1,2]\n" + link.encode({"t": "relax"})
    out = []
    for i in range(0, len(data), 3):
        out += r.feed(data[i:i + 3])
    assert out == [{"t": "hello"}, {"t": "relax"}]


def test_line_reader_drops_endless_line():
    r = link.LineReader()
    r.feed(b"x" * (link.MAX_LINE + 1))
    assert r.buf == b"" and r.feed(link.encode({"t": "cal"})) == [{"t": "cal"}]


# ---------- рефлексы ----------
@pytest.mark.parametrize("sid, bus", [(11, "A"), (33, "A"), (41, "B"), (63, "B"), (71, "C"), (92, "C"), (5, None), (40, None)])
def test_bus_of(sid, bus):
    assert reflex.bus_of(sid) is bus


CLEAR = [False] * 6


@pytest.mark.parametrize("v, far, stop", [
    ((40, 0, 0), [True, False, False, False, False, False], True),    # вперёд, слева впереди обрыв
    ((-40, 0, 0), [True, False, False, False, False, False], False),  # назад — от края можно
    ((-40, 0, 0), [False, False, True, False, False, False], True),
    ((0, 30, 0), [False] * 4 + [True, False], True),                  # влево, слева пусто
    ((0, -30, 0), [False] * 4 + [True, False], False),
    ((0, 0, 20), [False, False, False, True, False, False], True),   # поворот у края — нельзя
    ((3, 0, 0), [True] * 5 + [False], False),                         # стоим (меньше 5 мм/с)
])
def test_blocked(v, far, stop):
    assert reflex.blocked(v, far) is stop


@pytest.mark.parametrize("volts, level", [(7.6, "ok"), (6.8, "ok"), (6.79, "low"), (6.39, "critical"), (0.0, "unknown")])
def test_battery_level(volts, level):
    assert reflex.battery_level(volts, 6.8, 6.4) == level


def test_decide_priorities():
    assert reflex.decide((40, 0, 0), [True] * 6, [], "ok") == "relax"            # подняли
    assert reflex.decide((0, 0, 0), CLEAR, ["fall"], "ok") == "relax"
    assert reflex.decide((40, 0, 0), [True] + [False] * 5, [], "critical") == "sit"
    assert reflex.decide((40, 0, 0), [True] + [False] * 5, [], "ok") == "stop"
    assert reflex.decide((40, 0, 0), CLEAR, ["shock"], "low") == "go"
