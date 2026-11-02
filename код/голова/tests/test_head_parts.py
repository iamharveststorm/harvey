"""Драйвер GC9D01, настроение, касания, звук."""
import pytest

from conftest import project_file
from harvey_head import audio, gc9d01
from harvey_head.mood import ASLEEP_AFTER_S, SLEEPY_AFTER_S, Mood
from harvey_head.touch import TouchDetector

VENDOR = project_file("документы/GC9D01 — код запуска Waveshare 0.71.txt")


class FakeSpi:
    def __init__(self, dc):
        self.dc, self.log = dc, []

    def writebytes(self, data):
        self.log.append(("cmd" if not self.dc.level else "data", bytes(data)))

    def writebytes2(self, data):
        assert len(data) <= gc9d01.CHUNK
        self.log.append(("data" if self.dc.level else "cmd", bytes(data)))


class FakeDC:
    level = 0

    def on(self):
        self.level = 1

    def off(self):
        self.level = 0


def display():
    dc = FakeDC()
    spi = FakeSpi(dc)
    sleeps = []
    init = gc9d01.load_vendor_init(VENDOR.read_text(encoding="utf-8"))
    return gc9d01.GC9D01(spi, dc, init, madctl=0x48, sleep=sleeps.append), spi, init, sleeps


# ---------- GC9D01 ----------
def test_vendor_init_is_parsed_completely():
    init = gc9d01.load_vendor_init(VENDOR.read_text(encoding="utf-8"))
    assert len(init) == 50 and init[0] == (0xFE, b"", 0)
    assert (0x3A, b"\x05", 0) in init                                 # COLMOD: 16 бит на точку
    assert [c for c, _, _ in init][-3:] == [0x11, 0x29, 0x2C]
    assert dict((c, ms) for c, _, ms in init)[0x11] == 200            # пауза после Sleep Out


def test_init_sends_commands_with_dc_low_and_data_with_dc_high():
    disp, spi, init, sleeps = display()
    cmds = [b[0] for kind, b in spi.log if kind == "cmd"]
    assert cmds == [c for c, _, _ in init]
    assert ("data", b"\x48") in spi.log                               # поворот глаза — вместо значения из демо
    assert 0.2 in sleeps


def test_show_sets_full_window_and_streams_frame_in_chunks():
    disp, spi, _, _ = display()
    spi.log.clear()
    disp.show(bytes(160 * 160 * 2))
    assert spi.log[0] == ("cmd", b"\x2a") and spi.log[1] == ("data", bytes([0, 0, 0, 159]))
    assert spi.log[2] == ("cmd", b"\x2b") and spi.log[4] == ("cmd", b"\x2c")
    assert sum(len(b) for k, b in spi.log[5:]) == 51200 and len(spi.log) == 5 + 13
    with pytest.raises(ValueError):
        disp.show(b"\x00" * 10)


# ---------- настроение ----------
def test_mood_reacts_and_returns_to_neutral():
    m = Mood(0)
    m.event("pet", 1.0)
    assert m.expression(2.0) == "happy" and m.expression(4.1) == "neutral"


def test_fright_is_not_interrupted_by_smaller_things():
    m = Mood(0)
    m.event("lifted", 0)
    m.event("tap", 0.5)
    assert m.expression(0.6) == "surprised"
    m.event("fall", 0.7)
    assert m.expression(0.8) == "alarm"


def test_boredom_sleepy_then_asleep():
    m = Mood(0)
    assert m.expression(SLEEPY_AFTER_S - 1) == "neutral"
    assert m.expression(SLEEPY_AFTER_S + 1) == "sleepy"
    assert m.expression(ASLEEP_AFTER_S + 1) == "asleep"
    m.event("tap", ASLEEP_AFTER_S + 2)
    assert m.expression(ASLEEP_AFTER_S + 2.5) == "curious"


def test_docked_dozes_and_low_battery_tires():
    m = Mood(0)
    m.event("docked", 0)
    assert m.expression(10) == "sleepy" and m.expression(SLEEPY_AFTER_S + 1) == "asleep"
    m.undock()
    m.event("bat_low", 200)
    assert m.expression(210) == "sleepy"                              # скучал 200 с — всё равно сонный
    m.event("tap", 300)
    assert m.expression(302) == "tired"


def test_brain_emote():
    m = Mood(0)
    m.emote("love", 2.0, 5.0)
    assert m.expression(6.0) == "love" and m.expression(7.5) == "neutral"


# ---------- касания ----------
def press(det, pad, t0, t1):
    return det.update(pad, True, t0) + det.update(pad, False, t1)


def test_stroke_front_to_back_is_pet():
    det = TouchDetector()
    assert det.update(0, True, 0.0) == [] and det.update(1, True, 0.2) == []
    assert det.update(2, True, 0.4) == ["pet"]


def test_stroke_back_to_front_is_pet_but_slow_or_jumpy_is_not():
    assert TouchDetector().update(3, True, 0) + TouchDetector().update(2, True, 0) == []
    det = TouchDetector()
    det.update(3, True, 0.0), det.update(2, True, 0.3)
    assert det.update(1, True, 0.6) == ["pet"]
    slow = TouchDetector()
    slow.update(0, True, 0.0), slow.update(1, True, 0.8)
    assert slow.update(2, True, 2.1) == []
    jumpy = TouchDetector()
    jumpy.update(0, True, 0), jumpy.update(2, True, 0.2)
    assert jumpy.update(1, True, 0.4) == []


def test_short_touch_is_tap_long_is_hold():
    det = TouchDetector()
    assert press(det, 1, 0.0, 0.3) == ["tap"]
    det.update(2, True, 1.0)
    assert det.tick(2.0) == [] and det.tick(2.6) == ["hold"] and det.tick(3.0) == []
    assert det.update(2, False, 3.1) == []                            # после «подержать» — не «коснуться»


# ---------- звук ----------
def test_audio_commands_and_amp_gating():
    calls, amp = [], type("Amp", (), {"state": [], "on": lambda s: s.state.append(1), "off": lambda s: s.state.append(0)})()
    run = lambda cmd, check: (calls.append(cmd), type("R", (), {"returncode": 0})())[1]
    a = audio.Audio(amp, "hw:1", run=run)
    assert a.play("/tmp/x.wav") and amp.state == [1, 0]
    assert calls[0] == ["aplay", "-q", "-D", "hw:1", "/tmp/x.wav"]
    assert a.record("/tmp/y.wav", 2.4)
    assert calls[1][-3:] == ["-d", "2", "/tmp/y.wav"] and "S32_LE" in calls[1]
