"""Походка головы: размеры ног из CAD, обратная задача ног, трипод по команде скорости, лечь, клешни поджаты; приводы."""
import json
import math

import pytest

from harvey_head import gait as g
from harvey_head import protocol, servos

from conftest import project_file

GEO = g.load()
L2 = GEO.tib - GEO.foot_r
H0 = -(GEO.tib - GEO.fem * math.sin(math.radians(GEO.stance_deg)) - GEO.foot_r)   # стопа под осью бедра в стойке, мм


def fk(n, q):
    """Где стопа (мм, система корпуса; z — от плоскости осей бедра) при суставах q = (поворот, бедро, колено)."""
    x, y, yaw = GEO.mounts[n]
    qc, qf, qk = q
    r = GEO.cox + GEO.fem * math.cos(qf) + L2 * math.cos(qf + qk)
    a = math.radians(yaw) + qc
    return x + r * math.cos(a), y + r * math.sin(a), GEO.fem * math.sin(qf) + L2 * math.sin(qf + qk)


def legs(angles, n):
    return tuple(angles[f"{n}_{j}"] for j in "cfk")


def test_geometry_is_the_same_cad_export_the_simulation_uses():
    sim = json.loads(project_file("код/симуляция/мини/assets/mini_visual.json").read_text(encoding="utf-8"))["G"]
    assert (GEO.cox, GEO.fem, GEO.tib, GEO.foot_r) == (sim["cox"], sim["fem"], sim["tib"], sim["foot_r"])
    assert {k: tuple(v) for k, v in sim["mounts"].items()} == GEO.mounts


@pytest.mark.parametrize("leg", ["LF", "LM", "LB", "RF", "RM", "RB"])
def test_leg_ik_puts_the_foot_where_asked(leg):
    nx, ny = g.neutral(GEO, leg)
    for dx, dy, dh in ((0, 0, 0), (10, 0, 0), (0, -8, 0), (0, 0, 12), (-8, 5, 6)):
        q = g.leg_ik(GEO, leg, (nx + dx, ny + dy), H0 + dh)
        assert fk(leg, q) == pytest.approx((nx + dx, ny + dy, H0 + dh), abs=0.01)


def test_standing_still_puts_every_foot_at_stance():
    angles = g.Gait(GEO).step({"v": (0, 0, 0), "pose": "stand"}, 0.02)
    for n in GEO.mounts:
        x, y, h = fk(n, legs(angles, n))
        mx, my, _ = GEO.mounts[n]
        assert h == pytest.approx(H0, abs=0.01)
        assert math.hypot(x - mx, y - my) == pytest.approx(GEO.cox + GEO.fem * math.cos(math.radians(GEO.stance_deg)), abs=0.01)


def walk(cmd, sec, dt=0.02, gait=None):
    gait = gait or g.Gait(GEO)
    return gait, [gait.step(cmd, dt) for _ in range(round(sec / dt))]


def test_tripods_take_turns_and_lift_the_foot_15_mm():
    _, frames = walk({"v": (60, 0, 0)}, 1.5)
    up = {n: [fk(n, legs(a, n))[2] - H0 > 2.0 for a in frames] for n in GEO.mounts}
    a, b = g.TRIPOD_A, [n for n in GEO.mounts if n not in g.TRIPOD_A]
    assert not any(up[x][i] and up[y][i] for x in a for y in b for i in range(len(frames)))
    assert max(fk(n, legs(f, n))[2] - H0 for f in frames for n in GEO.mounts) == pytest.approx(15.0, abs=1.5)


def test_speed_ramps_up_with_limited_acceleration():
    gait = g.Gait(GEO)
    gait.step({"v": (60, 0, 30)}, 0.02)
    vx, vy, wz = gait.velocity()
    assert vx == pytest.approx(16.0) and vy == 0 and wz == pytest.approx(math.degrees(0.8 * 0.02))


def test_lie_lowers_the_body_13_mm_at_20_mm_per_second():
    gait, frames = walk({"v": (0, 0, 0), "pose": "lie"}, 0.3)
    assert fk("LM", legs(frames[-1], "LM"))[2] == pytest.approx(H0 + 6.0, abs=0.01)
    _, frames = walk({"v": (0, 0, 0), "pose": "lie"}, 1.0, gait=gait)
    assert fk("LM", legs(frames[-1], "LM"))[2] == pytest.approx(H0 + GEO.rest_drop, abs=0.01)


def test_claws_tucked_grips_and_eyes_straight():
    angles = g.Gait(GEO).step({"v": (0, 0, 0)}, 0.02)
    for s in "LR":
        assert [angles[f"{s}_{j}"] for j in "ype"] == pytest.approx([math.radians(a) for a in GEO.tuck_deg])
        assert angles[f"{s}_g"] == 0.0 and angles[f"{s}_s"] == 0.0
    assert len(angles) == 28


def test_a_turn_command_turns_the_feet_the_commanded_way():
    _, frames = walk({"v": (0, 0, 40)}, 0.4)
    # опорные стопы тройки, стоящей на столе, идут по часовой — корпус поворачивает против, налево
    gait = g.Gait(GEO)
    gait.vel = [0.0, 0.0, math.radians(40)]
    gait.phase = 0.0
    p0 = g.foot_targets(GEO, gait.phase, gait.vel, gait.t_half, gait.lift)["LM"]
    gait.phase = 0.2
    p1 = g.foot_targets(GEO, gait.phase, gait.vel, gait.t_half, gait.lift)["LM"]
    a0, a1 = math.atan2(p0[1], p0[0]), math.atan2(p1[1], p1[0])
    assert a1 < a0 and len(frames) == 20


# ---------- приводы ----------
def test_servo_ids_follow_the_wiring_table():
    assert servos.SERVO_IDS["LF_c"] == 11 and servos.SERVO_IDS["RB_k"] == 63 and servos.SERVO_IDS["R_g"] == 84
    assert servos.SERVO_IDS["L_s"] == 91 and len(set(servos.SERVO_IDS.values())) == 28


def test_servo_position_roundtrip():
    for a in (-1.2, -0.3, 0.0, 0.5, 1.4):
        assert servos.to_rad(servos.to_pos(a)) == pytest.approx(a, abs=2 * math.pi / 4096)


def test_joint_message_for_the_spine():
    gait = g.Gait(GEO)
    msg = servos.message(gait.step({"v": (40, 0, 0)}, 0.02), gait.velocity())
    assert msg["t"] == "j" and len(msg["q"]) == 28 and msg["v"] == [16.0, 0.0, 0.0]              # разгон 0,8 м/с² за 20 мс
    assert protocol.decode(protocol.encode(msg).strip()) == msg
