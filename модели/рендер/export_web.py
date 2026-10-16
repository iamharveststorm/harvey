"""Сетки звеньев Харви (компоновка v2) для визуализаций three.js — визуализация/lib/harvey_meshes.js.
Каждое звено — в своей системе сустава, как группы в «3D-модели» и «Интерактивном двойнике»:
three.js: X — влево, Y — вверх, Z — вперёд (у ноги: X — вдоль ноги, Y — вверх). Координаты — Int16, base64.
    python export_web.py"""
import os, sys, json, math, base64
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import export_robot as R
L, LC, CP, TP, EP, B, LP = R.L, R.LC, R.CP, R.TP, R.EP, R.B, R.LP
P = LP.P
ZB = 52.6                        # высота осей бедра над столом в двойнике (LEG.ZJ)
OUT = os.path.join(HERE, "..", "..", "визуализация", "lib", "harvey_meshes.js")


def U(ms):
    m = Manifold()
    for x in ms:
        if x is not None and not x.is_empty():
            m += x
    return m


def body_map(v):        # CAD корпуса (x вперёд, y влево, z вверх) → three (X влево, Y вверх, Z вперёд)
    return np.stack([v[:, 1], v[:, 2], v[:, 0]], 1)


def leg_map(v):         # CAD ноги (x вдоль ноги, y влево от ноги, z вверх) → three ноги (X вдоль, Y вверх, Z = −y)
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)


def pack(m, mapper, tol=0.12):
    m = m.simplify(tol) if hasattr(m, "simplify") else m
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    p = mapper(v)[t].reshape(-1, 3)                       # без индексов: плоские нормали, «CAD-вид»
    s = float(np.abs(p).max()) / 32000.0 or 1.0
    q = np.round(p / s).astype(np.int16)
    return {"s": s, "n": int(len(t)), "v": base64.b64encode(q.tobytes()).decode("ascii")}


def split_servo(case, full):
    return case, full - case


meshes = {}
total = [0]


def add(name, mat, m, mapper):
    if m.is_empty():
        return
    d = pack(m, mapper); d["m"] = mat
    meshes.setdefault(name, []).append(d); total[0] += d["n"]


# ---------------- нога ----------------
sc, sm = R.leg_servo_split(); cc, cm = R.coxa_servo_split()
CZ = -P["coxa_drop"]
up58 = lambda m: m.translate([0, 0, P["coxa_drop"]])            # ось бедра — на уровне корня ноги
add("leg_coxa", "printed", up58(LP.coxa_bracket()), leg_map)
add("leg_coxa", "servo", up58(sc.translate([P["coxa"], 0, CZ])), leg_map)
add("leg_coxa", "metal", up58(sm.translate([P["coxa"], 0, CZ])), leg_map)
add("leg_femur", "printed", U([LC.plates(), LP.knee_sleeve().translate([P["femur"], 0, 0])]), leg_map)
add("leg_femur", "servo", sc.translate([P["femur"], 0, 0]), leg_map)
add("leg_femur", "metal", sm.translate([P["femur"], 0, 0]), leg_map)
tib_rot = lambda m: m.rotate([0, -90, 0])                       # стержень голени — вдоль X (колено 0 — продолжает бедро)
add("leg_tibia", "printed", tib_rot(LP.tibia_fork()), leg_map)
add("leg_tibia", "tpu", tib_rot(LP.foot().translate([0, 0, -(P["tibia"] - P["foot_r"]) - P["foot_r"] + 1 - 4])), leg_map)

# ---------------- клешня (левая; правая — зеркало по X в three) ----------------
A1, AF, xs, H1, HT, GS = CP.C["A1"], CP.C["AF"], CP.C["xs"], CP.H1, CP.HT, CP.G_S
c15, m15 = R.s15_split(); c32, m32 = R.s32_split()
add("claw_yaw", "grey", CP.yaw_bracket(), body_map)
add("claw_yaw", "servo", CP.place(c15, CP.J2_COLS, (0, 0, 0)), body_map)
add("claw_yaw", "metal", CP.place(m15, CP.J2_COLS, (0, 0, 0)), body_map)
add("claw_up", "printed", U([CP.arm_plate(1), CP.arm_plate(-1), CP.elbow_sleeve()]), body_map)
add("claw_up", "servo", CP.place(c15, CP.J3_COLS, (A1, 0, 0)), body_map)
add("claw_up", "metal", CP.place(m15, CP.J3_COLS, (A1, 0, 0)), body_map)
el = lambda m: m                                             # предплечье в CAD уже задано от оси локтя
add("claw_fore", "printed", el(CP.forearm()), body_map)
add("claw_fore", "servo", el(CP.place(c32, CP.J4_COLS, (AF - HT, 0, 0))), body_map)
add("claw_fore", "metal", el(CP.place(m32, CP.J4_COLS, (AF - HT, 0, 0))), body_map)
piv, contact = xs + CP.C["piv"], -8.5
lt, ub = contact - CP.P32["pad"] - 0.5, contact + CP.P32["pad"] + 0.5
pd = CP.pads()
low = CP.HP.rot_y(pd.translate([piv + 2, 0, lt - 0.5]), CP.C["bend"], piv, contact)
upd = CP.HP.rot_y(pd.mirror([0, 0, 1]).translate([piv + 2, 0, ub + 0.5]), CP.C["bend"], piv, contact)
add("claw_hand", "printed", CP.hand(), body_map)
add("claw_hand", "servo", CP.place(c32, CP.J5_COLS, (xs, GS, 0)), body_map)
add("claw_hand", "metal", CP.place(m32, CP.J5_COLS, (xs, GS, 0)), body_map)
add("claw_hand", "tpu", low, body_map)
jp = lambda m: m.translate([-xs, 0, 0])                          # верхний палец — от оси J5
add("claw_jaw", "printed", jp(CP.jaw()), body_map)
add("claw_jaw", "tpu", jp(upd), body_map)

# ---------------- хвост (в системе хвоста; корень в three повёрнут на 180°) ----------------
TA1, TAF = TP.TC["A1"], TP.TC["AF"]
add("tail_yaw", "grey", TP.yaw_bracket(), body_map)
add("tail_yaw", "servo", CP.place(c15, TP.j2_cols(), (0, 0, 0)), body_map)
add("tail_yaw", "metal", CP.place(m15, TP.j2_cols(), (0, 0, 0)), body_map)
add("tail_up", "printed", U([TP.arm_plate(1), TP.arm_plate(-1), TP.elbow_sleeve()]), body_map)
add("tail_up", "servo", CP.place(c15, CP.J3_COLS, (TA1, 0, 0)), body_map)
add("tail_up", "metal", CP.place(m15, CP.J3_COLS, (TA1, 0, 0)), body_map)
add("tail_fore", "printed", TP.forearm(), body_map)
add("tail_fore", "servo", CP.place(c32, TP.W_COLS, (TAF, TP.YF, 0)), body_map)
add("tail_fore", "metal", CP.place(m32, TP.W_COLS, (TAF, TP.YF, 0)), body_map)
wr = lambda m: m.translate([-TAF, 0, 0])
add("tail_cup", "printed", wr(TP.cup_holder()), body_map)
add("tail_cup", "cup", wr(TP.cup()), body_map)

# ---------------- глаз (левый; в системе оси наклона) ----------------
add("eye", "grey", EP.horn_adapter(), body_map)
add("eye", "printed", U([EP.stalk(), EP.housing()]), body_map)
add("eye", "tpu", EP.bumper(), body_map)
add("eye", "glass", EP.display(), body_map)

# ---------------- корпус: рама, электроника, неподвижные приводы ----------------
lift = lambda m: m.translate([0, 0, ZB])
frame = [m for n, m in B.frame_parts() if not n.startswith("05_tray")]
add("body", "grey", lift(U(frame)), body_map)
add("body", "printed", lift(B.tray()), body_map)
E = B.electronics()
add("body", "pcb", lift(U([m for k, m in E.items() if ("Pi 5" in k or "Pico" in k or "BMS" in k or "DC-DC" in k)])), body_map)
add("body", "battery", lift(U([m for k, m in E.items() if "21700" in k])), body_map)
add("body", "red", lift(U([m for k, m in E.items() if "аварийной" in k])), body_map)
add("body", "servo", lift(U([m for k, m in E.items() if ("насос" in k or "динамик" in k)] + B.camera_assembly(0)[0])), body_map)
add("body", "pcb", lift(U(B.camera_assembly(0)[1])), body_map)
fixed_c, fixed_m = [], []
for n in L.MOUNTS:
    x, y, yaw = L.MOUNTS[n]
    tr = lambda m: m.translate([0, 0, P["coxa_drop"]]).rotate([0, 0, yaw]).translate([x, y, 0])
    fixed_c.append(tr(cc)); fixed_m.append(tr(cm))
for s in "LR":
    j1c = CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)); j1m = CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT))
    if s == "R":
        j1c, j1m = j1c.mirror([0, 1, 0]), j1m.mirror([0, 1, 0])
    fixed_c.append(j1c.translate(list(L.ARM_S[s]))); fixed_m.append(j1m.translate(list(L.ARM_S[s])))
    cols = [(0, 0, -1), (0, 1, 0), (1, 0, 0)]
    ec = CP.place(c32, cols, (-CP.HT, 0, 0)); em = CP.place(m32, cols, (-CP.HT, 0, 0))
    if s == "R":
        ec, em = ec.mirror([0, 1, 0]), em.mirror([0, 1, 0])
    fixed_c.append(ec.translate(list(L.EYE_PIVOT[s]))); fixed_m.append(em.translate(list(L.EYE_PIVOT[s])))
tj = lambda m: m.rotate([0, 0, 180]).translate(list(L.T_MOUNT))
fixed_c.append(tj(CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)))); fixed_m.append(tj(CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT))))
add("body", "servo", lift(U(fixed_c)), body_map)
add("shell_soft", "shell", lift(R.soft_cover()["shell"][0]), body_map)          # мягкий кожух (вариант «мягкий»)
add("body", "metal", lift(U(fixed_m)), body_map)

geo = {
    "ZJ": ZB, "arm_s": [L.ARM_S["L"][0], L.ARM_S["L"][1], L.ARM_S["L"][2] + ZB], "A1": A1, "AF": AF, "tip": [41.6, -17.5],
    "jaw_pivot": xs, "tail": [L.T_MOUNT[0], L.T_MOUNT[2] + ZB], "tail_A1": TA1, "tail_AF": TAF,
    "eye_pivot": [L.EYE_PIVOT["L"][0], L.EYE_PIVOT["L"][1], L.EYE_PIVOT["L"][2] + ZB],
    "eye_screen": [EP.housing_x()[1] - 1.6 - EP.E["lens_t"] + 0.3, 0.0, EP.E["stalk_up"]], "eye_r": 16.2,
    "tray": [-52.0, 35.0, 52.5, 66.0 + ZB],
    "edge": {"front": [127, 12, 4 + ZB], "back": [-104, 14, 4 + ZB], "side": [-28, 52, 4 + ZB]},
    "camera": [60 + 18, 0, 40 + ZB],
}
js = "// Сгенерировано модели/рендер/export_web.py — сетки звеньев Харви (компоновка v2). Не править вручную.\n"
js += "window.HARVEY_GEO=" + json.dumps(geo, ensure_ascii=False) + ";\n"
js += "window.HARVEY_MESHES=" + json.dumps(meshes, separators=(",", ":")) + ";\n"
open(OUT, "w", encoding="utf-8").write(js)
print(f"{OUT}: {os.path.getsize(OUT) / 1e6:.2f} МБ, треугольников {total[0]}")
for k, v in meshes.items():
    print(f"  {k:10s}", sum(d["n"] for d in v))
