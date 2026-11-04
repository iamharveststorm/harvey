"""Калибровка нулей приводов: две позы (подставка и «сдвинуть рукой») → ноль и направление каждого привода.
Сквозная проверка — через настоящий Spine прошивки RP2350, у имитации шины спрятаны настоящие нули и направления."""
import math
import random
import sys

import pytest

from harvey_head import calibrate as cal
from harvey_head import servos
from harvey_head.protocol import LineReader, encode

from conftest import project_file

sys.path.insert(0, str(project_file("код/прошивка/rp2350/tests")))
from fakes import FakeBus  # noqa: E402
from spine import Spine  # noqa: E402

K = 4096 / (2 * math.pi)


class Rig:
    """Харви на USB: Spine + шины, у каждого привода свой ноль и направление (как собран)."""

    def __init__(self, seed=1, dead=()):
        rnd = random.Random(seed)
        self.zero = {sid: rnd.randint(1400, 2700) for sid in servos.JOINT_OF}
        self.sign = {sid: rnd.choice((1, -1)) for sid in servos.JOINT_OF}
        self.dead = set(dead)
        self.buses = {"A": FakeBus(), "B": FakeBus(), "C": FakeBus()}
        self.out, self.reader, self.t = b"", LineReader(), 0
        rig = self

        class Port:
            def read(self):
                data, rig.out = rig.out, b""
                return data

            def write(self, data):
                rig.inbox += rig.reader.feed(data)
        self.inbox = []
        self.spine = Spine(Port(), self.buses, cfg={"telemetry_ms": 50}, clock=lambda: self.t)

    def set_angles(self, angles_deg):
        for joint, a in angles_deg.items():
            sid = servos.SERVO_IDS[joint]
            if sid in self.dead:
                continue
            bus = "A" if sid < 40 else "B" if sid < 70 else "C"
            self.buses[bus].positions[sid] = (self.zero[sid] + self.sign[sid] * round(math.radians(a) * K)) % 4096

    # как SpineLink головы
    def send(self, msg):
        self.out += encode(msg)
        return True

    def poll(self, now=0.0):
        out, self.inbox = self.inbox, []
        return out

    def wait(self, sec):
        for _ in range(round(sec / 0.005)):
            self.t += 5
            self.spine.step()


def pose_a():
    return cal.pose_a(cal.load_pose())


def scripted(rig, moves=None):
    """«Человек»: первое Enter — Харви в позе A, дальше по группам сдвигает суставы, как сказано."""
    a = pose_a()
    steps = iter([None] + [g for g in cal.GROUPS])
    rig.set_angles(a)

    def ask(prompt):
        step = next(steps)
        if step is not None:
            _, joints, _ = step
            rig.set_angles({j: a[j] + (moves or {}).get(j, cal.DIRECTION[j[-1]] * 20.0) for j in joints})
        return ""
    return ask


def test_two_poses_find_every_zero_and_direction(tmp_path):
    rig = Rig()
    said = []
    c = cal.run(rig, ask=scripted(rig), say=said.append, wait=rig.wait, path=tmp_path / "servo_calib.json")
    for joint, sid in servos.SERVO_IDS.items():
        assert c.sign[joint] == rig.sign[sid], joint
        assert c.zero[joint] == rig.zero[sid], joint
    assert (tmp_path / "servo_calib.json").exists()
    loaded = servos.Calibration.load(tmp_path / "servo_calib.json")
    assert loaded.zero == c.zero and loaded.sign == c.sign


def test_calibrated_positions_put_each_joint_where_asked(tmp_path):
    rig = Rig(seed=7)
    c = cal.run(rig, ask=scripted(rig), say=lambda s: None, wait=rig.wait, path=tmp_path / "c.json")
    for joint, sid in servos.SERVO_IDS.items():
        for a in (-0.4, 0.0, 0.3):
            want = (rig.zero[sid] + rig.sign[sid] * round(a * K)) % 4096
            assert abs(c.pos(joint, a) - want) <= 1, joint


def test_a_joint_not_moved_is_reported_and_not_saved(tmp_path):
    rig = Rig()
    said = []
    c = cal.run(rig, ask=scripted(rig, moves={"LF_k": 1.0}), say=said.append, wait=rig.wait, path=tmp_path / "c.json")
    assert "LF_k" not in c.zero and any("LF_k" in s and "не сдвинулся" in s for s in said)


def test_a_silent_servo_is_reported(tmp_path):
    rig = Rig(dead={servos.SERVO_IDS["RB_f"]})
    said = []
    c = cal.run(rig, ask=scripted(rig), say=said.append, wait=rig.wait, path=tmp_path / "c.json")
    assert "RB_f" not in c.zero and any("RB_f" in s and "не ответил" in s for s in said)


def test_without_a_spine_nothing_is_saved(tmp_path):
    class Dead:
        def send(self, msg):
            return False

        def poll(self, now=0.0):
            return []
    said = []
    assert cal.run(Dead(), ask=lambda p: "", say=said.append, wait=lambda s: None, path=tmp_path / "c.json") is None
    assert not (tmp_path / "c.json").exists() and any("RP2350 не отвечает" in s for s in said)


# ---------- ноль и направление ----------
def test_identity_calibration_is_the_plain_mapping():
    c = servos.Calibration()
    assert c.pos("LF_f", 0.5) == servos.to_pos(0.5) and c.rad("LF_f", servos.to_pos(0.5)) == pytest.approx(0.5, abs=0.002)


def test_reversed_servo_counts_the_other_way():
    c = servos.Calibration({"LF_f": 2000}, {"LF_f": -1})
    assert c.pos("LF_f", math.radians(10)) == 2000 - round(math.radians(10) * K)
    assert c.rad("LF_f", c.pos("LF_f", 0.3)) == pytest.approx(0.3, abs=0.002)


def test_range_across_the_4095_edge_is_flagged():
    c = servos.Calibration({"LF_k": 300}, {"LF_k": 1})                 # колено −130…−60° → ниже нуля
    assert "LF_k" in c.out_of_range()
    assert servos.Calibration({"LF_k": 3000}, {"LF_k": 1}).out_of_range() == []


def test_message_uses_the_calibration():
    c = servos.Calibration({"LF_c": 1000}, {"LF_c": -1})
    msg = servos.message({"LF_c": 0.0, "LF_f": 0.0}, (0, 0, 0), c)
    assert msg["q"]["11"] == 1000 and msg["q"]["12"] == 2048
