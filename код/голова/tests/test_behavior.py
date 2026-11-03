"""Поведение: телеметрия и события «спинного мозга», «зрение» → команда корпусу. Без железа и без симуляции."""
import math

import pytest

from harvey_head.behavior import Behavior

DT = 0.05                                    # телеметрия 20 раз в секунду


def tel(far=(0,) * 6, beacon="none", edge=(70, 70, 72, 72, 104, 104), tilt=(0.0, 0.0), axis="none"):
    return {"t": "tel", "far": list(far), "beacon": beacon, "edge": list(edge), "tilt": list(tilt), "bat": [7.4, 1.0],
            "axis": axis}


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
            return tel(beacon="ahead", axis="on")
        if abs(b) <= 70:
            return tel(beacon="left" if b > 0 else "right")
        return tel(beacon="none")
    return f


@pytest.mark.parametrize("target", [-150, -60, -20, 0, 25, 65, 170])
def test_home_turns_to_face_the_beacon(target):
    r = Run("home")
    world = beacon_at(target)
    assert r.until("home_axis", telem=world) == "home_axis"
    assert (target - r.heading + 180) % 360 - 180 == pytest.approx(0, abs=4)


@pytest.mark.parametrize("target", [-60, 0, 25, 170])
def test_home_centering_cancels_the_beacon_delay(target):
    r = Run("home")
    world = beacon_at(target, lag=0.1)                     # RP2350 считает пачки окнами по 100 мс
    assert r.until("home_axis", telem=world) == "home_axis"
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
    r.go(3.0, telem=lambda r: tel(beacon="ahead", axis="on"))
    assert r.heading == pytest.approx(h0, abs=3) and r.cmds[-1]["v"][2] < 0














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
    return tel(beacon="ahead", axis="on", edge=(d, d, 72, 72, 104, 104))


def approach(r):
    """Сразу на заход: Харви уже на оси и смотрит на станцию."""
    r.b.on_axis = True
    r.b._faced(r.t)
    r.go(DT, telem=beacon_at(0))
    assert r.b.state == "home_approach"
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
    end = r.t + 30
    while r.cmds[-1]["pose"] != "lie" and r.t < end:
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
    r.go(4.6)
    assert r.b.state == "home_retry"                       # отходит 5 с — на 20 см, чтобы снова увидеть площадку
    r.go(0.4)
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




# ---------- домой: метка (направление и расстояние) и маяк с двумя светодиодами ----------
LED_X, TAG_X, WEDGE_D, FIN_L, RX_X, CONE = 144.0, 140.0, 3.5, 46.5, 71.0, 50.0   # мм и ° — как станция в CAD


def wrap(a):
    return (a + 180) % 360 - 180


def station(r):
    """Телеметрия у станции: боковые приёмники — куда маяк, центральный — по какую сторону оси (клин за перегородкой),
    передние датчики края — площадка, стол, башенка."""
    b = wrap(math.degrees(math.atan2(-r.y, LED_X - r.x)) - r.heading)
    beacon = "ahead" if abs(b) <= 40 else ("left" if b > 0 else "right") if abs(b) <= 70 else "none"
    h = math.radians(r.heading)
    xr, yr = r.x + RX_X * math.cos(h), r.y + RX_X * math.sin(h)
    w = WEDGE_D * ((LED_X - xr) / FIN_L - 1)
    in_beams = abs(math.degrees(math.atan2(yr, LED_X - xr))) <= CONE and abs(b) <= 60
    axis = ("on" if abs(yr) < w else "left" if yr > 0 else "right") if in_beams else "none"
    land = r.x + 132
    d = 59 if -32 <= land <= 32 else (70 - (land - 140)) if land > 140 else 70
    return tel(beacon=beacon, axis=axis, edge=(d, d, 72, 72, 104, 104))


def tag(r):
    dx, dy = TAG_X - r.x, -r.y
    b = wrap(math.degrees(math.atan2(dy, dx)) - r.heading)
    return {"dock": {"bearing_deg": b, "dist_mm": math.hypot(dx, dy)}} if abs(b) < 50 and math.hypot(dx, dy) < 600 else {}


def charged(r):
    return ["docked"] if r.b.state == "home_lie" and abs(r.y) < 3.5 and abs(r.x) < 17.5 else []


STARTS = [(-300, 60, 30), (-250, -50, -60), (-200, 0, 120), (-320, 90, 0), (-180, -20, -170)]


@pytest.mark.parametrize("start", STARTS)
def test_home_in_the_dark_by_the_two_led_beacon(start):
    r = Run("home")
    r.x, r.y, r.heading = start
    r.until("docked", limit=120.0, telem=station, events=charged)
    assert r.b.state == "docked" and abs(r.y) < 3.5


@pytest.mark.parametrize("start", STARTS)
def test_home_in_the_light_with_the_tag(start):
    r = Run("home")
    r.x, r.y, r.heading = start
    r.until("docked", limit=120.0, telem=station, events=charged, vision=tag)
    assert r.b.state == "docked" and abs(r.y) < 3.5


def test_home_in_the_dark_holds_the_axis_against_drift():
    r = Run("home")
    r.x, r.y, r.heading = -300.0, 30.0, 10.0
    r.drift, r.slip = 1.5, 1.5                             # снос втрое больше, чем в симуляции (4 мм за 8 с)
    r.until("docked", limit=120.0, telem=station, events=charged)
    assert r.b.state == "docked" and abs(r.y) < 3.5


def test_tag_in_view_faces_the_station_first():
    r = Run("home")
    r.x, r.y, r.heading = -250.0, 0.0, 20.0
    r.go(0.1, telem=station, vision=tag)
    assert r.b.state == "home_face" and r.cmds[-1]["v"][2] < 0


def test_left_of_the_axis_steps_right_and_keeps_facing_the_station():
    r = Run("home")
    r.b._faced(r.t)
    cmd = r.go(DT, telem=lambda r: tel(beacon="ahead", axis="left"), vision=lambda r: {"dock": {"bearing_deg": 0.0, "dist_mm": 300}})
    assert cmd["v"][0] == 0 and cmd["v"][1] < 0 and cmd["v"][2] > 0


def test_approach_losing_the_beams_goes_back_to_finding_the_axis():
    r = Run("home")
    r.b._go("home_approach", r.t, ref=None, step="pad", lost=None)
    r.go(1.2, telem=lambda r: tel(beacon="ahead", axis="none"))
    assert r.b.state == "home_axis"


def test_flicker_at_the_pad_edge_is_not_taken_for_the_tower():
    def flicker(r):
        t = r.t - r.t_approach
        d = 70 if t < 1.0 else 58 if t < 2.5 else (70 if int(t * 20) % 2 else 59) if t < 3.0 else 70
        return tel(beacon="ahead", axis="on", edge=(d, d, 72, 72, 104, 104))
    r = Run("home")
    approach(r)
    r.go(4.0, telem=flicker)
    assert r.b.state == "home_approach"


def test_wedge_edges_are_measured_where_the_receiver_is():
    r = Run("home")
    r.b._go("home_axis", r.t, lat=0.0, vy=0.0, edges=[], inside=None)
    r.b.heading = 3.0
    r.b.data["h_ref"] = 0.0
    assert r.b._receiver_lat() == pytest.approx(71.0 * math.sin(math.radians(3.0)), abs=0.01)
