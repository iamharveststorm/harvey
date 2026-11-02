"""Точные проверки: эталонные картинки глаз, границы порогов, переподключение, команды дисплея.
Эталоны глаз — tests/golden/*.png; после намеренной правки рисунка:  python -m tests.test_exact  (пересоздаёт их)."""
import asyncio
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from conftest import project_file
from harvey_head import audio, gc9d01
from harvey_head.eyes import EXPRESSIONS, Animator, Look, render
from harvey_head.head import Head
from harvey_head.links import BrainLink, SpineLink
from harvey_head.mood import ASLEEP_AFTER_S, REACTIONS, SLEEPY_AFTER_S, Mood
from harvey_head.touch import HOLD_S, STROKE_WINDOW_S, TAP_MAX_S, TouchDetector

GOLDEN = Path(__file__).absolute().parent / "golden"
CASES = {f"{name}_{side}": (EXPRESSIONS[name], side) for name in EXPRESSIONS for side in ("left", "right")}
CASES.update({"look_x_right": (Look(x=0.7, y=0.4), "right"), "look_x_left": (Look(x=-0.6, y=-0.5), "left"),
              "half_tilt_left": (Look(openness=0.5, lid_tilt=0.3, lower=0.2), "left")})


def golden_path(name):
    return GOLDEN / f"{name}.png"


@pytest.mark.parametrize("name", sorted(CASES))
def test_eye_matches_golden(name):
    look, side = CASES[name]
    ref = golden_path(name)
    if not ref.exists():                                              # эталон ищем и через раскрытый путь (mutator)
        ref = project_file(f"код/голова/tests/golden/{name}.png")
    got = np.asarray(render(look, side))
    exp = np.asarray(Image.open(ref).convert("RGB"))
    assert (got != exp).any(axis=2).sum() == 0, f"{name}: картинка изменилась"


# ---------- аниматор ----------
def test_glance_moves_gaze_in_small_steps_and_reschedules():
    an = Animator(seed=7)
    an.next_blink = 99
    t0 = an.next_glance
    an.frame(t0 - 0.01)
    assert an.gaze == (0.0, 0.0)
    an.frame(t0)
    gx, gy = an.gaze
    assert gx != 0 and -0.3 <= gx <= 0.3 and -0.2 <= gy <= 0.2
    assert t0 + 1 <= an.next_glance <= t0 + 4
    assert an.frame(t0 + 0.5).x == pytest.approx(gx, abs=1e-9)        # взгляд прибавляется к выражению


def test_blink_ends_exactly_after_its_duration():
    an = Animator(seed=1)
    an.next_glance = 99
    an.next_blink = 1.0
    an.frame(1.0)
    assert an.frame(1.0 + Animator.BLINK_S + 1e-9).openness == 1.0 and an.blink_at is None    # 1,16 − 1,0 = 0,1599… в float


def test_transition_starts_from_current_look():
    an = Animator(seed=1)
    an.next_blink = an.next_glance = 99
    an.set("sleepy", 0.0)
    assert an.frame(0.0 + Animator.MOVE_S / 2).openness == pytest.approx((1 + 0.35) / 2)


# ---------- настроение: границы времени ----------
def test_reaction_ends_exactly_on_time():
    m = Mood(0)
    m.event("pet", 0)
    assert m.expression(REACTIONS["pet"].seconds - 1e-6) == "happy" and m.expression(REACTIONS["pet"].seconds) == "neutral"


def test_equal_priority_replaces_and_expired_is_replaced_by_anything():
    m = Mood(0)
    m.event("tip", 0)                                                  # приоритет 6
    m.event("shock", 0.5)                                              # тоже 6 — заменяет
    assert m.expression(0.6) == "surprised"
    m.event("docked", REACTIONS["shock"].seconds + 0.5)                # прежняя кончилась ровно сейчас — заменяет и слабым
    assert m.expression(REACTIONS["shock"].seconds + 0.6) == "sleepy"


def test_sleepy_and_asleep_exactly_at_limits():
    m = Mood(0)
    assert m.expression(SLEEPY_AFTER_S) == "sleepy" and m.expression(ASLEEP_AFTER_S) == "asleep"
    d = Mood(0)
    d.docked = True
    assert d.expression(SLEEPY_AFTER_S) == "asleep"


# ---------- касания: границы ----------
def test_stroke_window_is_inclusive():
    det = TouchDetector()
    det.update(0, True, 0.0), det.update(1, True, STROKE_WINDOW_S / 2)
    assert det.update(2, True, STROKE_WINDOW_S) == ["pet"]


def test_tap_and_hold_limits_are_inclusive():
    det = TouchDetector()
    det.update(0, True, 0.0)
    assert det.update(0, False, TAP_MAX_S) == ["tap"]
    det.update(1, True, 1.0)
    assert det.tick(1.0 + HOLD_S) == ["hold"]


def test_repeated_press_and_release_are_ignored():
    det = TouchDetector()
    det.update(0, True, 0.0)
    assert det.update(0, True, 0.3) == [] and det.down_at[0] == 0.0
    assert det.update(3, False, 0.3) == []


def test_two_fingers_are_not_a_tap():
    det = TouchDetector()
    det.update(0, True, 0.0), det.update(3, True, 0.1)
    assert det.update(0, False, 0.2) == []


# ---------- голова ----------
class NoSpine:
    def __init__(self):
        self.sent = []

    def poll(self, now):
        return []

    def send(self, msg):
        self.sent.append(msg)


def test_telemetry_period_boundary_and_bad_battery_field():
    out = []
    h = Head(NoSpine(), {}, type("B", (), {"offer": lambda s, m: out.append(m)})(), now=0.0, seed=1, telemetry_hz=5)
    h.on_spine({"t": "tel"}, 0.2)                                      # ровно через 0,2 с — уже пора
    h.mood.docked = True
    h.on_spine({"t": "tel", "bat": [7.9]}, 0.3)                        # нет тока — со станции не сходим
    assert len(out) == 1 and h.mood.docked
    h.on_spine({"t": "tel", "bat": [7.9, 0.0]}, 0.35)
    assert h.mood.docked                                               # ток 0 — ещё на станции


def test_look_defaults_and_link_log():
    h = Head(NoSpine(), {}, None, seed=1)
    h.anim.look_at(0.5, 0.5)
    h.on_brain({"t": "look"}, 0)
    assert h.anim.gaze == (0.0, 0.0)
    h.on_brain({"t": "link", "brain": "up"}, 0)
    h.on_brain({"t": "nonsense"}, 0)
    assert h.log == ["brain: {'t': 'link', 'brain': 'up'}"]


# ---------- связь ----------
class Port:
    in_waiting = 0

    def read(self, n):
        return b""

    def write(self, b):
        pass


def test_spine_backoff_grows_then_resets_after_success():
    state = {"ok": False, "n": 0}

    def opener():
        state["n"] += 1
        if not state["ok"]:
            raise OSError
        return Port()

    link = SpineLink(opener)
    link.poll(0.0), link.poll(1.0), link.poll(2.9)
    assert state["n"] == 2                                             # 0 с, 1 с; следующая — не раньше 3 с
    link.poll(3.0)
    assert state["n"] == 3
    state["ok"] = True
    link.poll(7.0)
    assert link.port is not None and link.attempt == 0 and link.send({"t": "x"}) is True


def test_brain_connected_flag():
    async def scenario():
        flags = []

        async def serve(reader, writer):
            await asyncio.sleep(0.2)
            writer.close()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        link = BrainLink("127.0.0.1", server.sockets[0].getsockname()[1])
        stop = asyncio.Event()
        task = asyncio.ensure_future(link.run(stop))
        await asyncio.wait_for(link.inbox.get(), 2)
        flags.append(link.connected)
        await asyncio.wait_for(link.inbox.get(), 2)
        flags.append(link.connected)
        stop.set()
        task.cancel()
        server.close()
        return flags

    assert asyncio.run(scenario()) == [True, False]


# ---------- дисплей ----------
def test_madctl_replaced_only_for_36h_and_sleep_out_waits():
    class Dc:
        level = 0

        def on(self):
            self.level = 1

        def off(self):
            self.level = 0

    log, sleeps, dc = [], [], Dc()
    spi = type("S", (), {"writebytes": lambda s, d: log.append((dc.level, bytes(d))),
                         "writebytes2": lambda s, d: log.append((dc.level, bytes(d)))})()
    gc9d01.GC9D01(spi, dc, [(0x3A, b"\x05", 0), (0x36, b"\x00", 0), (0x11, b"", 0)], madctl=0x48, sleep=sleeps.append)
    assert log == [(0, b"\x3a"), (1, b"\x05"), (0, b"\x36"), (1, b"\x48"), (0, b"\x11")] and sleeps == [0.005]
    log.clear()
    d = gc9d01.GC9D01(spi, dc, [], size=160, sleep=sleeps.append)
    d.window(2, 3, 150, 159)
    assert log == [(0, b"\x2a"), (1, bytes([0, 2, 0, 150])), (0, b"\x2b"), (1, bytes([0, 3, 0, 159]))]


def test_audio_reports_failure():
    fail = lambda cmd, check: type("R", (), {"returncode": 1})()
    a = audio.Audio(None, run=fail)
    assert a.play("x.wav") is False and a.record("y.wav", 1) is False
    assert audio.record_cmd("y.wav", 3, "hw:0")[:8] == ["arecord", "-q", "-D", "hw:0", "-c", "2", "-r", "16000"]


if __name__ == "__main__":
    GOLDEN.mkdir(exist_ok=True)
    for name, (look, side) in CASES.items():
        render(look, side).save(golden_path(name))
    print(f"эталоны пересозданы: {len(CASES)} в {GOLDEN}")
