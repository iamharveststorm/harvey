"""Обе клешни на подставках в рабочих позах — части по материалам для рендера в Blender.
    python export_render_parts.py      → render_parts/*.stl
    blender --background --python render_claws.py   → «рендер клешней.png»"""
import os
import harvey_claw_parts as cp
from manifold3d import Manifold

out = os.path.join(cp.HERE, "render_parts")
os.makedirs(out, exist_ok=True)
parts = cp.link_parts()


# корпуса и «металл» приводов раздельно
def s15_case(): return cp.boxr(cp.TX0, cp.TX1, -cp.W / 2, cp.W / 2, -cp.H / 2, cp.H / 2)
def s15_metal(): return cp.s15_body() - s15_case()
def s32_case(): return cp.boxr(cp.X0, cp.X1, -cp.P32["body_T"] / 2, cp.P32["body_T"] / 2, -cp.P32["body_D"], 0)
def s32_metal(): return cp.s32_body() - s32_case()


A1, AF, xs, H1, HT, GS = cp.C["A1"], cp.C["AF"], cp.C["xs"], cp.H1, cp.HT, cp.G_S
SERVOS = {  # звено: [(корпус, металл), …] в системе звена
    "base": [(cp.place(s32_case(), cp.J1_COLS, (0, 0, -H1 - HT)), cp.place(s32_metal(), cp.J1_COLS, (0, 0, -H1 - HT)))],
    "yaw": [(cp.place(s15_case(), cp.J2_COLS, (0, 0, 0)), cp.place(s15_metal(), cp.J2_COLS, (0, 0, 0)))],
    "up": [(cp.place(s15_case(), cp.J3_COLS, (A1, 0, 0)), cp.place(s15_metal(), cp.J3_COLS, (A1, 0, 0)))],
    "fore": [(cp.place(s32_case(), cp.J4_COLS, (AF - HT, 0, 0)), cp.place(s32_metal(), cp.J4_COLS, (AF - HT, 0, 0)))],
    "hand": [(cp.place(s32_case(), cp.J5_COLS, (xs, GS, 0)), cp.place(s32_metal(), cp.J5_COLS, (xs, GS, 0)))],
}
PRINTED_GREY = {"base", "yaw"}


def pad_pair():
    piv, contact = xs + cp.C["piv"], -8.5
    lt, ub = contact - cp.P32["pad"] - 0.5, contact + cp.P32["pad"] + 0.5
    p = cp.pads()
    low = cp.HP.rot_y(p.translate([piv + 2, 0, lt - 0.5]), cp.C["bend"], piv, contact)
    up = cp.HP.rot_y(p.mirror([0, 0, 1]).translate([piv + 2, 0, ub + 0.5]), cp.C["bend"], piv, contact)
    return low, up


def scene(q, ty, mirror):
    groups = {"petg_orange": [], "petg_grey": [], "case": [], "metal": [], "tpu": []}
    model = {k: (list(v[0]), []) for k, v in parts.items()}
    for link, lst in SERVOS.items():
        model[link] = (model[link][0], [])
    low, up = pad_pair()
    posed_pr = cp.posed({k: (v[0], []) for k, v in model.items()}, q)
    posed_sv = cp.posed({k: ([c for c, _ in SERVOS.get(k, [])], []) for k in parts}, q)
    posed_mt = cp.posed({k: ([m for _, m in SERVOS.get(k, [])], []) for k in parts}, q)
    posed_pad = cp.posed({"hand": ([low], []), "jaw": ([up], []), "base": ([], []), "yaw": ([], []), "up": ([], []), "fore": ([], [])}, q)
    for link, lst in posed_pr.items():
        groups["petg_grey" if link in PRINTED_GREY else "petg_orange"] += lst
    for lst in posed_sv.values(): groups["case"] += lst
    for lst in posed_mt.values(): groups["metal"] += lst
    for lst in posed_pad.values(): groups["tpu"] += lst
    groups["petg_grey"].append(cp.test_stand())
    out_g = {}
    for k, lst in groups.items():
        m = Manifold()
        for x in lst:
            m += x
        if mirror:
            m = m.mirror([0, 1, 0])
        out_g[k] = m.translate([0, ty, 0])
    return out_g


R = scene((-25, 35.7, -95.4, 0, 30), -70, False)      # правая — тянется к столу, пальцы раскрыты
L = scene((-20, 75, 70, 40, 10), 70, True)            # левая (зеркальная) — поднята «над спиной», кисть повёрнута
for k in R:
    cp.to_trimesh(R[k] + L[k]).export(os.path.join(out, k + ".stl"))
print("ok, пол на z =", -H1 - HT - 70.0)
