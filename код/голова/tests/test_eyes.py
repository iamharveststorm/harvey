"""Глаза: картинка по выражению, RGB565 для GC9D01, моргание и плавные переходы."""
import numpy as np
import pytest
from PIL import Image

from harvey_head.eyes import EXPRESSIONS, LID, SCLERA, Animator, Look, blend, render, to_rgb565


def white(img):
    a = np.asarray(img, dtype=int)
    return int((np.abs(a - SCLERA).sum(axis=2) < 10).sum())


def pupil_x(img):
    a = np.asarray(img, dtype=int)
    ys, xs = np.nonzero(a.sum(axis=2) < 60)
    return xs.mean() - 80


@pytest.mark.parametrize("name", list(EXPRESSIONS))
def test_every_expression_renders_160_square(name):
    img = render(EXPRESSIONS[name], "left")
    assert img.size == (160, 160) and img.mode == "RGB"
    assert img.getpixel((0, 159)) == LID                            # угол круглого дисплея — цвет корпуса


def test_closed_eye_shows_no_white():
    assert white(render(Look(openness=1.0))) > 12000
    assert white(render(Look(openness=0.0))) == 0
    assert white(render(Look(openness=0.5))) < white(render(Look(openness=1.0))) * 0.6


@pytest.mark.parametrize("x", [0.8, -0.8])
def test_both_eyes_look_the_same_way(x):
    left, right = pupil_x(render(Look(x=x), "left")), pupil_x(render(Look(x=x), "right"))
    assert left == pytest.approx(right, abs=1.0) and abs(left) > 15
    assert (left < 0) == (x > 0)                                     # + — к правому боку Харви: для зрителя влево


def test_right_eye_lids_mirror_left():
    sad_l, sad_r = np.asarray(render(EXPRESSIONS["sad"], "left")), np.asarray(render(EXPRESSIONS["sad"], "right"))
    assert (np.abs(sad_l[:, :, :].astype(int) - sad_r[:, ::-1, :]) > 30).mean() < 0.02   # всё, кроме блика, зеркально


def test_sad_outer_corner_is_lower():
    a = np.asarray(render(EXPRESSIONS["sad"], "left"), dtype=int)
    first_white = lambda col: int(np.argmax(np.abs(a[:, col] - SCLERA).sum(axis=1) < 10))
    assert first_white(140) > first_white(20)                        # левый глаз: внешний угол — справа на картинке


def test_happy_lower_lid_hides_bottom():
    assert white(render(EXPRESSIONS["happy"])) < white(render(EXPRESSIONS["neutral"])) * 0.85


def test_rgb565_packing_matches_gc9d01_16_bit():
    img = Image.new("RGB", (2, 1))
    img.putpixel((0, 0), (255, 0, 0))
    img.putpixel((1, 0), (0, 255, 255))
    assert to_rgb565(img) == bytes([0xF8, 0x00, 0x07, 0xFF])         # R5 G6 B5, старший байт первым
    assert len(to_rgb565(render(Look()))) == 160 * 160 * 2


def test_blend_endpoints_and_middle():
    a, b = EXPRESSIONS["neutral"], EXPRESSIONS["sleepy"]
    assert blend(a, b, 0) == a and blend(a, b, 1) == b and blend(a, b, 5) == b
    assert blend(a, b, 0.5).openness == pytest.approx((a.openness + b.openness) / 2)


def test_animator_moves_smoothly_and_blinks():
    an = Animator(seed=1)
    an.next_blink, an.next_glance = 10.0, 99.0
    an.set("sleepy", 0.0)
    assert an.frame(0.0).openness == pytest.approx(1.0)
    assert 0.35 < an.frame(0.125).openness < 1.0                     # половина перехода (0,25 с)
    assert an.frame(1.0).openness == pytest.approx(0.35)
    an.set("neutral", 2.0)
    an.frame(3.0)
    assert an.frame(10.0).openness == pytest.approx(1.0)              # моргание начинается с первого кадра после срока
    assert an.frame(10.08).openness < 0.1                            # середина моргания (0,16 с)
    assert an.frame(10.2).openness == pytest.approx(1.0)
    assert 12.0 <= an.next_blink <= 16.2


def test_asleep_does_not_blink():
    an = Animator(seed=1)
    an.set("asleep", 0.0)
    an.next_blink = 0.5
    an.frame(1.0)
    assert an.blink_at is None


def test_look_at_is_clamped():
    an = Animator(seed=2)
    an.next_glance = 99.0
    an.look_at(5, -5)
    f = an.frame(1.0)
    assert (f.x, f.y) == (1.0, -1.0)
