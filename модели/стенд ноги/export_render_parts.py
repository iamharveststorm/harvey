"""Две ноги на стойках (рабочая стойка и шаг с поднятой ногой) — части по материалам для рендера в Blender.
    python export_render_parts.py     → render_parts/*.stl
    blender --background --python render_legs.py   → «рендер ног.png»"""
import os, math, sys
sys.argv = sys.argv[:1]
import leg_check as C
import harvey_leg_parts as LP
from manifold3d import Manifold

P = LP.P
HERE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(HERE, "render_parts")
os.makedirs(out, exist_ok=True)
L, W, H, SF, FT = P["servo_L"], P["servo_W"], P["servo_H"], P["shaft_from_end"], P["flange_t"]
CZ = -P["coxa_drop"]
ZJ = C.TIB_FOOT - P["femur"] * math.sin(math.radians(20))
TABLE = CZ - ZJ                                   # стол — под стопой в рабочей стойке


def s15_case_y():   # STS3215 вал по y (бедро, колено) — корпус и металл раздельно
    return LP.box(L, H, W, -(L / 2 - SF), 0, 0)


def s15_metal_y():
    m = Manifold()
    for s in (1, -1):
        m += LP.cyl(FT, P["flange_D"] / 2, 0, s * (H / 2 + FT / 2), 0, "y")
    cx, cy = P["case_screw"]
    for sz in (1, -1):
        for sy in (1, -1):
            m += LP.cyl(1.6, 1.9, cx, sy * (H / 2 + FT - 1.3 + 0.8), sz * cy, "y")
    return m


def coxa_case():
    return LP.box(L, W, H, -(L / 2 - SF), 0, -FT - H / 2)


def coxa_metal():
    return LP.cyl(FT, P["flange_D"] / 2, 0, 0, -FT / 2)


def tower():
    """Стойка-подставка (условно): держит привод основания, как в панцире."""
    zt = -2.0
    m = LP.box(42, 44, zt - TABLE, -24, 0, (zt + TABLE) / 2)
    m -= LP.box(L + 0.6, W + 0.6, H + 2, -(L / 2 - SF), 0, -FT - H / 2 + 1)
    m += LP.box(70, 70, 4, -24, 0, TABLE + 2)
    return m


def leg(qc, qf, qk):
    lk = {
        "base": ([coxa_case()], [coxa_metal()], []),
        "coxa": ([s15_case_y().translate([P["coxa"], 0, CZ])], [s15_metal_y().translate([P["coxa"], 0, CZ])], [LP.coxa_bracket()]),
        "femur": ([s15_case_y().translate([P["femur"], 0, 0])], [s15_metal_y().translate([P["femur"], 0, 0])],
                  [C.plates(), LP.knee_sleeve().translate([P["femur"], 0, 0])]),
        "tibia": ([], [], [LP.tibia_fork()]),
    }
    foot = LP.foot().translate([0, 0, -(P["tibia"] - P["foot_r"]) - P["foot_r"] + 1 - 4])
    groups = {"case": Manifold(), "metal": Manifold(), "petg_orange": Manifold(), "petg_grey": Manifold(), "tpu": Manifold(), "stand": Manifold()}
    for kind, idx in (("case", 0), ("metal", 1), ("printed", 2)):
        P_ = C.posed({k: (v[idx], []) for k, v in lk.items()}, qc, qf, qk)
        for link, ms in P_.items():
            for m in ms:
                key = kind if kind != "printed" else ("petg_grey" if link == "coxa" else "petg_orange")
                groups[key] += m
    groups["tpu"] += C.posed({"base": ([], []), "coxa": ([], []), "femur": ([], []), "tibia": ([foot], [])}, qc, qf, qk)["tibia"][0]
    groups["petg_grey"] += LP.leg_tower()
    return groups


stand = leg(0, 20, -110)
qf, qk = C.ik(P["coxa"] + P["femur"] * math.cos(math.radians(20)) - P["coxa"], -(ZJ - P["foot_r"]) + 25)
lift = leg(-25, qf, qk)
for k in stand:
    m = stand[k].translate([0, -60, 0]) + lift[k].translate([0, 60, 0])
    import trimesh, numpy as np
    mesh = m.to_mesh()
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False).export(os.path.join(out, k + ".stl"))
print(f"ok; стол на z = {TABLE:.1f} мм; шаг: бедро {qf:.1f}°, колено {qk:.1f}°")
