"""Симуляция «Компакт мини»: кинематика ног и клешней против MuJoCo, правила движения и сценарии с нормами.

    (окружение C:/venvs/harvey) python -m pytest tests      # ≈ 15 с
Нормы — из заметок/Компакт мини.md и того, что симуляция уже показывала (mini_results.json): ходьба 5–8 см/с,
поворот по знаку команды, поднятая ручка — в пальцах, на станции — заряд.
"""
import math
import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import harvey_mini as hm  # noqa: E402

LEGS = list(hm.MOUNTS)


@pytest.fixture(scope="module")
def mini():
    return hm.Mini()


# ---------- модель ----------
def test_28_servos_all_in_the_model(mini):
    names = hm.joint_names()
    assert len(names) == len(set(names)) == 28
    assert all(mini.m.joint(n) is not None for n in names)
    assert mini.m.nu == 28


def test_mass_from_cad_matches_model(mini):
    assert float(sum(mini.m.body_mass)) == pytest.approx(hm.MS["total"], rel=0.02)


def test_legs_are_mirror_symmetric():
    for a, b in (("LF", "RF"), ("LM", "RM"), ("LB", "RB")):
        pa, pb = hm.neutral(a), hm.neutral(b)
        assert pa[0] == pytest.approx(pb[0], abs=1e-6) and pa[1] == pytest.approx(-pb[1], abs=1e-6)


# ---------- кинематика ног: IK против MuJoCo ----------
def foot_world(m, d, n):
    return d.geom(f"{n}_foot").xpos.copy()


@pytest.mark.parametrize("leg", LEGS)
def test_leg_ik_moves_foot_where_asked(leg):
    s = hm.Mini()
    d = s.d
    h0 = -(hm.ZJ - hm.FOOT_R)
    p0 = hm.neutral(leg)
    for k, v in zip("cfk", hm.leg_ik(leg, p0, h0)):
        d.qpos[s.j[f"{leg}_{k}"][0]] = v
    mujoco.mj_kinematics(s.m, d)
    base = foot_world(s.m, d, leg)
    for dx, dy, dh in ((0.010, 0, 0), (0, 0.008, 0), (0, 0, 0.012), (-0.008, -0.005, 0.006)):
        for k, v in zip("cfk", hm.leg_ik(leg, p0 + [dx, dy], h0 + dh)):
            d.qpos[s.j[f"{leg}_{k}"][0]] = v
        mujoco.mj_kinematics(s.m, d)
        R = d.body("torso").xmat.reshape(3, 3)
        moved = R.T @ (foot_world(s.m, d, leg) - base)               # в системе корпуса
        assert moved == pytest.approx([dx, dy, dh], abs=0.0005)


# ---------- клешни ----------
@pytest.mark.parametrize("p", [(0.10, 0.035, 0.03), (0.09, 0.05, 0.06), (0.12, 0.03, 0.0)])
def test_arm_ik_fk_roundtrip(p):
    q = hm.arm_ik("L", p)
    assert hm.arm_fk("L", q) == pytest.approx(p, abs=1e-6)
    pr = (p[0], -p[1], p[2])
    assert hm.arm_fk("R", hm.arm_ik("R", pr)) == pytest.approx(pr, abs=1e-6)


def test_claw_rules():
    tuck = tuple(math.radians(a) for a in hm.TUCK_Q)
    assert hm.claw_ok("L", tuck) and hm.claw_ok("R", tuck)
    assert not hm.claw_ok("L", (math.radians(75), 0.5, -1.0))                      # поворот плеча за 70°
    assert not hm.claw_ok("L", (math.radians(-5), math.radians(65), math.radians(-60)))   # правило 4: высоко — не внутрь
    low_out = (math.radians(20), math.radians(-15), math.radians(-30))
    assert not hm.claw_ok("L", low_out)                                              # правило 1: низко — не наружу


def test_rule_2_eye_moves_out_when_claw_is_high():
    s = hm.Mini()
    s.q["L_p"] = math.radians(70)
    s.step(False)
    assert s.q["L_s"] <= math.radians(-45) and s.q["R_s"] == 0.0


# ---------- походка ----------
def test_gait_tripods_alternate_and_lift():
    s = hm.Mini()
    fn = s.gait(0.06, t_half=0.30, lift=0.015)
    h0 = -(hm.ZJ - hm.FOOT_R)
    heights = {n: [] for n in LEGS}
    for k in range(60):
        fn(k * 0.01)
        for n in LEGS:
            q = tuple(s.q[f"{n}_{j}"] for j in "cfk")
            heights[n].append(hm.FEM * math.sin(q[1]) + (hm.TIB - hm.FOOT_R) * math.sin(q[1] + q[2]) - h0)
    up = {n: np.array(v) > 0.002 for n, v in heights.items()}
    a, b = hm.TRIPOD_A, [n for n in LEGS if n not in hm.TRIPOD_A]
    assert not any((up[x] & up[y]).any() for x in a for y in b)                    # треноги не в воздухе вместе
    assert max(max(v) for v in heights.values()) == pytest.approx(0.015, abs=0.0015)


def test_walker_walks_at_commanded_speed():
    s = hm.Mini()
    w = hm.Walker(s)
    s.run(0.5, record=False)
    x0, y0 = s.d.body("torso").xpos[:2]
    for _ in range(int(6.0 / hm.DT)):
        w.step(np.array([0.06, 0.0, 0.0]))
        s.step(False)
    x1, y1 = s.d.body("torso").xpos[:2]
    assert 5.0 <= (x1 - x0) / 6.0 * 100 <= 8.0
    assert abs(y1 - y0) < 0.015


def test_walker_stands_still_without_command():
    s = hm.Mini()
    w = hm.Walker(s)
    stand = s.stand_q()
    w.step(np.zeros(3))
    assert all(s.q[k] == pytest.approx(v, abs=1e-9) for k, v in stand.items())


def test_table_has_edges():
    s = hm.Mini(world_xml=hm.table_xml(-0.3, 0.3, -0.3, 0.3))
    gid = np.zeros(1, np.int32)
    grp = np.array([1, 0, 0, 0, 0, 0], np.uint8)
    on = mujoco.mj_ray(s.m, s.d, np.array([0.2, 0.0, 0.1]), np.array([0.0, 0.0, -1.0]), grp, 1, -1, gid)
    off = mujoco.mj_ray(s.m, s.d, np.array([0.4, 0.0, 0.1]), np.array([0.0, 0.0, -1.0]), grp, 1, -1, gid)
    assert on == pytest.approx(0.1, abs=1e-6) and off == pytest.approx(0.1 + hm.FLOOR_DROP, abs=1e-6)


def test_contact_force_on_the_floor_carries_the_weight():
    s = hm.Mini()
    s.run(1.0, record=False)
    floor = s.m.geom("floor").id
    total = sum(hm.contact_force(s.m, s.d, floor, s.m.geom(f"{n}_foot").id) for n in LEGS)
    assert total == pytest.approx(float(sum(s.m.body_mass)) * 9.81, rel=0.1)


# ---------- сценарии с нормами ----------
def test_stand_scenario():
    r = hm.test_stand()
    assert r["наклон"] < 2 and 15 <= r["просвет_под_корпусом_мм"] <= 30 and r["бедро"]["пик_%предела"] < 50


def test_walk_scenario():
    r = hm.test_walk()
    assert 5.0 <= r["скорость_см_с"] <= 8.0 and abs(r["увод_мм"]) < 15 and r["на_ногах"] and r["наклон_макс"] < 5
    assert r["бедро"]["пик_%предела"] < 100 and r["колено"]["пик_%предела"] < 100


@pytest.mark.parametrize("wz", [0.8, -0.8])
def test_turn_goes_the_commanded_way(wz):
    r = hm.test_turn(wz)
    assert r["на_ногах"]
    assert math.copysign(1, r["градусов_в_с"]) == math.copysign(1, wz)
    assert abs(r["градусов_в_с"]) == pytest.approx(math.degrees(abs(wz)), rel=0.15)


def test_pen_scenario():
    r = hm.test_pen()
    assert r["в_пальцах"] and r["поднята_на_мм"] >= 50 and r["нарушений_правил"] == 0 and r["на_ногах"]


def test_wipe_scenario():
    r = hm.test_wipe()
    assert r["следует_за_рукой"] and r["нарушений_правил"] == 0 and r["наклон"] < 5


def test_tip_scenario():
    assert hm.test_tip()["наклон"] < 5


def test_edge_margins_are_positive():
    r = hm.test_edge()
    assert r["запас_стопы_мм"] > 0 and r["запас_клешни_мм"] > 0


def test_dock_scenario():
    r = hm.test_dock()
    assert r["заряжается"] and max(abs(v) for v in r["промах_мм"]) <= 10 and r["наклон"] < 5


# ---------- отчёт о нагрузке и наклон ----------
def test_load_report_in_percent_of_rated_and_stall():
    s = hm.Mini()
    s.reset_load()
    s.tq["LF_f"] = [hm.RATED] * 99 + [hm.STALL]                       # 99 % времени номинал, 1 % — упор
    s.tq["RF_f"] = [hm.RATED / 2] * 100
    r = s.load(["LF_f", "RF_f"])
    mean = (99 * hm.RATED + hm.STALL + 100 * hm.RATED / 2) / 200
    assert r["средняя_%ном"] == round(mean / hm.RATED * 100)
    assert r["пик_%ном"] == 100 and r["пик_%предела"] == round(hm.RATED / hm.STALL * 100)


def test_load_ignores_joints_without_samples():
    s = hm.Mini()
    s.reset_load()
    s.tq["LF_k"] = [hm.RATED]
    assert s.load(["LF_k", "RF_k"])["средняя_%ном"] == 100


@pytest.mark.parametrize("deg", [0, 10, 35])
def test_tilt_reads_body_roll(deg):
    s = hm.Mini()
    a = math.radians(deg)
    s.d.qpos[s.m.jnt_qposadr[s.m.body("torso").jntadr[0]] + 3:][:4] = [math.cos(a / 2), math.sin(a / 2), 0, 0]
    mujoco.mj_kinematics(s.m, s.d)
    assert s.tilt() == pytest.approx(deg, abs=1e-6)
