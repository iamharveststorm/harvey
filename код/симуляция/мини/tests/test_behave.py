"""Поведение головы в симуляции по датчикам Харви — нормы (≈ 2 мин). Все 10 стартов домой — `python mini_behave.py`."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import mini_behave as mb  # noqa: E402


@pytest.mark.parametrize("start", [mb.HOME_STARTS[i] for i in (1, 4)])
def test_home_in_the_light_with_the_tag_charges(start):
    r = mb.scenario_home(mb.start_at(*start))
    assert r["state"] == "docked" and r["charging"] and r["t"] <= 60 and not r["fell"]


@pytest.mark.parametrize("start", [mb.HOME_STARTS[i] for i in (0, 5, 8)])          # 5, 8 — под 45° и 35°: раньше не доходили
def test_home_in_the_dark_by_the_two_led_beacon_charges(start):
    r = mb.scenario_home(mb.start_at(*start), camera=False)
    assert r["state"] == "docked" and r["charging"] and r["t"] <= 100 and not r["fell"]        # 45° — со второй попытки, ~90 с


def test_station_behind_is_reported_lost_and_robot_stays_on_the_table():
    r = mb.scenario_behind_station()
    assert r["state"] == "home_lost" and r["t"] <= 25 and r["on_table"] and not r["fell"]


def test_look_turns_a_full_circle_on_the_spot():
    r = mb.scenario_look()
    assert r["yaw"] == pytest.approx(360, abs=30) and r["t"] <= 25 and r["drift_mm"] < 30


def test_walks_up_to_the_hand_and_stops_close():
    r = mb.scenario_hand((0.0662 + 0.30 * math.cos(math.radians(30)), 0.30 * math.sin(math.radians(30))))
    assert r["state"] == "at_hand" and 70 <= r["hand_mm"] <= 110 and r["t"] <= 15


def test_hand_behind_is_found_by_looking_around():
    r = mb.scenario_hand((-0.25, 0.05), goal="look")
    assert r["state"] == "at_hand" and "hand" in r["states"]


@pytest.mark.parametrize("side", ["front", "left"])
def test_hand_beyond_the_table_edge_never_makes_it_fall(side):
    r = mb.scenario_hand_beyond_edge(side)
    assert r["edge_seen"] and r["on_table"] and not r["fell"] and r["max_tilt"] < 5


def test_lifted_robot_relaxes_quickly_and_looks_around_once_put_down():
    r = mb.scenario_lift()
    assert r["relaxed_after_s"] <= 0.3 and "lifted" in r["states"] and r["states"][-1] == "look" and r["on_table"]
