"""Тело на голове: поведение + походка → цели суставов на RP2350 50 раз в секунду; камера → метка станции."""
import math

import numpy as np
import pytest

from harvey_head.behavior import Behavior
from harvey_head.body import Body
from harvey_head.camera import DockCamera
from harvey_head.gait import Gait
from harvey_head.head import Head

from test_dock_tag import render


class Spine:
    def __init__(self):
        self.queue, self.sent = [], []

    def poll(self, now):
        out, self.queue = self.queue, []
        return out

    def send(self, msg):
        self.sent.append(msg)
        return True

    def of(self, t):
        return [m for m in self.sent if m["t"] == t]


def tel(gyr_z=0.0, far=(0,) * 6):
    return {"t": "tel", "far": list(far), "beacon": "none", "axis": "none", "edge": [70, 70, 72, 72, 104, 104],
            "tilt": [0.0, 0.0], "gyr": [0.0, 0.0, gyr_z], "bat": [7.4, 1.0]}


def run(body, sec, hz=100, tel_msg=None, t0=0.0):
    for k in range(round(sec * hz)):
        now = t0 + k / hz
        if tel_msg is not None:
            body.on_spine(tel_msg, now)
        body.tick(now)
    return t0 + sec


def make(vision=None):
    spine = Spine()
    return spine, Body(spine, Behavior(0.0), Gait(), vision=vision, now=0.0)


def test_joint_targets_go_to_the_spine_fifty_times_a_second():
    spine, body = make()
    run(body, 1.0, tel_msg=tel())
    js = spine.of("j")
    assert 48 <= len(js) <= 51 and all(len(m["q"]) == 28 for m in js)


def test_table_calibration_once_after_standing_up():
    spine, body = make()
    run(body, 1.4, tel_msg=tel())
    assert not spine.of("cal")
    run(body, 2.0, tel_msg=tel(), t0=1.4)
    assert len(spine.of("cal")) == 1


def test_no_targets_before_the_spine_has_spoken():
    spine, body = make()
    run(body, 0.5)
    assert not spine.of("j")


def test_a_goal_turns_into_walking_commands():
    spine, body = make()
    body.request("look", 0.0)
    run(body, 3.0, tel_msg=tel(gyr_z=0.0))
    assert any(m["v"][2] > 0 for m in spine.of("j"))                    # осмотр — поворот налево


def test_spine_events_reach_the_behaviour_once():
    spine, body = make()
    body.request("look", 0.0)
    body.on_spine({"t": "ev", "ev": "lifted"}, 0.0)
    run(body, 0.1, tel_msg=tel(far=(1,) * 6))
    assert body.behavior.state == "lifted" and body.events == []


def test_vision_is_asked_on_each_tick():
    calls = []
    spine, body = make(vision=lambda now: calls.append(now) or {})
    run(body, 0.2, tel_msg=tel())
    assert len(calls) >= 9


def test_head_passes_the_goal_from_the_pc_and_ticks_the_body():
    spine = Spine()
    body = Body(spine, Behavior(0.0), Gait(), now=0.0)
    head = Head(spine, body=body, now=0.0)
    head.on_brain({"t": "goal", "goal": "home"}, 0.0)
    spine.queue.append(tel())
    head.tick(0.1)
    assert body.behavior.goal == "home" and spine.of("j")


def test_head_draws_the_eyes_no_faster_than_its_fps():
    class Eye:
        def __init__(self):
            self.n = 0

        def show(self, frame):
            self.n += 1
    eye = Eye()
    head = Head(Spine(), eyes={"left": eye}, now=0.0, fps=25)
    for k in range(100):
        head.tick(k / 100)
    assert 24 <= eye.n <= 26


# ---------- камера ----------
def test_dock_camera_finds_the_tag_a_few_times_a_second():
    frame, K = render(-250, 10, 5)
    grabs = []
    cam = DockCamera(lambda: grabs.append(1) or frame, K, every_s=0.2)
    out = [cam.vision(k / 50) for k in range(50)]
    assert len(grabs) == 5
    assert out[-1]["dock"]["dist_mm"] == pytest.approx(math.hypot(140 + 250, 10), rel=0.02)


def test_dock_camera_without_a_tag_sees_nothing():
    cam = DockCamera(lambda: np.full((720, 1280), 128, np.uint8), np.eye(3), every_s=0.2)
    assert cam.vision(0.0) == {"dock": None}
