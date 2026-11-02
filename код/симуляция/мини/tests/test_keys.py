"""Что делает каждая клавиша управления (без физики: только состояние MiniTeleop) и сетки предметов."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import harvey_mini_teleop as T  # noqa: E402
import mini_objects as MO  # noqa: E402


@pytest.fixture(scope="module")
def shared():
    return T.MiniTeleop()


@pytest.fixture
def tp(shared):
    shared.soft_reset()
    return shared


def test_walk_keys_add_up_and_release(tp):
    tp.key("w", hold=True)
    assert tp.cmd.tolist() == pytest.approx([0.06, 0, 0]) and tp.msg == "иду"
    tp.key("A", hold=True)
    assert tp.cmd.tolist() == pytest.approx([0.06, 0, 0.8])
    tp.release("W")
    assert tp.cmd.tolist() == pytest.approx([0, 0, 0.8])
    tp.release("A")
    assert tp.msg == "стоп" and not tp.cmd.any()


def test_fast_and_space(tp):
    tp.key("F")
    tp.key("S", hold=True)
    assert tp.cmd.tolist() == pytest.approx([-0.7 * 0.08, 0, 0]) and tp.fast
    tp.key(" ")
    assert not tp.held and not tp.cmd.any() and tp.msg == "стоп"


def test_walking_stands_up_and_cancels_macro(tp):
    tp.key("Z")
    assert tp.pose == "лежит" and tp.dz_t == 0.013
    tp.macro = iter(())
    tp.key("Q", hold=True)
    assert tp.pose == "стоит" and tp.dz_t == 0.0 and tp.macro is None


def test_crouch_and_lie_toggle(tp):
    tp.key("R")
    assert (tp.pose, tp.dz_t) == ("присел", 0.016)
    tp.key("R")
    assert (tp.pose, tp.dz_t) == ("стоит", 0.0)
    tp.key("Z"), tp.key("Z")
    assert tp.pose == "стоит"


def test_claw_select_cycles(tp):
    seen = []
    for _ in range(3):
        tp.key("B")
        seen.append(tp.claw_sel)
    assert seen == ["L", "R", "LR"] and tp.msg == "клешня: обе"


def test_claw_keys_are_held(tp):
    tp.key("I", hold=True), tp.key("N", hold=True)
    assert tp.claw_held == {"I", "N"}
    tp.release("I")
    assert tp.claw_held == {"N"}


def test_pitch_is_limited_to_12_degrees(tp):
    for _ in range(5):
        tp.key("[")
    assert tp.pitch_t == pytest.approx(math.radians(12)) and "вниз" in tp.msg
    for _ in range(7):
        tp.key("]")
    assert tp.pitch_t == pytest.approx(math.radians(-12)) and "вверх" in tp.msg


def test_grip_limit_steps_and_bounds(tp):
    tp.key(".")
    assert tp.sim.grip_lim == pytest.approx(0.07)
    for _ in range(30):
        tp.key(",")
    assert tp.sim.grip_lim == pytest.approx(0.01) and "0.01 Н·м" in tp.msg


@pytest.mark.parametrize("k, eyes, msg", [("7", {"L": -35.0, "R": -35.0}, "грустит"), ("8", {"L": 18.0, "R": -12.0}, "интересно"),
                                          ("9", {"L": 12.0, "R": 12.0}, "радуется")])
def test_eye_keys(tp, k, eyes, msg):
    tp.key(k)
    assert tp.eyes == eyes and tp.msg == msg


def test_guard_physics_and_reset(tp):
    tp.key("G")
    assert not tp.guard and tp.msg == "защита края выкл"
    tp.key("C")
    assert tp.show_phys
    tp.key("0")
    assert tp.guard and tp.msg == "заново"


@pytest.mark.parametrize("i, msg", [(1, "клешни поджаты"), (2, "клешни к столу"), (3, "машет"), (4, "подаёт")])
def test_presets(tp, i, msg):
    tp.key(str(i))
    assert tp.msg == msg and set(tp.arm_go) == {"L", "R"}
    if i == 2:
        assert tp.pose == "присел"


def test_macros_start(tp):
    tp.key("T")
    assert tp.macro is not None and tp.msg == "беру…"
    tp.key("H")
    assert tp.msg == "иду на станцию"


def test_unknown_key_changes_nothing(tp):
    before = (tp.msg, tp.pose, tp.claw_sel, tp.guard)
    tp.key("P"), tp.key("ESC")
    assert (tp.msg, tp.pose, tp.claw_sel, tp.guard) == before


# ---------- сетки предметов ----------
def vertices(xml):
    vals = xml.split('vertex="')[1].split('"')[0].split()
    return np.array([float(v) for v in vals]).reshape(-1, 3)


def test_hex_prism_and_tip_meshes():
    body = vertices(MO._hex_mesh("b", -0.08, 0.07, 0.0072))
    tip = vertices(MO._hex_tip_mesh("t", 0.07, 0.09, 0.0072, 0.0012))
    r = 0.0072 / 2 / math.cos(math.radians(30))
    assert body.shape == tip.shape == (12, 3)
    assert np.allclose(np.hypot(body[:, 1], body[:, 2]), r, atol=1e-5)
    assert np.allclose(np.hypot(tip[6:, 1], tip[6:, 2]), 0.0012, atol=1e-5) and np.allclose(tip[:6, 0], 0.07)
    assert MO._hex_mesh("b", -0.08, 0.07, 0.0072).startswith('<mesh name="b" vertex="-0.08000 0.00416 0.00000 ')
