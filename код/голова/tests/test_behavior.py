"""Поведение: телеметрия и события «спинного мозга», «зрение» → команда корпусу. Без железа и без симуляции."""
import math

import pytest

from harvey_head.behavior import Behavior

DT = 0.05                                    # телеметрия 20 раз в секунду


def tel(far=(0,) * 6, beacon="none", edge=(70, 70, 72, 72, 104, 104), tilt=(0.0, 0.0)):
    return {"t": "tel", "far": list(far), "beacon": beacon, "edge": list(edge), "tilt": list(tilt), "bat": [7.4, 1.0]}


class Run:
    """Гоняет поведение во времени; мир — функции от прошедшего времени и накопленного поворота.
    Корпус поворачивается ровно с заданной скоростью, гироскоп в телеметрии её и показывает."""

    def __init__(self, goal=None):
        self.b, self.t, self.heading, self.wz = Behavior(0.0), 0.0, 0.0, 0.0
        self.x, self.y, self.slip = 0.0, 0.0, 0.0       # мм в системе станции; slip — снос вбок, мм/с
        self.gain, self.drift = 1.0, 0.0                 # поворачивается слабее команды / уводит сам
        self.history = [0.0]
        self.cmds = []
        if goal:
            self.b.request(goal, 0.0)

    def go(self, sec, telem=lambda r: tel(), events=lambda r: [], vision=lambda r: None):
        for _ in range(round(sec / DT)):
            self.t += DT
            rate = self.gain * self.wz + self.drift
            self.heading += rate * DT
            self.history.append(self.heading)
            if self.cmds:
                vx, vy, _ = self.cmds[-1]["v"]
                c, s = math.cos(math.radians(self.heading)), math.sin(math.radians(self.heading))
                self.x += (vx * c - vy * s) * DT
                self.y += (vx * s + vy * c + self.slip) * DT
            msg = dict(telem(self), gyr=[0.0, 0.0, rate])
            cmd = self.b.update(msg, events(self), vision(self), self.t)
            self.wz = cmd["v"][2]
            self.cmds.append(cmd)
        return self.cmds[-1]

    def until(self, state, limit=30.0, **world):
        while self.b.state != state and self.t < limit:
            self.go(DT, **world)
        return self.b.state


def test_starts_idle_and_still():
    cmd = Run().go(0.5)
    assert cmd["state"] == "idle" and cmd["v"] == (0, 0, 0) and cmd["pose"] == "stand"


# ---------- осмотреться ----------
def test_look_turns_a_full_circle_with_six_pauses_then_idles():
    r = Run("look")
    assert r.until("idle") == "idle" and r.t < 25
    assert r.heading == pytest.approx(360, abs=2) and r.b.state == "idle"
    turning = [c["v"][2] != 0 for c in r.cmds]
    pauses = sum(1 for a, b in zip(turning, turning[1:]) if a and not b)
    assert pauses == 6


def test_look_turns_by_the_gyro_even_when_the_body_lags():
    r = Run("look")
    r.gain = 0.6
    r.until("idle", limit=40.0)
    assert r.heading == pytest.approx(360, abs=2)


def test_look_switches_to_the_hand_when_it_comes_into_view():
    r = Run("look")
    r.go(1.0)
    cmd = r.go(0.1, vision=lambda r: {"hand": {"bearing_deg": 20.0, "dist_mm": 300}})
    assert cmd["state"] == "hand"


# ---------- подойти к руке ----------
def test_hand_far_off_to_the_side_turns_on_the_spot():
    cmd = Run("hand").go(0.1, vision=lambda r: {"hand": {"bearing_deg": -35.0, "dist_mm": 300}})
    assert cmd["v"][0] == 0 and cmd["v"][2] < 0


def test_hand_ahead_walks_and_steers_toward_it():
    cmd = Run("hand").go(0.1, vision=lambda r: {"hand": {"bearing_deg": 5.0, "dist_mm": 300}})
    assert cmd["v"][0] > 0 and cmd["v"][2] > 0


def test_hand_close_stops():
    cmd = Run("hand").go(0.1, vision=lambda r: {"hand": {"bearing_deg": 2.0, "dist_mm": 85}})
    assert cmd["v"] == (0, 0, 0) and cmd["state"] == "at_hand"


def test_hand_lost_goes_back_to_looking_instead_of_walking_blind():
    r = Run("hand")
    r.go(0.5, vision=lambda r: {"hand": {"bearing_deg": 0.0, "dist_mm": 300}})
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
    assert r.until("look") == "look"
    assert r.heading - h0 == pytest.approx(120, abs=3)


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
def beacon_at(target, lag=0.0):
    """Маяк виден обоими приёмниками в ±40° от курса, одним — до ±70°; lag — сколько секунд опаздывает ответ."""
    def f(r):
        h = r.history[max(0, len(r.history) - 1 - round(lag / DT))]
        b = (target - h + 180) % 360 - 180
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


@pytest.mark.parametrize("target", [-60, 0, 25, 170])
def test_home_centering_cancels_the_beacon_delay(target):
    r = Run("home")
    world = beacon_at(target, lag=0.1)                     # RP2350 считает пачки окнами по 100 мс
    assert r.until("home_approach", telem=world) == "home_approach"
    assert (target - r.heading + 180) % 360 - 180 == pytest.approx(0, abs=1.2)


def test_home_without_a_beacon_gives_up_after_a_full_circle():
    r = Run("home")
    r.go(14.0)
    assert r.b.state == "home_lost" and r.cmds[-1]["v"] == (0, 0, 0) and 330 < r.heading < 400


def test_home_approach_holds_the_heading_against_drift():
    r = Run("home")
    approach(r)
    h0 = r.heading
    r.drift = 4.0
    r.go(3.0, telem=lambda r: tel(beacon="ahead"))
    assert r.heading == pytest.approx(h0, abs=3) and r.cmds[-1]["v"][2] < 0


def tag(r):
    """Камера видит метку на башенке: где корпус в системе станции."""
    return {"dock": {"x_mm": r.x, "y_mm": r.y, "yaw_deg": r.heading}}


def test_home_by_the_tag_lines_up_on_the_station_axis_first():
    r = Run("home")
    r.x, r.y, r.heading = -320.0, 70.0, 25.0
    assert r.until("home_approach", vision=tag) == "home_approach"
    assert r.x == pytest.approx(-250, abs=10) and abs(r.y) < 2.5 and abs(r.heading) < 1.5


def test_home_approach_corrects_sideways_slip_by_the_tag():
    r = Run("home")
    r.x = -250.0
    r.until("home_approach", vision=tag)
    r.slip = 6.0
    r.go(3.0, telem=lambda r: tel(beacon="ahead"), vision=tag)
    assert abs(r.y) < 3 and r.cmds[-1]["v"][1] < 0


def test_home_by_the_beacon_switches_to_the_tag_once_it_is_in_view():
    r = Run("home")
    r.go(0.2, telem=beacon_at(30))
    assert r.b.state == "home_center"
    r.go(0.1, telem=beacon_at(30), vision=tag)
    assert r.b.state == "home_align"


def test_home_approach_far_off_the_axis_lines_up_again():
    r = Run("home")
    approach(r)
    r.x, r.y = -200.0, 40.0
    r.go(0.1, telem=lambda r: tel(beacon="ahead"), vision=tag)
    assert r.b.state == "home_align"


def test_home_tag_lost_while_lining_up_searches_again():
    r = Run("home")
    r.x, r.y = -320.0, 70.0
    r.go(0.5, vision=tag)
    assert r.b.state == "home_align"
    r.go(1.2)
    assert r.b.state == "home_search"


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


# ---------- точнее: паузы, ожидания, знаки ----------
def test_look_pauses_a_second_before_each_turn():
    r = Run("look")
    r.go(0.95)
    assert all(c["v"] == (0, 0, 0) for c in r.cmds)
    r.go(0.2)
    assert r.cmds[-1]["v"][2] > 0


def test_hand_briefly_out_of_view_is_waited_for():
    r = Run("hand")
    r.go(0.5, vision=lambda r: {"hand": {"bearing_deg": 0.0, "dist_mm": 300}})
    assert r.go(0.4)["state"] == "hand"


def test_hand_moved_away_is_followed_again_but_small_moves_are_ignored():
    r = Run("hand")
    r.go(0.1, vision=lambda r: {"hand": {"bearing_deg": 0.0, "dist_mm": 85}})
    assert r.go(0.1, vision=lambda r: {"hand": {"bearing_deg": 0.0, "dist_mm": 115}})["state"] == "at_hand"
    assert r.go(0.1, vision=lambda r: {"hand": {"bearing_deg": 0.0, "dist_mm": 130}})["state"] == "hand"


def test_hand_to_the_left_turns_left_on_the_spot():
    cmd = Run("hand").go(0.1, vision=lambda r: {"hand": {"bearing_deg": 12.0, "dist_mm": 300}})
    assert cmd["v"] == (0, 0, 30.0)


def test_lifted_waits_for_a_whole_second_on_the_table():
    r = Run("look")
    r.go(0.1, telem=lambda r: tel(far=(1,) * 6), events=lambda r: ["lifted"])
    r.go(0.5)
    r.go(0.1, telem=lambda r: tel(far=(0, 0, 0, 0, 0, 1)))       # поставили неровно — снова считать с нуля
    assert r.go(0.9)["state"] == "lifted"
    assert r.go(0.2)["state"] == "look"


def test_search_turns_on_the_spot():
    assert Run("home").go(0.3)["v"] == (0, 0, 30.0)


def test_tag_briefly_lost_while_lining_up_is_waited_for():
    r = Run("home")
    r.x, r.y = -320.0, 70.0
    r.go(0.2, vision=tag)
    assert r.go(0.8)["state"] == "home_align"


def test_lining_up_steps_forward_and_sideways_toward_the_axis():
    r = Run("home")
    r.x, r.y = -320.0, 70.0
    cmd = r.go(DT, vision=tag)
    cmd = r.go(DT, vision=tag)
    assert cmd["v"][0] == 40.0 and cmd["v"][1] == -30.0 and cmd["v"][2] == 0


def test_lining_up_when_turned_converts_the_error_into_body_axes():
    r = Run("home")
    r.x, r.y, r.heading = -250.0, 20.0, 90.0                     # стоит на 20 мм левее оси, смотрит налево
    r.go(DT, vision=tag)
    vx, vy, wz = r.go(DT, vision=tag)["v"]
    assert vx == pytest.approx(-30.0) and abs(vy) < 1e-9 and wz == -20.0   # ось — за спиной: назад и поворот направо


def test_charging_current_alone_means_docked():
    r = Run("home")
    lie_down(r)
    cmd = r.go(0.2, telem=lambda r: dict(tel(), bat=[7.4, -0.4]))
    assert cmd["state"] == "docked"


def test_search_counts_the_full_circle_from_where_it_started():
    r = Run("look")
    r.until("idle")                                          # курс уже 360°
    r.b.request("home", r.t)
    r.go(6.0)
    assert r.b.state == "home_search"


def test_home_approach_turns_back_onto_the_axis_by_the_tag():
    r = Run("home")
    r.x = -250.0
    r.until("home_approach", vision=tag)
    r.heading = 3.0
    assert r.go(DT, telem=lambda r: tel(beacon="ahead"), vision=tag)["v"][2] < 0
