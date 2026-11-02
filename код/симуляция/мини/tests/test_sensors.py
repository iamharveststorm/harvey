"""Датчики мини в симуляции для настоящей прошивки RP2350: края, IMU, ИК-маяк, шины приводов, «зрение» руки."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import harvey_mini as hm  # noqa: E402
import mini_sensors as ms  # noqa: E402
import beacon  # noqa: E402  — из прошивки (ms.FIRMWARE в sys.path)
import edge  # noqa: E402
import pins  # noqa: E402
import vl53l4cd  # noqa: E402

TABLE = (-0.3, 0.3, -0.3, 0.3)
DOCK = (0.20, 0.0)


class Pin:
    def __init__(self):
        self.level = 0

    def value(self, v=None):
        if v is None:
            return self.level
        self.level = v


def sim_at(x=0.0, y=0.0, yaw=0.0, dock=None, hand=None, settle=0.4):
    s = hm.Mini(xml=ms.world_xml(TABLE, dock, hand))
    ms.place(s, x, y, yaw)
    s.run(settle, record=False)
    return s


def edge_array(s):
    return edge.EdgeArray(None, [Pin() for _ in pins.EDGE_NAMES], pins.EDGE_NAMES, make=ms.tof_factory(s))


# ---------- датчики края ----------
def test_tof_on_flat_table_matches_ray_geometry():
    s = sim_at()
    make = ms.tof_factory(s)
    tb = s.d.body("torso")
    R = tb.xmat.reshape(3, 3)
    sensors = [make(None) for _ in ms.EDGE_RAYS]
    for i, ((o, v), sensor) in enumerate(zip(ms.EDGE_RAYS, sensors)):
        dist, status = sensor.measure()
        ow = tb.xpos + R @ np.array(o)
        dw = R @ (np.array(v) / np.linalg.norm(v))
        expected = ow[2] / -dw[2] * 1000
        assert status == vl53l4cd.VALID and dist == pytest.approx(expected, abs=2), pins.EDGE_NAMES[i]


def test_front_sensors_see_the_table_edge_and_back_ones_do_not():
    s = sim_at()
    arr = edge_array(s)
    arr.calibrate(rounds=2, wait_ms=0)
    ms.place(s, TABLE[1] - 0.040 - hm.BX1, 0.0, 0.0)
    arr.read()
    assert arr.flags() == [True, True, False, False, False, False]


def test_tof_reports_no_target_beyond_its_range():
    s = sim_at()
    ms.place(s, TABLE[1] - 0.040 - hm.BX1, 0.0, 0.0)
    make = ms.tof_factory(s)
    assert make(None).measure()[1] == vl53l4cd.SIGNAL_TOO_WEAK


# ---------- IMU ----------
def test_imu_at_rest_reads_one_g_up_and_no_rotation():
    s = sim_at(settle=1.0)
    acc, gyr = ms.SimImu(s).read()
    assert acc == pytest.approx((0, 0, 1), abs=0.05)
    assert max(abs(g) for g in gyr) < 2.0


# ---------- ИК-маяк ----------
def counts(yaw, x=DOCK[0] - 0.30, y=0.0):
    s = sim_at(x, y, yaw, dock=DOCK, settle=0.2)
    b = ms.SimBeacon(s, ms.led_world(DOCK))
    return b.take()


def test_beacon_straight_ahead_is_seen_by_both():
    left, right = counts(0.0)
    assert min(left, right) >= beacon.SEEN_MIN and beacon.bearing(left, right) == "ahead"


def test_beacon_70_degrees_left_is_seen_by_the_left_receiver_only():
    left, right = counts(-70.0)
    assert left >= beacon.SEEN_MIN and right == 0 and beacon.bearing(left, right) == "left"


def test_beacon_behind_the_receivers_is_not_seen():
    assert beacon.bearing(*counts(-125.0)) == "none"


def test_beacon_is_not_seen_from_behind_the_station():
    assert beacon.bearing(*counts(180.0, x=DOCK[0] + 0.30)) == "none"


@pytest.mark.parametrize("ee, angle, seen", [(0.30, 0, True), (0.20, 0, False), (31000.0, 0, False), (1.0, 95, False)])
def test_receiver_threshold_and_saturation(ee, angle, seen):
    assert ms.receiver_sees(ee, math.radians(angle)) is seen


# ---------- шины ----------
def test_servo_position_roundtrip():
    for a in (-1.2, -0.3, 0.0, 0.5, 1.4):
        assert ms.to_rad(ms.to_pos(a)) == pytest.approx(a, abs=2 * math.pi / 4096)


def test_servo_ids_follow_the_wiring_table():
    assert ms.SERVO_IDS["LF_c"] == 11 and ms.SERVO_IDS["RB_k"] == 63 and ms.SERVO_IDS["R_g"] == 84
    assert ms.SERVO_IDS["L_s"] == 91 and len(set(ms.SERVO_IDS.values())) == 28


def test_bus_moves_joints_and_relaxes():
    s = sim_at(settle=0.0)
    bus = ms.SimBus(s)
    bus.sync_write((42, 2), {12: ms.to_pos(0.4)})
    assert s.q["LF_f"] == pytest.approx(0.4, abs=0.002) and not s.relaxed
    bus.release_all()
    assert s.relaxed


# ---------- «зрение»: рука в кадре ----------
def test_hand_straight_ahead_is_seen_at_its_distance():
    s = sim_at(hand=(0.0662 + 0.30, 0.0))
    v = ms.see_hand(s)
    assert v is not None and v["dist_mm"] == pytest.approx(300, abs=15) and abs(v["bearing_deg"]) < 2


def test_hand_behind_is_not_seen():
    assert ms.see_hand(sim_at(hand=(-0.25, 0.0))) is None


def test_hand_outside_the_frame_is_not_seen():
    assert ms.see_hand(sim_at(hand=(0.10, 0.25))) is None
