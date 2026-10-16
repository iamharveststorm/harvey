"""Видимые детали Харви (компоновка v2) для симуляции MuJoCo — настоящие сетки из CAD на каждом теле модели.
Физика остаётся на простых формах симуляции; сетки только рисуются (группа 2, без столкновений и массы).
    python export_mujoco.py   → код/симуляция/управление с клавиатуры/assets/robot/*.stl + robot_visual.json
Системы тел — как в harvey_sim.py: torso (оси бедра — z = 0), ноги {n}_coxa / _femur / _tibia, клешни {n}_ay / _up /
_fore / _hand, хвост T_base / T_up / T_fore / T_wr / T_cup, глаза {n}_eye. Правые клешня и глаз — зеркальные."""
import os, sys, json
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_robot as R
L, LC, CP, TP, EP, B, LP = R.L, R.LC, R.CP, R.TP, R.EP, R.B, R.LP
P = LP.P
OUT = os.path.join(HERE, "..", "..", "код", "симуляция", "управление с клавиатуры", "assets", "robot")
os.makedirs(OUT, exist_ok=True)

U = R.U
manifest = {}          # тело → [(файл, материал)]


def put(body, mat, m, tol=0.08):
    if m is None or m.is_empty():
        return
    m = m.simplify(tol) if hasattr(m, "simplify") else m
    name = f"{body}__{mat}.stl"
    tm = CP.to_trimesh(m.scale([0.001, 0.001, 0.001]))
    tm.export(os.path.join(OUT, name))
    manifest.setdefault(body, []).append([name, mat])


# ---------- корпус ----------
frame = [m for n, m in B.frame_parts() if not n.startswith("05_tray")]
put("torso", "grey", U(frame))
put("torso", "orange", B.tray())
E = B.electronics()
put("torso", "pcb", U([m for k, m in E.items() if ("Pi 5" in k or "Pico" in k or "BMS" in k or "DC-DC" in k)] + B.camera_assembly(0)[1]))
put("torso", "battery", U([m for k, m in E.items() if "21700" in k]))
put("torso", "red", U([m for k, m in E.items() if "аварийной" in k]))
cc, cm = R.coxa_servo_split()
c32, m32 = R.s32_split()
c15, m15 = R.s15_split()
H1, HT = CP.H1, CP.HT
fc, fm = [], []
for n, (x, y, yaw) in L.MOUNTS.items():
    tr = lambda m: m.translate([0, 0, P["coxa_drop"]]).rotate([0, 0, yaw]).translate([x, y, 0])
    fc.append(tr(cc)); fm.append(tr(cm))
for s in "LR":
    j1c = CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)); j1m = CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT))
    cols = [(0, 0, -1), (0, 1, 0), (1, 0, 0)]
    ec = CP.place(c32, cols, (-CP.HT, 0, 0)); em = CP.place(m32, cols, (-CP.HT, 0, 0))
    if s == "R":
        j1c, j1m, ec, em = (q.mirror([0, 1, 0]) for q in (j1c, j1m, ec, em))
    fc += [j1c.translate(list(L.ARM_S[s])), ec.translate(list(L.EYE_PIVOT[s]))]
    fm += [j1m.translate(list(L.ARM_S[s])), em.translate(list(L.EYE_PIVOT[s]))]
tj = lambda m: m.rotate([0, 0, 180]).translate(list(L.T_MOUNT))
fc.append(tj(CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)))); fm.append(tj(CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT))))
fc += B.camera_assembly(0)[0]
put("torso", "servo", U(fc))
put("torso", "metal", U(fm))

# ---------- ноги (одинаковые для всех шести) ----------
sc, sm = R.leg_servo_split()
CZ = -P["coxa_drop"]
up58 = lambda m: m.translate([0, 0, P["coxa_drop"]])
tib = lambda m: m.rotate([0, -90, 0])
put("leg_coxa", "orange", up58(LP.coxa_bracket()))
put("leg_coxa", "servo", up58(sc.translate([P["coxa"], 0, CZ])))
put("leg_coxa", "metal", up58(sm.translate([P["coxa"], 0, CZ])))
put("leg_femur", "orange", U([LC.plates(), LP.knee_sleeve().translate([P["femur"], 0, 0])]))
put("leg_femur", "servo", sc.translate([P["femur"], 0, 0]))
put("leg_femur", "metal", sm.translate([P["femur"], 0, 0]))
put("leg_tibia", "orange", tib(LP.tibia_fork()))
put("leg_tibia", "tpu", tib(LP.foot().translate([0, 0, -(P["tibia"] - P["foot_r"]) - P["foot_r"] + 1 - 4])))

# ---------- клешня (левая; правая — зеркало) ----------
A1, AF, xs, GS = CP.C["A1"], CP.C["AF"], CP.C["xs"], CP.G_S
piv, contact = xs + CP.C["piv"], -8.5
lt, ub = contact - CP.P32["pad"] - 0.5, contact + CP.P32["pad"] + 0.5
pd = CP.pads()
low = CP.HP.rot_y(pd.translate([piv + 2, 0, lt - 0.5]), CP.C["bend"], piv, contact)
upd = CP.HP.rot_y(pd.mirror([0, 0, 1]).translate([piv + 2, 0, ub + 0.5]), CP.C["bend"], piv, contact)
claw = {
    "ay": {"grey": CP.yaw_bracket(), "servo": CP.place(c15, CP.J2_COLS, (0, 0, 0)), "metal": CP.place(m15, CP.J2_COLS, (0, 0, 0))},
    "up": {"orange": U([CP.arm_plate(1), CP.arm_plate(-1), CP.elbow_sleeve()]),
           "servo": CP.place(c15, CP.J3_COLS, (A1, 0, 0)), "metal": CP.place(m15, CP.J3_COLS, (A1, 0, 0))},
    "fore": {"orange": CP.forearm(), "servo": CP.place(c32, CP.J4_COLS, (AF - HT, 0, 0)), "metal": CP.place(m32, CP.J4_COLS, (AF - HT, 0, 0))},
    "hand": {"orange": U([CP.hand(), CP.HP.rot_y(CP.jaw(), -12, xs, 0)]), "servo": CP.place(c32, CP.J5_COLS, (xs, GS, 0)),
             "metal": CP.place(m32, CP.J5_COLS, (xs, GS, 0)), "tpu": U([low, CP.HP.rot_y(upd, -12, xs, 0)])},
}
for link, mats in claw.items():
    for mat, m in mats.items():
        put(f"L_{link}", mat, m)
        put(f"R_{link}", mat, m.mirror([0, 1, 0]))

# ---------- хвост ----------
TA1, TAF = TP.TC["A1"], TP.TC["AF"]
tail = {
    "T_base": {"grey": TP.yaw_bracket(), "servo": CP.place(c15, TP.j2_cols(), (0, 0, 0)), "metal": CP.place(m15, TP.j2_cols(), (0, 0, 0))},
    "T_up": {"orange": U([TP.arm_plate(1), TP.arm_plate(-1), TP.elbow_sleeve()]),
             "servo": CP.place(c15, CP.J3_COLS, (TA1, 0, 0)), "metal": CP.place(m15, CP.J3_COLS, (TA1, 0, 0))},
    "T_fore": {"orange": TP.forearm(), "servo": CP.place(c32, TP.W_COLS, (TAF, TP.YF, 0)), "metal": CP.place(m32, TP.W_COLS, (TAF, TP.YF, 0))},
    "T_wr": {"orange": TP.cup_holder().translate([-TAF, 0, 0])},
    "T_cup": {"cup": TP.cup().translate([-TAF - 22.0, 0, 0])},
}
for body, mats in tail.items():
    for mat, m in mats.items():
        put(body, mat, m)

# ---------- глаз ----------
eye = {"grey": EP.horn_adapter(), "orange": U([EP.stalk(), EP.housing()]), "tpu": EP.bumper()}
for mat, m in eye.items():
    put("L_eye", mat, m)
    put("R_eye", mat, m.mirror([0, 1, 0]))
c = EP.eye_center(); x1 = EP.housing_x()[1]
screen = {"x": (x1 - 1.6 - EP.E["lens_t"] + 0.2) / 1000, "z": float(c[2]) / 1000, "r": 0.0162}

json.dump({"bodies": manifest, "eye_screen": screen}, open(os.path.join(OUT, "robot_visual.json"), "w", encoding="utf-8"), indent=1)
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print(f"{OUT}: {len(os.listdir(OUT))} файлов, {size / 1e6:.1f} МБ")
