"""Поведение: телеметрия и события «спинного мозга», «зрение» → команда корпусу. Без железа и без симуляции."""
import math

import pytest

from harvey_head.behavior import Behavior

DT = 0.05                                    # телеметрия 20 раз в секунду


def tel(far=(0,) * 6, beacon="none", edge=(70, 70, 72, 72, 104, 104), tilt=(0.0, 0.0)):
    return {"t": "tel", "far": list(far), "beacon": beacon, "edge": list(edge), "tilt": list(tilt), "bat": [7.4, 1.0]}


class Run:
    """Гоняет поведение во времени; мир — функции от прошедшего времени и накопленного поворота."""

    def __init__(self, goal=None):
        self.b, self.t, self.heading = Behavior(0.0), 0.0, 0.0
        self.cmds = []
        if goal:
            self.b.request(goal, 0.0)

    def go(self, sec, telem=lambda r: tel(), events=lambda r: [], vision=lambda r: None):
        for _ in range(round(sec / DT)):
            self.t += DT
            cmd = self.b.update(telem(self), events(self), vision(self), self.t)
            self.heading += cmd["v"][2] * DT
            self.cmds.append(cmd)
        return self.cmds[-1]


def test_starts_idle_and_still():
    cmd = Run().go(0.5)
    assert cmd["state"] == "idle" and cmd["v"] == (0, 0, 0) and cmd["pose"] == "stand"


# ---------- осмотреться ----------
def test_look_turns_a_full_circle_with_six_pauses_then_idles():
    r = Run("look")
    r.go(16.0)
    assert r.heading == pytest.approx(360, abs=2) and r.b.state == "idle"
    turning = [c["v"][2] != 0 for c in r.cmds]
    pauses = sum(1 for a, b in zip(turning, turning[1:]) if a and not b)
    assert pauses == 6


def test_look_switches_to_the_hand_when_it_comes_into_view():
    r = Run("look")
    r.go(1.0)
    cmd = r.go(0.1, vision=lambda r: {"bearing_deg": 20.0, "dist_mm": 300})
    assert cmd["state"] == "hand"


# ---------- подойти к руке ----------
def test_hand_far_off_to_the_side_turns_on_the_spot():
    cmd = Run("hand").go(0.1, vision=lambda r: {"bearing_deg": -35.0, "dist_mm": 300})
    assert cmd["v"][0] == 0 and cmd["v"][2] < 0


def test_hand_ahead_walks_and_steers_toward_it():
    cmd = Run("hand").go(0.1, vision=lambda r: {"bearing_deg": 5.0, "dist_mm": 300})
    assert cmd["v"][0] > 0 and cmd["v"][2] > 0


def test_hand_close_stops():
    cmd = Run("hand").go(0.1, vision=lambda r: {"bearing_deg": 2.0, "dist_mm": 85})
    assert cmd["v"] == (0, 0, 0) and cmd["state"] == "at_hand"


def test_hand_lost_goes_back_to_looking_instead_of_walking_blind():
    r = Run("hand")
    r.go(0.5, vision=lambda r: {"bearing_deg": 0.0, "dist_mm": 300})
    cmd = r.go(0.3)
    assert cmd["v"] == (0, 0, 0)
    assert r.go(0.4)["state"] == "look"


# ---------- край стола ----------
def test_edge_ahead_backs_away_then_turns_round_then_resumes():
    r = Run("look")
    front = (1, 1, 0, 0, 0, 0)
    cmd = r.go(0.2, telem=lambda r: tel(far=front), events=lambda r: ["edge"])
    assert cmd["state"] == "edge" and cmd["v"][0] < 0 and cmd["v"][2] == 0
    r.go(0.45)                                              # край ушёл из-под датчиков — ещё немного назад
    h0 = r.heading
    r.go(4.0)
    assert r.heading - h0 == pytest.approx(120, abs=5)
    assert r.go(0.2)["state"] == "look"


def test_edge_behind_goes_forward():
    cmd = Run("look").go(0.1, telem=lambda r: tel(far=(0, 0, 1, 1, 0, 0)), events=lambda r: ["edge"])
    assert cmd["v"][0] > 0


def test_edge_on_the_left_steps_right():
    cmd = Run("look").go(0.1, telem=lambda r: tel(far=(0, 0, 0, 0, 1, 0)), events=lambda r: ["edge"])
    assert cmd["v"][1] < 0 and cmd["v"][0] == 0


def test_edge_while_going_home_restarts_the_search_afterwards():
    r = Run("home")
    r.go(0.1, telem=lambda r: tel(far=(1, 1, 0, 0, 0, 0)), events=lambda r: ["edge"])
    r.go(6.0)
    assert r.b.state == "home_search"


# ---------- подняли ----------
def test_lifted_stays_still_until_back_on_the_table_then_looks_around():
    r = Run("hand")
    cmd = r.go(0.5, telem=lambda r: tel(far=(1,) * 6), events=lambda r: ["lifted"] if r.t < 0.06 else [])
    assert cmd["state"] == "lifted" and cmd["v"] == (0, 0, 0)
    assert r.go(0.5)["state"] == "lifted"
    assert r.go(0.7)["state"] == "look"


def test_bat_low_goes_home():
    cmd = Run("look").go(0.1, events=lambda r: ["bat_low"])
    assert cmd["state"].startswith("home")


# ---------- домой по маяку ----------
def beacon_at(target):
    """Маяк виден обоими приёмниками в ±40° от курса, одним — до ±70°."""
    def f(r):
        b = (target - r.heading + 180) % 360 - 180
        if abs(b) <= 40:
            return tel(beacon="ahead")
        if abs(b) <= 70:
            return tel(beacon="left" if b > 0 else "right")
        return tel(beacon="none")
    return f


@pytest.mark.parametrize("target", [-150, -60, -20, 0, 25, 65, 170])
def test_home_turns_to_face_the_beacon(target):
    r = Run("home")
    world = beacon_at(target)
    for _ in range(600):
        r.go(DT, telem=world)
        if r.b.state == "home_approach":
            break
    assert r.b.state == "home_approach"
    assert (target - r.heading + 180) % 360 - 180 == pytest.approx(0, abs=4)


def test_home_without_a_beacon_gives_up_after_a_full_circle():
    r = Run("home")
    r.go(14.0)
    assert r.b.state == "home_lost" and r.cmds[-1]["v"] == (0, 0, 0) and 330 < r.heading < 400


def pad_then_tower(r):
    """Под передними датчиками: стол, площадка (−12 мм), снова стол, потом стенка башенки всё ближе."""
    t = r.t - r.t_approach
    if t < 1.0:
        d = 70
    elif t < 2.5:
        d = 58
    elif t < 4.0:
        d = 70
    else:
        d = 70 - 6 * (t - 4.0) / 0.5
    return tel(beacon="ahead", edge=(d, d, 72, 72, 104, 104))


def approach(r):
    r.go(0.05, telem=beacon_at(0))
    while r.b.state != "home_approach":
        r.go(DT, telem=beacon_at(0))
    r.t_approach = r.t


def test_home_stops_over_the_contacts_after_pad_then_tower_and_lies_down():
    r = Run("home")
    approach(r)
    r.go(4.3, telem=pad_then_tower)
    assert r.cmds[-1]["v"][0] > 0                          # площадка прошла, башенка ещё не видна
    r.go(0.4, telem=pad_then_tower)
    back = r.go(0.2, telem=pad_then_tower)
    assert back["v"][0] < 0                                # проехал — чуть назад
    cmd = r.go(1.0, telem=pad_then_tower)
    assert cmd["pose"] == "lie" and cmd["v"] == (0, 0, 0)


def lie_down(r):
    approach(r)
    while r.cmds[-1]["pose"] != "lie":
        r.go(DT, telem=pad_then_tower)


def test_docked_event_ends_the_trip():
    r = Run("home")
    lie_down(r)
    cmd = r.go(0.5, events=lambda r: ["docked"])
    assert cmd["state"] == "docked" and cmd["pose"] == "lie"


def test_no_charge_after_lying_retries_once_then_fails():
    r = Run("home")
    lie_down(r)
    r.go(3.2)
    retry = r.go(0.2)
    assert retry["pose"] == "stand" and retry["v"][0] < 0
    r.go(2.2)
    assert r.b.state == "home_search"
    lie_down(r)
    r.go(3.4)
    assert r.b.state == "home_failed" and r.cmds[-1]["v"] == (0, 0, 0)


def test_turn_rate_is_gentle():
    r = Run("look")
    r.go(3.0)
    assert max(abs(c["v"][2]) for c in r.cmds) <= 45 and not math.isnan(r.heading)
