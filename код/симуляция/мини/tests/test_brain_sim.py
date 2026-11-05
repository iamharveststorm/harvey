"""Сессия «мозг ведёт Харви»: настоящая голова + прошивка RP2350 в SimRobot, мозг подменён сценарием по времени симуляции."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import mini_brain as mb  # noqa: E402


class ScriptedBrain:
    """Подделка мозга: сообщения выдаются, когда время симуляции дошло до их метки; offer копит телеметрию."""

    def __init__(self, script):
        self.script, self.robot, self.offered = sorted(script, key=lambda x: x[0]), None, []
        self.connected = True

    def poll(self):
        out = []
        while self.script and self.script[0][0] <= self.robot.t:
            out.append(self.script.pop(0)[1])
        return out

    def offer(self, msg):
        self.offered.append(msg)


def make_session(script, **kw):
    robot = mb.make_robot()
    brain = ScriptedBrain(script)
    brain.robot = robot
    return mb.Session(robot, brain, fast=True, **kw), robot, brain


def run_until(session, robot, pred, limit_s):
    log = []
    while robot.t < limit_s:
        session.step()
        log += session.events()
        if pred():
            break
    return log


def test_make_robot_has_table_dock_and_a_visible_hand():
    robot = mb.make_robot()
    v = robot.vision()
    assert v["hand"] is not None and v["hand"]["dist_mm"] < 400
    assert robot.dock_pos == mb.mb.DOCK and robot.on_table()


def test_goal_home_walks_to_the_station_and_docks():
    s, robot, _ = make_session([(0.5, {"t": "goal", "goal": "home"})])
    log = run_until(s, robot, lambda: s.state == "docked", 120.0)
    assert s.state == "docked" and robot.on_table()
    assert "Поведение: home_search" in log or any(e.startswith("Поведение: home") for e in log)
    assert "Поведение: docked" in log


def test_emote_shows_in_events():
    s, robot, _ = make_session([(0.2, {"t": "emote", "name": "happy", "s": 3})])
    log = run_until(s, robot, lambda: False, 1.0)
    assert "Глаза: happy" in log


def test_second_command_cancels_the_first():
    s, robot, _ = make_session([(0.5, {"t": "goal", "goal": "home"}), (2.5, {"t": "goal", "goal": "idle"})])
    run_until(s, robot, lambda: False, 4.0)
    assert s.state == "idle"


def test_brain_going_down_mid_way_does_not_stop_the_walk():
    s, robot, _ = make_session([(0.5, {"t": "goal", "goal": "home"}), (3.0, {"t": "link", "brain": "down"})])
    log = run_until(s, robot, lambda: s.state == "docked", 120.0)
    assert s.state == "docked"
    assert "Мозг: не на связи" in log


def test_telemetry_goes_to_the_brain():
    s, robot, brain = make_session([])
    run_until(s, robot, lambda: False, 2.0)
    assert any(m.get("t") == "tel" for m in brain.offered)


def test_without_brain_says_so_once():
    s, robot, brain = make_session([])
    brain.connected = False
    log = run_until(s, robot, lambda: False, 3.0)
    assert log.count("Мозг: не на связи") == 1


def test_real_time_pacing_sleeps_when_sim_is_ahead():
    sleeps, wall = [], [0.0]

    def sleep(x):
        sleeps.append(x)
        wall[0] += x
    robot = mb.make_robot()
    brain = ScriptedBrain([])
    brain.robot = robot
    s = mb.Session(robot, brain, now_fn=lambda: wall[0], sleep_fn=sleep)
    for _ in range(int(0.5 / mb.mb.mr.TICK)):
        s.step()
    assert sleeps and all(x > 0 for x in sleeps) and sum(sleeps) == pytest.approx(0.5, abs=0.05)


def test_fast_never_sleeps():
    sleeps = []
    robot = mb.make_robot()
    brain = ScriptedBrain([])
    brain.robot = robot
    s = mb.Session(robot, brain, now_fn=lambda: 0.0, sleep_fn=sleeps.append, fast=True)
    for _ in range(100):
        s.step()
    assert sleeps == []
