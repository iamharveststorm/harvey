"""Харви целиком (компоновка v2) — детали по материалам для рендера в Blender и для визуализаций.
    python export_robot.py            → parts/<вариант>/<материал>.stl + parts/scene.json
Варианты: tech — открытая рама (видны приводы и электроника), soft — мягкий скруглённый кожух поверх рамы.
Система: стол z = 0, x — вперёд, мм. Поза — «привет»: стоит, левая клешня поднята, правая поджата, хвост сложен."""
import os, sys, json, math
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "корпус"))
import harvey_layout as L
import harvey_body_parts as B

LP, LC, CP, TP, EP = L.LP, L.LC, L.CP, L.TP, L.EP
box, boxr, cyl, hull = CP.box, CP.boxr, CP.cyl, CP.hull
P = LP.P

ZJ = 52.6                                   # высота осей бедра над столом в рабочей стойке
POSE = dict(
    legs={n: (0.0, 20.0, -110.0) for n in L.MOUNTS},
    claw={"L": (0.0, 129.0, -94.0, 40.0, 25.0), "R": (0.0, 14.0, -102.0, 0.0, 5.0)},
    tail=(0.0, 66.1, 126.3, 77.6),
    eye={"L": -22.0, "R": 8.0},
)


def U(ms):
    m = Manifold()
    for x in ms:
        if x is not None and not x.is_empty():
            m += x
    return m


# ---------------- корпуса приводов: «корпус» и «металл» ----------------
def leg_servo_split():
    Ls, W, H, SF = P["servo_L"], P["servo_W"], P["servo_H"], P["shaft_from_end"]
    full = LC.servo()
    case = LP.box(Ls, H, W, -(Ls / 2 - SF), 0, 0)
    return case, full - case


def coxa_servo_split():
    full = LC.coxa_servo()
    Ls, W, H, SF = P["servo_L"], P["servo_W"], P["servo_H"], P["shaft_from_end"]
    case = LP.box(Ls, W, H, -(Ls / 2 - SF), 0, -P["flange_t"] - H / 2)
    return case, full - case


def s15_split():
    case = CP.boxr(CP.TX0, CP.TX1, -CP.W / 2, CP.W / 2, -CP.H / 2, CP.H / 2)
    return case, CP.s15_body() - case


def s32_split():
    P32 = CP.P32
    case = CP.boxr(CP.X0, CP.X1, -P32["body_T"] / 2, P32["body_T"] / 2, -P32["body_D"], 0)
    return case, CP.s32_body() - case


# ---------------- ноги ----------------
def legs():
    g = {"orange": [], "grey": [], "case": [], "metal": [], "tpu": []}
    sc, sm = leg_servo_split(); cc, cm = coxa_servo_split()
    CZ = -P["coxa_drop"]
    links = {
        "base": ([], [], [(cc, cm)]),
        "coxa": ([LP.coxa_bracket()], [], [(sc.translate([P["coxa"], 0, CZ]), sm.translate([P["coxa"], 0, CZ]))]),
        "femur": ([LC.plates(), LP.knee_sleeve().translate([P["femur"], 0, 0])], [],
                  [(sc.translate([P["femur"], 0, 0]), sm.translate([P["femur"], 0, 0]))]),
        "tibia": ([LP.tibia_fork()], [LP.foot().translate([0, 0, -(P["tibia"] - P["foot_r"]) - P["foot_r"] + 1 - 4])], []),
    }
    for n in L.MOUNTS:
        qc, qf, qk = POSE["legs"][n]
        lk_print = {k: (v[0], []) for k, v in links.items()}
        lk_tpu = {k: (v[1], []) for k, v in links.items()}
        lk_case = {k: ([c for c, _ in v[2]], []) for k, v in links.items()}
        lk_metal = {k: ([m for _, m in v[2]], []) for k, v in links.items()}
        for key, lk in (("orange", lk_print), ("tpu", lk_tpu), ("case", lk_case), ("metal", lk_metal)):
            out = L.leg(n, qc, qf, qk, links=lk)
            for v in out.values():
                g[key] += v
    return g


# ---------------- клешни ----------------
def claws():
    g = {"orange": [], "grey": [], "case": [], "metal": [], "tpu": []}
    A1, AF, xs, H1, HT, GS = CP.C["A1"], CP.C["AF"], CP.C["xs"], CP.H1, CP.HT, CP.G_S
    c15, m15 = s15_split(); c32, m32 = s32_split()
    SERV = {
        "base": [(CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)), CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT)))],
        "yaw": [(CP.place(c15, CP.J2_COLS, (0, 0, 0)), CP.place(m15, CP.J2_COLS, (0, 0, 0)))],
        "up": [(CP.place(c15, CP.J3_COLS, (A1, 0, 0)), CP.place(m15, CP.J3_COLS, (A1, 0, 0)))],
        "fore": [(CP.place(c32, CP.J4_COLS, (AF - HT, 0, 0)), CP.place(m32, CP.J4_COLS, (AF - HT, 0, 0)))],
        "hand": [(CP.place(c32, CP.J5_COLS, (xs, GS, 0)), CP.place(m32, CP.J5_COLS, (xs, GS, 0)))],
    }
    piv, contact = xs + CP.C["piv"], -8.5
    lt, ub = contact - CP.P32["pad"] - 0.5, contact + CP.P32["pad"] + 0.5
    pd = CP.pads()
    low = CP.HP.rot_y(pd.translate([piv + 2, 0, lt - 0.5]), CP.C["bend"], piv, contact)
    up = CP.HP.rot_y(pd.mirror([0, 0, 1]).translate([piv + 2, 0, ub + 0.5]), CP.C["bend"], piv, contact)
    printed = {"base": [], "yaw": [CP.yaw_bracket()], "up": [CP.arm_plate(1), CP.arm_plate(-1), CP.elbow_sleeve()],
               "fore": [CP.forearm()], "hand": [CP.hand()], "jaw": [CP.jaw()]}
    for s in "LR":
        q = POSE["claw"][s]
        sets = {"orange": {k: (v if k != "yaw" else [], []) for k, v in printed.items()},
                "grey": {k: (v if k == "yaw" else [], []) for k, v in printed.items()},
                "case": {k: ([c for c, _ in SERV.get(k, [])], []) for k in printed},
                "metal": {k: ([m for _, m in SERV.get(k, [])], []) for k in printed},
                "tpu": {k: ([low] if k == "hand" else [up] if k == "jaw" else [], []) for k in printed}}
        for key, pr in sets.items():
            out = L.claw(s, q if s == "L" else q, parts=pr)
            for v in out.values():
                g[key] += v
    return g


# ---------------- хвост ----------------
def tail():
    g = {"orange": [], "grey": [], "case": [], "metal": [], "tpu": [], "silicone": []}
    A1, AF, H1, HT = TP.TC["A1"], TP.TC["AF"], CP.H1, CP.HT
    c15, m15 = s15_split(); c32, m32 = s32_split()
    SERV = {
        "base": [(CP.place(c32, CP.J1_COLS, (0, 0, -H1 - HT)), CP.place(m32, CP.J1_COLS, (0, 0, -H1 - HT)))],
        "yaw": [(CP.place(c15, TP.j2_cols(), (0, 0, 0)), CP.place(m15, TP.j2_cols(), (0, 0, 0)))],
        "up": [(CP.place(c15, CP.J3_COLS, (A1, 0, 0)), CP.place(m15, CP.J3_COLS, (A1, 0, 0)))],
        "fore": [(CP.place(c32, TP.W_COLS, (AF, TP.YF, 0)), CP.place(m32, TP.W_COLS, (AF, TP.YF, 0)))],
    }
    printed = {"base": [], "yaw": [TP.yaw_bracket()], "up": [TP.arm_plate(1), TP.arm_plate(-1), TP.elbow_sleeve()],
               "fore": [TP.forearm()], "cup": [TP.cup_holder()]}
    sets = {"orange": {k: (v if k != "yaw" else [], []) for k, v in printed.items()},
            "grey": {k: (v if k == "yaw" else [], []) for k, v in printed.items()},
            "case": {k: ([c for c, _ in SERV.get(k, [])], []) for k in printed},
            "metal": {k: ([m for _, m in SERV.get(k, [])], []) for k in printed},
            "silicone": {k: ([TP.cup()] if k == "cup" else [], []) for k in printed}}
    for key, pr in sets.items():
        out = L.tail(POSE["tail"], parts=pr)
        for v in out.values():
            g[key] += v
    return g


# ---------------- глаза ----------------
def eyes():
    g = {"orange": [], "grey": [], "case": [], "metal": [], "tpu": [], "glass": []}
    c32, m32 = s32_split()
    cols = [(0, 0, -1), (0, 1, 0), (1, 0, 0)]
    sc = CP.place(c32, cols, (-CP.HT, 0, 0)); sm = CP.place(m32, cols, (-CP.HT, 0, 0))
    screens = {}
    for s in "LR":
        t = POSE["eye"][s]
        parts_ = {"grey": [EP.horn_adapter()], "orange": [EP.stalk(), EP.housing()], "tpu": [EP.bumper()],
                  "glass": [EP.display()]}
        for key, ms in parts_.items():
            out = L.eye(s, t, parts=(ms, Manifold()))
            g[key] += out["moving"]
        out = L.eye(s, t, parts=([], sc)); g["case"] += out["fixed"]
        out = L.eye(s, t, parts=([], sm)); g["metal"] += out["fixed"]
        # центр и нормаль экрана (для картинки глаза в Blender)
        c = np.array(EP.eye_center()); x1 = EP.housing_x()[1]
        pts = {"c": np.array([x1 - 1.6 - EP.E["lens_t"] + 0.2, c[1], c[2]]), "n": np.array([1.0, 0, 0]), "up": np.array([0, 0, 1.0])}
        a = math.radians(t)
        R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        sy = 1 if s == "L" else -1
        M = np.diag([1, sy, 1])
        piv = np.array(L.EYE_PIVOT[s])
        screens[s] = {"center": (M @ (R @ pts["c"]) + piv + [0, 0, ZJ + 2]).tolist(),
                      "normal": (M @ (R @ pts["n"])).tolist(), "up": (M @ (R @ pts["up"])).tolist(),
                      "radius": 16.2}
    return g, screens


# ---------------- корпус ----------------
def frame():
    g = {"grey": [], "orange": [], "pcb": [], "battery": [], "dark": [], "red": [], "case": [], "metal": [], "glass": []}
    for n, m in B.frame_parts():
        (g["orange"] if n.startswith("05_tray") else g["grey"]).append(m)
    E = B.electronics()
    for k, m in E.items():
        if "Pi 5" in k or "Pico" in k or "BMS" in k or "DC-DC" in k:
            g["pcb"].append(m)
        elif "21700" in k:
            g["battery"].append(m)
        elif "аварийной" in k:
            g["red"].append(m)
        else:
            g["dark"].append(m)
    sv, cam = B.camera_assembly(0.0)
    g["case"] += sv; g["pcb"] += cam
    return g


def soft_cover():
    """Мягкий скруглённый кожух (вариант для рендера): гладкий панцирь-купол между основаниями ног (по границе
    зон, где ходят ноги), «лицо» под клешнями и капля хвоста. Совместимость — той же проверкой, что и рама."""
    def sph(p, r):
        return Manifold.sphere(r, 48).translate(list(p))
    def inset(d):
        out = []
        for n, (x, y, yaw) in L.MOUNTS.items():
            k = math.hypot(x, y); out.append((x - d * x / k, y - d * y / k))
        return out
    pts = [sph((x, y, z), r) for (x, y) in inset(14.5) for z, r in ((-4, 11), (44, 11))]
    pts += [sph((x, y, 56), 6) for (x, y) in inset(34)]
    shell = Manifold.batch_hull(pts)                                     # панцирь
    face = Manifold.batch_hull([sph((x, y, z), 7) for x in (50, 119) for y in (-13, 13) for z in (-6, 10)])
    head = Manifold.batch_hull([sph((x, y, z), 8) for x in (52, 72) for y in (-11, 11) for z in (24, 47)]) - CP.boxr(70, 90, -13, 13, 28, 52)
    tailpod = Manifold.batch_hull([sph((x, y, z), 7) for x in (-97, -66) for y in (-14, 14) for z in (-6, 16)])
    lid = Manifold.batch_hull([sph((x, y, 68.5), 3.5) for x in (-42, 33) for y in (-52, 52)]
                              + [sph((x, y, 68.0), 3.5) for x in (-44, 35) for y in (-54, 54)])    # крышка-спина вместо подноса: z 64,5…72
    shell = shell + face + head + tailpod + lid
    for f in B.fixed_hardware():                                      # проёмы: корпуса приводов выглядывают из «панциря»
        shell -= f
    for n in L.MOUNTS:
        shell -= B.to_leg(B.sleeve_leg()[0], n)
    return {"shell": [shell]}


def robot(variant):
    groups = {}
    def add(g):
        for k, v in g.items():
            groups.setdefault(k, []).extend(v)
    add(legs()); add(claws()); add(tail())
    eg, screens = eyes(); add(eg)
    add(frame())
    if variant == "soft":
        sc = soft_cover()
        add(sc)
        for k in ("pcb", "battery", "dark"):
            groups[k] = []
        tray = B.tray()                                   # поднос — под крышкой, не нужен
        groups["orange"] = [m for m in groups["orange"] if m is not tray]
    out = {k: U(v).translate([0, 0, ZJ + 2.0]) for k, v in groups.items() if v}
    return out, screens


if __name__ == "__main__":
    os.chdir(HERE)
    meta = {}
    for variant in ("tech", "soft"):
        d = os.path.join("parts", variant); os.makedirs(d, exist_ok=True)
        groups, screens = robot(variant)
        for k, m in groups.items():
            CP.to_trimesh(m).export(os.path.join(d, k + ".stl"))
            print(variant, k, len(m.to_mesh().tri_verts), "треугольников")
        meta[variant] = {"materials": sorted(groups)}
    meta["screens"] = screens
    meta["pose"] = POSE
    json.dump(meta, open(os.path.join("parts", "scene.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if "--check" in sys.argv:
        bad = B.check(frame=[("кожух", soft_cover()["shell"][0])], verbose=True)
