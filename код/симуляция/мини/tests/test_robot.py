"""Робот целиком: команда → походка → сообщение `j` → настоящий Spine (рефлексы) → шины → физика → телеметрия."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import mini_robot as mr  # noqa: E402


def drive(r, v, sec, pose="stand"):
    events = []
    for _ in range(int(sec / mr.TICK)):
        r.step({"v": v, "pose": pose})
        events += r.events
    return events


def test_calibration_gives_six_table_distances():
    r = mr.SimRobot()
    assert len(r.spine.edge.base) == 6 and all(b and 50 < b < 150 for b in r.spine.edge.base)


def test_telemetry_reaches_the_head_side():
    r = mr.SimRobot()
    drive(r, (0, 0, 0), 0.2)
    assert r.tel["t"] == "tel" and r.tel["far"] == [0] * 6 and r.tel["relaxed"] == 0


def test_spine_forwards_walking():
    r = mr.SimRobot()
    x0 = r.pose()[0]
    drive(r, (40, 0, 0), 3.0)
    assert 0.08 < r.pose()[0] - x0 < 0.14


def test_turning_goes_the_commanded_way():
    r = mr.SimRobot()
    drive(r, (0, 0, 30), 2.0)
    assert 40 < r.pose()[2] < 75


def test_walk_to_the_edge_is_stopped_by_the_spine():
    r = mr.SimRobot(start=(0.1, 0.0, 0.0))
    events = drive(r, (40, 0, 0), 8.0)
    assert "edge" in events and r.on_table()
    assert r.pose()[0] + mr.hm.BX1 < mr.TABLE[1]


def test_lifted_robot_relaxes():
    r = mr.SimRobot()
    drive(r, (0, 0, 0), 0.2)
    r.lift(0.5)
    assert "lifted" in r.lift_events and r.tel["relaxed"] == 1


def test_charging_needs_the_belly_on_the_contacts():
    r = mr.SimRobot(dock_pos=(0.0, 0.0))
    drive(r, (0, 0, 0), 0.3)
    assert not r.charging()
    drive(r, (0, 0, 0), 1.5, pose="lie")
    assert r.charging()


def test_charging_only_when_each_contact_is_under_its_brass_plate():
    def lying(dy, dx=0.0):
        r = mr.SimRobot(dock_pos=(0.0, 0.0), start=(dx, dy, 0.0))
        drive(r, (0, 0, 0), 1.5, pose="lie")
        return r.charging()
    assert lying(0.002) and lying(0.0, 0.012)
    assert not lying(0.008) and not lying(0.0, 0.025)


def test_switched_on_facing_an_object_does_not_take_the_table_for_an_edge():
    r = mr.SimRobot(table=(-0.3, 0.6, -0.3, 0.3), dock_pos=(0.0, 0.0), start=(0.25, 0.0, 180.0))   # носом к башенке
    assert r.spine.edge.base[:2] == [72, 72]                              # не 39 мм до стенки башенки
    events = drive(r, (-30, 0, 0), 1.5)                                  # отойти от башенки: под носом снова стол
    assert "edge" not in events and r.tel["far"] == [0] * 6
