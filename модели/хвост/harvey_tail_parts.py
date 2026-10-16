"""Харви: хвост — «третья рука» с присоской (STL). 4 привода:
поворот T1 (STS3032) → подъём T2 (STS3215) → плечо 70 → локоть T3 (STS3215) → предплечье 70 →
наклон запястья T4 (STS3032) → держатель присоски (присоска Ø22 на сильфоне, 26 мм от оси запястья).
Основание, поворотная стойка, пластины плеча и обхват локтя — те же узлы, что у клешни
(модели/клешни/harvey_claw_parts.py), с длиной плеча 70 мм и своим углом установки привода подъёма.
Система хвоста: начало — точка T (ось подъёма пересекает ось поворота), x — вдоль хвоста (назад от робота),
z — вверх. Трубка насоса идёт по хвосту в клипсах к штуцеру держателя присоски.
    python harvey_tail_parts.py      # STL в stl/, ходы и проверки в консоли"""
import os, math, importlib.util
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("harvey_claw_parts", os.path.join(HERE, "..", "клешни", "harvey_claw_parts.py"))
CP = importlib.util.module_from_spec(spec); spec.loader.exec_module(CP)
box, boxr, cyl, place, to_trimesh, hull = CP.box, CP.boxr, CP.cyl, CP.place, CP.to_trimesh, CP.hull
P32, L15 = CP.P32, CP.L15

TC = dict(
    A1=70.0,        # плечо T2 → T3 (как в симуляции)
    AF=70.0,        # предплечье T3 → ось запястья T4 (как в симуляции)
    beta=-90.0,     # длинная часть корпуса T2 — вниз: поворотная стойка — компактная колонна, не нависает над подносом
    BR=(24.0, 27.4),
    cup_arm=26.0,   # от оси запястья до поверхности присоски (симуляция: 26)
    cup_d=22.0,     # присоска Ø20–25 мм на сильфоне — покупная
)
HT, G_S = CP.HT, CP.G_S


def with_tail_params(fn, *a, **k):
    """Вызов узла клешни с размерами хвоста (плечо 70, свой угол привода подъёма)."""
    old = dict(CP.C)
    CP.C.update(A1=TC["A1"], beta=TC["beta"])
    cols = CP.J2_COLS
    b = math.radians(TC["beta"]); u = (-math.cos(b), 0.0, -math.sin(b))
    CP.J2_COLS = [u, (u[2], 0.0, -u[0]), (0.0, 1.0, 0.0)]
    try:
        return fn(*a, **k)
    finally:
        CP.C.clear(); CP.C.update(old); CP.J2_COLS = cols


def j2_cols():
    b = math.radians(TC["beta"]); u = (-math.cos(b), 0.0, -math.sin(b))
    return [u, (u[2], 0.0, -u[0]), (0.0, 1.0, 0.0)]


def base():
    return CP.base()


def yaw_bracket():
    return with_tail_params(CP.yaw_bracket)


def arm_plate(side):
    return with_tail_params(CP.arm_plate, side)


def elbow_sleeve():
    return with_tail_params(CP.elbow_sleeve)


BEAM = (25.0, 29.0)        # балки вилки (|y|) — снаружи пластин плеча (они до 21,8): при сгибе локтя проходят мимо
YF = BEAM[0] + 0.5 - 3.0 - 0.3 - P32["body_D"]   # −5,3: передний торец T4 (вал по −y); задний торец — у балки +y
W_COLS = [(0, 0, 1), (-1, 0, 0), (0, -1, 0)]      # S: x → +z (длинная часть корпуса вниз), y → −x, вал → −y
XBAR = (32.0, 38.0)        # поперечина вилки — снизу и за кругом, который заметает присоска (R ≈ 28 от T4)


def forearm():
    """Предплечье-вилка: уши на обоих фланцах T3, балки СНАРУЖИ пластин плеча — локоть складывается почти вдвое;
    поперечина снизу (при сгибе уходит вверх, мимо обхвата локтя). Привод запястья T4 стоит между балками
    и держится задним торцом (4 × M2 в ушки, как спереди) за плиту на балке +y; держатель присоски
    крутится внутри вилки на передней качалке."""
    AF, t = TC["AF"], CP.T4
    YS = CP.YS
    b0, b1 = BEAM
    yr = YF + P32["body_D"] + 0.3                                    # задний торец T4 + зазор
    m = Manifold()
    for s in (1, -1):
        ear = cyl(22.3 - YS, 13, 0, s * (YS + 22.3) / 2, 0, "y")             # тонкая часть — в слое пластин плеча
        ear += cyl(b1 - 22.3, 16, 0, s * (22.3 + b1) / 2, 0, "y")             # толстая — до балки
        ear -= CP.flange_plate_cut(t).rotate([-90 if s > 0 else 90, 0, 0]).translate([0, s * YS, 0])
        for k in range(4):                                                    # колодцы под головки M3 фланца
            a = math.radians(45 + 90 * k)
            ear -= hull(*(cyl(b1 - YS - t + 1, 3.2, r * math.cos(a), s * (YS + t + (b1 - YS - t + 1) / 2), r * math.sin(a), "y")
                          for r in (5.5, 9.5)))
        x_end = AF if s > 0 else XBAR[1] - 3
        beam = hull(cyl(b1 - b0, 8.0, 8, s * (b0 + b1) / 2, 0, "y"), cyl(b1 - b0, 9.0 if s > 0 else 7.0, x_end, s * (b0 + b1) / 2, 0, "y"))
        m += ear + beam
    m += boxr(XBAR[0], XBAR[1], -b1, b1, -13, -4)                    # поперечина
    m += boxr(AF - 11, AF + 11, yr, b0 + 0.5, -19, 7)                # плита на задний торец T4
    m -= cyl(30, P32["horn_D"] / 2 + 1.0, AF, b1, 0, "y")             # окно под заднюю качалку T4
    for zs in (-14.8, -5.8, 3.2):                                    # 6 × M2 × 10 в ушки заднего торца
        for xo in (P32["holes_y"], -P32["holes_y"]):
            m -= cyl(30, P32["m2"] / 2, AF + xo, b1, zs, "y")
    for x in (16.0, 30.0):                                           # клипсы под трубку Ø4 снаружи балки −y
        m += boxr(x - 2.5, x + 2.5, -b1 - 6, -b1 + 0.5, -4, 4) - cyl(8, 2.1, x, -b1 - 3.2, 0, "x") \
            - boxr(x - 3, x + 3, -b1 - 7, -b1 - 4.5, -1.5, 1.5)
    return m


def cup_holder():
    """Держатель присоски: диск на качалку T4 → рычаг 26 мм → гнездо Ø14 под шток присоски с сильфоном,
    штуцер Ø4 под трубку насоса (канал по рычагу до центра присоски). Строится в средней плоскости y = 0
    и сдвигается на переднюю качалку T4 (y = YF − G_S)."""
    AF, ca = TC["AF"], TC["cup_arm"]
    t = P32["jaw_w"]
    m = place(CP.HP.horn_disk(t, 7.5).translate([0, 0, HT]), W_COLS, (AF, G_S, 0))    # диск y ∈ [−2; 2]
    xc = AF + ca - 6.0                                             # гнездо штока (присоска торчит ещё на 6)
    m += hull(cyl(t, 5.5, AF, 0, 0, "y"), cyl(t, 5.0, xc - 4, 0, 0, "y"))
    m += cyl(10, 7.0, xc, 0, 0, "x")                               # гнездо: цилиндр вдоль рычага
    m -= cyl(8.1, 4.1, xc + 1.0, 0, 0, "x")                        # под шток присоски Ø8 (клей или на резьбу M8)
    m -= cyl(xc - AF - 2, 1.2, (AF + xc) / 2 + 2, 0, 0, "x")        # воздушный канал Ø2,4 по рычагу
    m += cyl(6, 2.0, xc - 6, 0, 5.5, "z") - cyl(8, 1.2, xc - 6, 0, 5.5, "z")   # штуцер под трубку Ø4/2,5
    m -= cyl(6, 1.2, xc - 6, 0, 3.0, "z")
    for k in range(4):                                             # винты в качалку T4
        a = math.radians(90 * k)
        z, x = P32["horn_pcd"] / 2 * math.cos(a), -P32["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(10, P32["m2"] / 2, AF + x, 0, z, "y")
    m -= cyl(10, 2.3, AF, 0, 0, "y")
    return m.translate([0, YF - G_S - 0.2, 0])   # 0,2 мм от торца качалки


def cup():
    """Присоска Ø22 на сильфоне (покупная) — для проверок и рендера, не печатается."""
    AF, ca, r = TC["AF"], TC["cup_arm"], TC["cup_d"] / 2
    xc = AF + ca - 6.0
    m = cyl(10, 4.0, xc + 5, 0, 0, "x")                             # шток и сильфон
    m += hull(cyl(1, r * 0.55, xc + 10.5, 0, 0, "x"), cyl(1, r, AF + ca - 0.5, 0, 0, "x"))   # юбка
    return m.translate([0, YF - G_S - 0.2, 0])   # 0,2 мм от торца качалки


# ---------------- сборка ----------------
def link_parts():
    A1, AF = TC["A1"], TC["AF"]
    H1 = CP.H1
    s15 = CP.s15_body
    return {
        "base": ([base()], [place(CP.s32_body(), CP.J1_COLS, (0, 0, -H1 - HT))]),
        "yaw": ([yaw_bracket()], [place(s15(), j2_cols(), (0, 0, 0))]),
        "up": ([arm_plate(1), arm_plate(-1), elbow_sleeve()], [place(s15(), CP.J3_COLS, (A1, 0, 0))]),
        "fore": ([forearm()], [place(CP.s32_body(), W_COLS, (AF, YF, 0))]),
        "cup": ([cup_holder()], [cup()]),
    }


def posed(parts, q):
    """q = (поворот, подъём, локоть, запястье), градусы."""
    q1, qp, qe, qw = q
    A1, AF = TC["A1"], TC["AF"]
    def T(link, m):
        if link == "base":
            return m
        if link == "cup":
            m = CP.rot(m, "y", -qw, (AF, 0, 0))
        if link in ("fore", "cup"):
            m = CP.rot(m, "y", -qe).translate([A1, 0, 0])
        if link in ("up", "fore", "cup"):
            m = CP.rot(m, "y", -qp)
        return CP.rot(m, "z", q1)
    return {link: [T(link, m) for m in pr + sv] for link, (pr, sv) in parts.items()}


PAIRS = [("base", "up"), ("base", "fore"), ("base", "cup"), ("yaw", "up"), ("yaw", "fore"), ("yaw", "cup"),
         ("up", "cup"), ("up", "fore"), ("fore", "cup")]


def worst(P_, pairs=PAIRS):
    w = (0.0, "")
    for a, b in pairs:
        for i, x in enumerate(P_[a]):
            for j, y in enumerate(P_[b]):
                v = (x ^ y).volume()
                if v > w[0]:
                    w = (v, f"{a}[{i}]×{b}[{j}]")
    return w


if __name__ == "__main__":
    os.chdir(HERE); os.makedirs("stl", exist_ok=True)
    parts = link_parts()
    print("Посадки на свои приводы:")
    for link, (pr, sv) in parts.items():
        for i, p in enumerate(pr):
            for s in sv:
                print(f"  {link}[{i}] × свой: {(p ^ s).volume():.1f} мм³")
    for name, j, rng, q0 in (("подъём T2 (нужно −72…+140)", 1, range(-90, 181, 5), (0, 0, 0, 0)),
                             ("локоть T3 (нужно −18…+147)", 2, range(-180, 181, 5), (0, 30, 0, 0)),
                             ("запястье T4 (нужно −160…+160)", 3, range(-180, 181, 10), (0, 30, 60, 0))):
        ok = []
        for v in rng:
            q = list(q0); q[j] = v
            ok.append((v, worst(posed(parts, q))[0] <= 0.5))
        vals = [v for v, _ in ok]; good = dict(ok)
        z = q0[j] if q0[j] in good else vals[len(vals) // 2]
        i = vals.index(z); lo = hi = i
        while lo > 0 and good[vals[lo - 1]]: lo -= 1
        while hi < len(vals) - 1 and good[vals[hi + 1]]: hi += 1
        print(f"{name}: без столкновений {vals[lo]}…{vals[hi]}" if good[z] else f"{name}: столкновение уже в {z}")
    PARTS = [("01_base", base()), ("02_yaw_bracket", yaw_bracket()), ("03_arm_plate_outer", arm_plate(-1)),
             ("04_arm_plate_inner", arm_plate(1)), ("05_elbow_sleeve", elbow_sleeve()), ("06_forearm", forearm()),
             ("07_cup_holder", cup_holder())]
    for n, m in PARTS:
        tm = to_trimesh(m)
        print(f"  {n:20s} {tm.volume / 1000 * 1.27:5.1f} г, цельная: {tm.is_watertight and len(m.decompose()) == 1}")
        tm.export(f"stl/{n}.stl")
