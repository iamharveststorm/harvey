"""Управление с клавиатуры без окон: клавиши в любой раскладке и самопроверка run_test (≈ 45 с)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import harvey_mini_teleop as T  # noqa: E402


@pytest.mark.parametrize("code, name", [(87, "W"), (65, "A"), (49, "1"), (32, " "), (27, "ESC"), (188, ","), (190, "."),
                                        (219, "["), (221, "]"), (112, "")])
def test_windows_keycodes_do_not_depend_on_layout(monkeypatch, code, name):
    monkeypatch.setattr(T.sys, "platform", "win32")
    assert T.keyname(SimpleNamespace(keycode=code, keysym="ц")) == name   # «ц» — та же клавиша W в русской раскладке


@pytest.mark.parametrize("keysym, name", [("w", "W"), ("space", " "), ("Escape", "ESC"), ("comma", ","), ("period", "."),
                                          ("bracketleft", "["), ("bracketright", "]"), ("F1", "")])
def test_keysyms_elsewhere(monkeypatch, keysym, name):
    monkeypatch.setattr(T.sys, "platform", "linux")
    assert T.keyname(SimpleNamespace(keycode=0, keysym=keysym)) == name


@pytest.fixture(scope="module")
def selftest():
    return T.run_test()


def test_pen_is_picked_and_given(selftest):
    assert selftest["ручка_поднята_мм"] >= 50 and selftest["ручка_подана_мм"] > selftest["ручка_поднята_мм"]


def test_goes_home_and_charges(selftest):
    assert bool(selftest["заряжается"]) and selftest["заряд_растёт"]


def test_edge_guard_stops_before_the_table_edge(selftest):
    assert selftest["на_столе"] and selftest["стоп_у_края_y_мм"] < selftest["край_стола_y_мм"] - 50
