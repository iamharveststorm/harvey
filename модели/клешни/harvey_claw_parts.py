"""Харви: обе клешни целиком для 3D-печати (STL), по 5 приводов в каждой.
Цепочка (как в симуляции): поворот плеча J1 (STS3032) → подъём плеча J2 (STS3215) → плечо →
локоть J3 (STS3215) → предплечье → вращение запястья J4 (STS3032) → кисть с захватом J5 (STS3032).
Правая клешня строится в своей системе, левая — зеркало по y (приводы в ней стоят перевёрнутыми,
посадочные места те же).
Система плеча: начало — точка S (ось подъёма J2 пересекает ось поворота J1), x — вперёд, y — влево, z — вверх.
Детали держат приводы обхватом корпуса и за фланцы/качалки — как стенды ноги и кисти; размеры приводов
берутся из скриптов стендов (там же пометки «ИЗМЕРИТЬ»).
    pip install manifold3d trimesh numpy
    python harvey_claw_parts.py      # STL в stl/, ходы суставов и проверки в консоли"""
import os, math, importlib.util
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, *rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, *rel))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


LP = _load("harvey_leg_parts", "..", "стенд ноги", "harvey_leg_parts.py")
HP = _load("harvey_hand_parts", "..", "стенд кисти", "harvey_hand_parts.py")
box, boxr, cyl, place = HP.box, HP.boxr, HP.cyl, HP.place
L15, P32 = LP.P, HP.P


def to_trimesh(m):
    """Сетка как есть, без слияния вершин: слияние склеивает почти совпадающие вершины и рвёт замкнутость."""
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)

# ---------------- параметры клешни, мм ----------------
C = dict(
    A1=54.0,        # плечо: ось J2 → ось J3. В симуляции 45, но два корпуса STS3215 там не помещаются:
                    # угол корпуса J2 (повёрнут на β) выходит на 17,5 мм от оси, обхват J3 — на 36 мм от J3
    AF=60.0,        # предплечье: ось J3 → плоскость качалки J4 (как в симуляции)
    beta=-100.0,    # длинная часть корпуса J2 — почти вниз: стойка поворота компактная (выступает назад на 23 мм, а не 37) — помещается перед передней ногой; рука не опускается ниже −15°
    gap=0.3, wall=3.0, plate=4.0,
    yaw_r=23.0,     # диск поворота плеча — лежит на опорном кольце основания, изгиб не на валу J1
    yaw_cut=12.0,   # спереди диск срезан (под рукой, опущенной вниз): опора на кольцо — сзади и с боков
    ring=(19.5, 22.0),          # опорное кольцо основания (под тефлоновую шайбу или ленту)
    base_x=(-56.0, 18.0),       # основание: плечо на переднем крае панциря — вперёд почти не выступает
    base_y=31.0,
    base_holes=((-50.0, 25.0), (12.0, 25.0)),   # 4 × M3 к панцирю: (x, ±y)
    sleeve_x1=-18.0,            # обхваты STS3215 кончаются за 18 мм до оси вала (больше ход соседнего звена)
    case_screw=(-30.7, 10.1),   # задние винты корпуса STS3215 (чертёж даташита: 8 × PA2.0 в углах), x_T и ±y_T:
                                # их меняют на винты длиннее на 1,5 мм — они держат корпус в обхвате   ИЗМЕРИТЬ
    BR=(24.0, 27.4),            # мост вилки предплечья (от оси J3): за корпусом J4, окно под его заднюю качалку
    chamfer=5.0,    # фаски на переднем крае обхвата локтя — там проходит задняя качалка J4 при сгибе
    rail_y=(10.0, 13.0),        # рёбра предплечья по бокам от J4 (ушки J4 — до 9,5)
    xs=15.0,        # ось захвата J5 от плоскости качалки J4
    piv=11.0,       # изгиб пальцев — дальше оси J5 на столько
    finger=18.0,    # длина пальцев (на стенде кисти 26 — здесь короче, кисть компактнее)
    bend=30.0,
)
# STS3215 в системе T: вал — z, корпус x ∈ [−(L−s), s], y ± W/2, z ± H/2, фланцы Ø20 на |z| = H/2 … H/2+ft
L, W, H, SF = L15["servo_L"], L15["servo_W"], L15["servo_H"], L15["shaft_from_end"]
FD, FT = L15["flange_D"], L15["flange_t"]
TX0, TX1 = -(L - SF), SF
YS = H / 2 + FT - 1.3          # внутренняя плоскость пластин на фланцах (фланец утоплен на 1,3)
T4 = C["plate"]
# STS3032 в системе S: вал — z, торец z = 0, корпус z ∈ [−D, 0], x ∈ [X0, X1], y ± T/2
X0, X1, HT = HP.X0, HP.X1, P32["horn_top"]
G_S = HT + P32["jaw_w"] / 2     # 6,8: торец J5 от плоскости пальцев


def rot(m, axis, deg, center=(0, 0, 0)):
    c = np.array(center, float); r = [0, 0, 0]; r["xyz".index(axis)] = deg
    return m.translate(list(-c)).rotate(r).translate(list(c))


def hull(*ms):
    return Manifold.batch_hull(list(ms))


# ---------------- ориентации приводов ----------------
_b = math.radians(C["beta"])
U2 = (-math.cos(_b), 0.0, -math.sin(_b))                 # x_T привода J2 — от длинной части к валу
J2_COLS = [U2, (U2[2], 0.0, -U2[0]), (0.0, 1.0, 0.0)]    # вал J2 — по +y
J3_COLS = [(1, 0, 0), (0, 0, -1), (0, 1, 0)]             # J3: длинная часть назад, к J2; вал по +y
J1_COLS = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]              # J1: вал вверх
J4_COLS = HP.W_COLS                                      # J4: вал по +x, длинная часть корпуса вниз
J5_COLS = [(0, 0, 1), (-1, 0, 0), (0, -1, 0)]            # J5: вал по −y, корпус стоит вертикально
for cols in (J1_COLS, J2_COLS, J3_COLS, J4_COLS, J5_COLS):
    a_, b_, c_ = (np.array(v, float) for v in cols)
    assert np.allclose(np.cross(a_, b_), c_), cols


# ---------------- корпуса приводов (для проверок, не печатаются) ----------------
def s15_body():
    b = boxr(TX0, TX1, -W / 2, W / 2, -H / 2, H / 2)
    for z in (H / 2 + FT / 2, -H / 2 - FT / 2):
        b += cyl(FT, FD / 2, 0, 0, z)
    return b + s15_case_heads()


def s32_body():
    return HP.servo_body()


# ---------------- общие узлы ----------------
def s15_sleeve(x1=None, inserts=(), chamfer=0.0):
    """Обхват задней части корпуса STS3215 в системе T; стенки по z_T (вдоль вала) — заподлицо с фланцами.
    inserts — x_T отверстий под латунные вставки M3 насквозь по z_T (к ним крепятся пластины);
    chamfer — фаски 45° на переднем крае стенок по y_T."""
    g, w = C["gap"], C["wall"]
    x1 = C["sleeve_x1"] if x1 is None else x1
    x0 = TX0 - g
    yo = W / 2 + g + w
    m = boxr(x0 - w, x1, -yo, yo, -YS, YS)
    for sy in (1, -1):
        if chamfer > 0:
            m -= box(2 * chamfer, 2 * chamfer, 2 * YS + 2).rotate([0, 0, 45]).translate([x1, sy * yo, 0])
    m -= boxr(x0, x1 + 1, -(W / 2 + g), W / 2 + g, -(H / 2 + g), H / 2 + g)
    m -= boxr(x0 - w - 1, x0 + 1, -6, 6, -5, 5)                        # выход кабеля
    cx, cy = C["case_screw"]
    for sy in (1, -1):                                                 # длинные винты корпуса — сквозь стенки
        m -= cyl(2 * YS + 2, 1.1, cx, sy * cy, 0)
    for x in inserts:
        m -= cyl(2 * YS + 2, L15["insert"] / 2, x, 0, 0)
    return m


def s15_case_heads():
    """Головки удлинённых винтов корпуса STS3215 (в системе T) — для проверок столкновений."""
    cx, cy = C["case_screw"]
    m = Manifold()
    for sy in (1, -1):
        for sz in (1, -1):
            m += cyl(1.6, 1.9, cx, sy * cy, sz * (YS + 0.8))
    return m


def s32_plate(cols_x, t=3.0):
    """Пластина на торец STS3032 (как на стенде кисти), но со своим выбором столбцов винтов M2:
    cols_x — x_S отверстий из (−14,8; −5,8; 3,2), ряды y = ±8."""
    m = boxr(X0 - 2.0, X1 + 2.3, -11, 11, 0, t)
    m -= cyl(t + 2, P32["horn_D"] / 2 + 0.5, 0, 0, t / 2)
    for x in cols_x:
        for y in (P32["holes_y"], -P32["holes_y"]):
            m -= cyl(t + 2, P32["m2"] / 2, x, y, t / 2)
            m -= cyl(1.6 + 0.01, P32["m2_head"] / 2, x, y, t - 0.8 + 0.005)
    return m


def flange_plate_cut(t):
    """Гнездо под фланец STS3215 + пазы M3 в пластине толщиной t (пластина z ∈ [0, t], фланец снизу)."""
    return LP.flange_cut(t, "bottom")


def finger_bar(piv, z0, z1, contact, flen, bend, half):
    root = boxr(piv - 2, piv, -half, half, z0, z1)
    tip = HP.rot_y(boxr(piv, piv + flen, -half, half, z0, z1), bend, piv, contact)
    joint = hull(root, HP.rot_y(boxr(piv, piv + 2, -half, half, z0, z1), bend, piv, contact))
    end = HP.rot_y(cyl(2 * half, (z1 - z0) / 2, piv + flen, 0, (z0 + z1) / 2, "y"), bend, piv, contact)
    return root + tip + joint + end


# ---------------- детали (правая клешня; системы звеньев) ----------------
def yaw_frame():
    """Высота H1 — от S вниз до плоскости качалки J1: под нижнюю точку обхвата J2 и диск поворота."""
    sl = place(s15_sleeve(), J2_COLS, (0, 0, 0))
    zmin = sl.bounding_box()[2]
    return -zmin + 4.0 + 1.0


H1 = None


def base():
    """Основание плеча (неподвижно, в панцирь): пластина на торец J1, опорное кольцо, 4 × M3 к панцирю."""
    zf = -H1 - HT                                               # торец J1
    bx0, bx1 = C["base_x"]; by = C["base_y"]
    m = boxr(bx0, bx1, -by, by, zf, zf + 3)
    m -= cyl(10, P32["horn_D"] / 2 + 0.5, 0, 0, zf)                  # окно под качалку J1
    for x in P32["holes_x"][:2]:                                     # J1 висит под пластиной, 4 × M2 сверху
        for y in (P32["holes_y"], -P32["holes_y"]):
            m -= cyl(10, P32["m2"] / 2, x, y, zf)
            m -= cyl(1.6 + 0.01, P32["m2_head"] / 2, x, y, zf + 3 - 0.8 + 0.005)
    r0, r1 = C["ring"]
    ring = cyl(-H1 - 0.3 - (zf + 3), r1, 0, 0, (zf + 3 + (-H1 - 0.3)) / 2) - cyl(10, r0, 0, 0, zf + 3)
    m += ring
    for hx, hy in C["base_holes"]:
        for sy in (1, -1):
            m -= cyl(10, L15["m3"] / 2, hx, sy * hy, zf)              # к панцирю: M3 во вставки панциря
    return m


def yaw_bracket():
    """Поворотная стойка: диск на качалку J1 → стенка → обхват задней части J2 (повёрнут на β)."""
    zd = -H1                                                    # низ диска = плоскость качалки J1
    disk = cyl(4.0, C["yaw_r"], 0, 0, zd + 2.0) - boxr(C["yaw_cut"], 50, -50, 50, zd - 1, zd + 5)
    sl = place(s15_sleeve(), J2_COLS, (0, 0, 0))
    bb = sl.bounding_box()
    foot = boxr(bb[0], bb[3], -YS, YS, zd + 3.9, zd + 4.0)           # опора — проекция обхвата на диск
    web = hull(sl, foot) - place(boxr(TX0 - C["gap"], TX1 + 20, -(W / 2 + C["gap"]), W / 2 + C["gap"], -YS - 1, YS + 1),
                                 J2_COLS, (0, 0, 0))
    web -= cyl(60, FD / 2 + 4.5, 0, 0, 0, "y")                      # вокруг оси J2 — фланцы и пластины плеча
    m = disk + web + sl
    m -= cyl(20, 2.3, 0, 0, zd)                                     # доступ к винту качалки J1
    # колодцы для отвёртки сквозь дно обхвата J2: стойку крепят к качалке J1, пока J2 ещё не вставлен
    for k in (1, 3, 5, 7):
        a = math.radians(45 * k)
        x, y = P32["horn_pcd"] / 2 * math.cos(a), P32["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(60, P32["m2_head"] / 2 + 0.3, x, y, zd + 4 + 30)
    m -= cyl(60, 2.6, 0, 0, zd + 4 + 30)
    # винты в качалку J1 (8 мест на Ø10): сверлим только те, к которым сверху подлезает ключ
    for x, y in yaw_screws(m, zd):
        m -= cyl(20, P32["m2"] / 2, x, y, zd)
        m -= cyl(1.2, P32["m2_head"] / 2, x, y, zd + 4 - 0.6 + 0.005)
    return m


def yaw_screws(body, zd):
    out = []
    for k in range(8):
        a = math.radians(45 * k)
        x, y = P32["horn_pcd"] / 2 * math.cos(a), P32["horn_pcd"] / 2 * math.sin(a)
        if (body ^ cyl(20, P32["m2_head"] / 2, x, y, zd + 4 + 10.01)).volume() < 0.01:
            out.append((x, y))
    return out


def arm_plate(side):
    """Пластина плеча (2 шт. на клешню, side = ±1): у J2 — на фланец, у J3 — к обхвату J3 двумя M3."""
    A1, t = C["A1"], T4
    end = A1 - 26                                                   # конец не доходит до ушей вилки при сгибе локтя
    p = hull(cyl(t, 14, 0, 0, t / 2), cyl(t, 9, end, 0, t / 2))
    p -= flange_plate_cut(t)
    for x in INS:
        p -= cyl(t + 2, L15["m3"] / 2, A1 + x, 0, t / 2)
    cx, cy = C["case_screw"]
    for sy in (1, -1):                                              # карманы под головки винтов корпуса J3
        p -= cyl(2 * 1.8, 2.2, A1 + cx, sy * cy, 0)
    # пластина в плоскости xz; z_пластины → ±y мира, гнездо фланца — с внутренней стороны
    p = p.rotate([-90, 0, 0]) if side > 0 else p.rotate([90, 0, 0])
    return p.translate([0, side * YS, 0])


INS = (-22.0, -29.0)            # вставки M3 в обхвате локтя (от оси J3); к ним — пластины плеча


def elbow_sleeve():
    return place(s15_sleeve(inserts=INS, chamfer=C["chamfer"]), J3_COLS, (C["A1"], 0, 0))


def forearm():
    """Предплечье (вилка): уши на фланцах J3 → мост → рёбра по бокам J4 → пластина на торец J4."""
    (b0, b1), AF, t = C["BR"], C["AF"], T4
    m = Manifold()
    for s in (1, -1):
        ear = hull(cyl(t, 13, 0, 0, 0, "y"), boxr(b0, b1, -t / 2, t / 2, -8, 8))
        ear = ear.translate([0, s * (YS + t / 2), 0])
        cut = flange_plate_cut(t).rotate([-90 if s > 0 else 90, 0, 0]).translate([0, s * YS, 0])
        m += ear - cut
    m += boxr(b0, b1, -(YS + t), YS + t, -8, 8)                      # мост = задняя пластина за корпусом J4
    r0, r1 = C["rail_y"]
    xp = AF - HT                                                    # торец J4
    xb = xp - P32["body_D"]                                         # задний торец J4
    for s in (1, -1):
        m += boxr(b0, xp + 3, min(s * r0, s * r1), max(s * r0, s * r1), -21.5, 8)
    m += place(HP.servo_plate(3.0), J4_COLS, (xp, 0, 0))
    m += boxr(xb + 3, xb + 7, -r1, r1, -21.5, -18.0)                # хомут под корпусом J4
    m -= cyl(20, P32["horn_D"] / 2 + 1.2, xb - 5, 0, 0, "x")        # задняя качалка J4 крутится в окне моста
    for zs in (-5.8, 3.2):                                          # M2 в задний торец J4 (ушки — как спереди)
        for ys in (P32["holes_y"], -P32["holes_y"]):
            m -= cyl(20, P32["m2"] / 2, b0 + 5, ys, zs, "x")
    return m


def hand():
    """Кисть: диск на качалку J4 → стенка → пластина J5 (вертикально) → мост → нижний палец."""
    xs, piv = C["xs"], C["xs"] + C["piv"]
    contact = -8.5
    lt = contact - P32["pad"] - 0.5
    half = P32["jaw_w"] / 2
    m = place(HP.horn_disk(4.0, 8.0, skip=(3,)), HP.W_COLS, (0, 0, 0))   # 3 винта: 4-е место под стенкой
    plate = place(s32_plate((-5.8, 3.2)), J5_COLS, (xs, G_S, 0))   # нижний столбец винтов закрыл бы мост пальца
    m += plate
    m += boxr(2, xs - P32["horn_D"] / 2 - 0.5, 2.6, G_S, -9.5, 8.0)   # стенка диск → пластина (мимо качалки J5)
    m += boxr(xs - 5, piv, -half, G_S, lt - 5.5, lt)                  # мост к нижнему пальцу
    m += finger_bar(piv, lt - 4, lt, contact, C["finger"], C["bend"], half)
    g = boxr(piv + 2, piv + C["finger"] - 1, -half + 0.6, half - 0.6, lt - 0.5, lt + 0.001)
    m -= HP.rot_y(g, C["bend"], piv, contact)                          # паз под накладку TPU
    for zs in (-5.8, 3.2):                                             # каналы для ключа к винтам пластины J5
        for xo in (P32["holes_y"], -P32["holes_y"]):
            m -= cyl(20, P32["m2_head"] / 2 + 0.1, xs + xo, G_S - 3 - 10, zs, "y")
    return m


def jaw():
    xs, piv = C["xs"], C["xs"] + C["piv"]
    contact = -8.5
    ub = contact + P32["pad"] + 0.5
    half = P32["jaw_w"] / 2
    m = place(HP.horn_disk(P32["jaw_w"], 7.5).translate([0, 0, HT]), J5_COLS, (xs, G_S, 0))
    m += hull(cyl(2 * half, 5.5, xs, 0, 0, "y"), boxr(piv - 2, piv, -half, half, ub, ub + 4))
    m += finger_bar(piv, ub, ub + 4, contact, C["finger"], C["bend"], half)
    for k in range(4):
        a = math.radians(90 * k)
        z, x = P32["horn_pcd"] / 2 * math.cos(a), -P32["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(10, P32["m2"] / 2, xs + x, 0, z, "y")
        m -= cyl(1.2, P32["m2_head"] / 2, xs + x, -half + 0.6 - 0.005, z, "y")
    m -= cyl(10, 2.3, xs, 0, 0, "y")
    g = boxr(piv + 2, piv + C["finger"] - 1, -half + 0.6, half - 0.6, ub, ub + 0.5)
    m -= HP.rot_y(g, C["bend"], piv, contact)
    return m


def pads():
    """Накладка TPU с насечкой под палец длиной C['finger'] (паз 0,5 мм в пальце)."""
    Lp, w = C["finger"] - 3.2, P32["jaw_w"] - 1.4
    m = boxr(0, Lp, -w / 2, w / 2, 0, P32["pad"] + 0.5)
    n = int((Lp - 1.5) // 3.2)
    for i in range(n):
        m -= boxr(1.5 + i * 3.2, 2.3 + i * 3.2, -w, w, P32["pad"] + 0.5 - 0.6, P32["pad"] + 1)
    return m


def test_stand():
    """Подставка для проверки клешни на столе: основание плеча ставится сверху на 4 × M3 во вставки."""
    bx0, bx1 = C["base_x"]; by = C["base_y"]
    h = 70.0
    zt = -H1 - HT                                                   # верх подставки = низ пластины основания
    m = boxr(bx0, bx1, -by, by, zt - h, zt) - boxr(bx0 + 4, bx1 - 4, -by + 4, by - 4, zt - h - 1, zt - 3)
    m -= boxr(X0 - 2, X1 + 2, -10.5, 10.5, zt - 5, zt + 1)           # окно под корпус J1 (с ушками)
    m += boxr(bx0 - 22, bx1 + 22, -by - 22, by + 22, zt - h, zt - h + 4)
    m -= boxr(bx0 + 4, bx1 - 4, -by + 4, by - 4, zt - h - 1, zt - h + 5)
    for hx, hy in C["base_holes"]:
        for sy in (1, -1):
            m += cyl(h - 4, 4.5, hx, sy * hy, zt - h / 2)
            m -= cyl(10, L15["insert"] / 2, hx, sy * hy, zt - 3)
    for x in (bx0 - 14, bx1 + 14):
        for sy in (1, -1):
            m -= cyl(10, 2.25, x, sy * (by + 14), zt - h + 2)          # шурупы 4 мм в доску
    m -= boxr(bx0 - 1, bx0 + 5, -8, 8, zt - h - 1, zt - h + 20)        # выход кабелей
    return m


# ---------------- сборка в позе ----------------
def link_parts():
    """Детали и корпуса приводов в системах своих звеньев (поза ноль)."""
    A1, AF = C["A1"], C["AF"]
    return {
        "base": ([base()], [place(s32_body(), J1_COLS, (0, 0, -H1 - HT))]),
        "yaw": ([yaw_bracket()], [place(s15_body(), J2_COLS, (0, 0, 0))]),
        "up": ([arm_plate(1), arm_plate(-1), elbow_sleeve()], [place(s15_body(), J3_COLS, (A1, 0, 0))]),
        "fore": ([forearm()], [place(s32_body(), J4_COLS, (AF - HT, 0, 0))]),
        "hand": ([hand()], [place(s32_body(), J5_COLS, (C["xs"], G_S, 0))]),
        "jaw": ([jaw()], []),
    }


def posed(parts, q):
    """q = (поворот, подъём, локоть, запястье, захват), градусы. Возвращает {звено: [manifold…]} в системе S."""
    q1, qp, qe, qr, qg = q
    A1, AF, xs = C["A1"], C["AF"], C["xs"]
    def T(link, m):
        if link == "base":
            return m
        if link == "jaw":
            m = rot(m, "y", -qg, (xs, 0, 0))
        if link in ("hand", "jaw"):
            m = rot(m, "x", qr).translate([AF, 0, 0])
        if link in ("fore", "hand", "jaw"):
            m = rot(m, "y", -qe).translate([A1, 0, 0])
        if link in ("up", "fore", "hand", "jaw"):
            m = rot(m, "y", -qp)
        return rot(m, "z", q1)
    return {link: [T(link, m) for m in pr + sv] for link, (pr, sv) in parts.items()}


def hits(a_list, b_list):
    v = 0.0
    for a in a_list:
        for b in b_list:
            v += (a ^ b).volume()
    return v


def sweep(parts, pairs, q0, j, values):
    ok = []
    for val in values:
        q = list(q0); q[j] = val
        P_ = posed(parts, q)
        bad = max(hits(P_[x], P_[y]) for x, y in pairs)
        ok.append((val, bad <= 0.5))
    return ok


def contiguous(ok, start):
    vals = [v for v, _ in ok]; good = dict(ok)
    i = vals.index(start)
    if not good[start]:
        return None
    lo = hi = i
    while lo > 0 and good[vals[lo - 1]]: lo -= 1
    while hi < len(vals) - 1 and good[vals[hi + 1]]: hi += 1
    return vals[lo], vals[hi]


H1 = yaw_frame()
FIXED = ("base", "yaw")
MOVING = ("up", "fore", "hand", "jaw")
ALL_PAIRS = [(a, b) for i, a in enumerate(FIXED + MOVING) for b in (FIXED + MOVING)[i + 1:]
             if not (a in FIXED and b in FIXED) and not (a == "hand" and b == "jaw")]

# рабочие точки из сценариев симуляции (телефон и ручка со стола на спину, поза «поджато»):
# смещение кончика от плеча S, мм (вперёд, вверх) — пересчитано из harvey_sim.py (S = 85; 65 мм)
TARGETS = {
    "над телефоном": (80, -65), "взять телефон": (80, -104), "поднять": (65, -15),
    "над головой": (5, 110), "над спиной": (-90, 103), "положить на спину": (-90, 23),
    "отпустить, вверх": (-65, 80), "вперёд-вверх": (25, 55), "поджато": (25, -90),
    "взять ручку": (75, -65), "поднять ручку": (55, -5), "над спиной 2": (-95, 103), "положить ручку": (-95, 17),
}
# те же движения, но промежуточные точки не вплотную к плечу (настоящий локоть не складывается на 150°)
TARGETS_ALT = {"поднять (дальше)": (100, -5), "поднять ручку (дальше)": (95, 0), "вперёд-вверх (дальше)": (60, 85)}


def tip_in_forearm():
    """Кончик пальцев (середина подушки) в системе предплечья при прямом запястье."""
    piv = C["xs"] + C["piv"]
    tx = piv + C["finger"] * math.cos(math.radians(C["bend"]))
    tz = -8.5 - C["finger"] * math.sin(math.radians(C["bend"]))
    return C["AF"] + tx, tz


def ik(dx, dz):
    """Оба решения (подъём, локоть) в градусах для кончика в (dx, dz) от S; None — не достаёт."""
    A1 = C["A1"]; vx, vz = tip_in_forearm()
    L2, dl = math.hypot(vx, vz), math.atan2(vz, vx)
    d = math.hypot(dx, dz)
    if d > A1 + L2 - 0.1 or d < abs(L2 - A1) + 0.1:
        return []
    a = math.acos((A1 ** 2 + d ** 2 - L2 ** 2) / (2 * A1 * d))
    out = []
    for s in (1, -1):
        qp = math.atan2(dz, dx) + s * a
        e = (dx - A1 * math.cos(qp), dz - A1 * math.sin(qp))
        th2 = math.atan2(e[1], e[0])
        qe = (th2 - qp - dl + math.pi) % (2 * math.pi) - math.pi
        out.append((math.degrees(qp), math.degrees(qe)))
    return out


if __name__ == "__main__":
    import trimesh
    os.chdir(HERE)
    os.makedirs("stl", exist_ok=True)
    print(f"Высота S над качалкой J1: H1 = {H1:.1f} мм")
    parts = link_parts()
    print("Детали в нулевой позе (самопроверка посадок):")
    for link, (pr, sv) in parts.items():
        for i, p in enumerate(pr):
            for s in sv:
                v = (p ^ s).volume()
                print(f"  {link}[{i}] × свой привод: {v:.1f} мм³")
    pairs_up = [(f, m) for f in FIXED for m in MOVING]
    rng = sweep(parts, pairs_up, (0, 0, 0, 0, 0), 1, list(range(-90, 181, 5)))
    print("Подъём плеча J2 без столкновений:", contiguous(rng, 0), " (в симуляции −90…170)")
    rng = sweep(parts, [("up", "fore"), ("up", "hand"), ("up", "jaw")] + pairs_up, (0, 0, 0, 0, 0), 2, list(range(-180, 181, 5)))
    print("Локоть J3 без столкновений:", contiguous(rng, 0), " (в симуляции −165…165)")
    rng = sweep(parts, [("fore", "hand"), ("fore", "jaw")], (0, 0, 0, 0, 0), 3, list(range(-180, 181, 10)))
    print("Запястье J4 без столкновений:", contiguous(rng, 0), " (в симуляции −90…90)")
    rng = sweep(parts, [("hand", "jaw")], (0, 0, 0, 0, 0), 4, list(range(0, 91, 5)))
    print("Захват J5 без столкновений:", contiguous(rng, 0), " (на стенде 0…60)")
    vx, vz = tip_in_forearm()
    print(f"Досягаемость рабочих точек симуляции (плечо {C['A1']:.0f}, кончик от локтя {math.hypot(vx, vz):.0f} мм):")
    n_ok = 0
    for name, (dx, dz) in {**TARGETS, **TARGETS_ALT}.items():
        sols = ik(dx, dz)
        good = []
        for qp, qe in sols:
            P_ = posed(parts, (0, qp, qe, 0, 0))
            v = max(hits(P_[a], P_[b]) for a, b in ALL_PAIRS)
            good.append((qp, qe, v))
        best = min(good, key=lambda g: g[2]) if good else None
        ok = best is not None and best[2] <= 0.5
        n_ok += ok
        desc = "не достаёт" if best is None else f"подъём {best[0]:6.1f}°, локоть {best[1]:7.1f}°, пересечение {best[2]:.1f} мм³"
        print(f"  {'✓' if ok else '✗'} {name:18s} ({dx:4.0f}; {dz:4.0f}): {desc}")
    print(f"  итог: {n_ok} из {len(TARGETS) + len(TARGETS_ALT)} точек без столкновений")
    # весь путь «телефон со стола на спину» — по суставам, с промежуточными шагами
    route = ["над телефоном", "взять телефон", "поднять (дальше)", "вперёд-вверх (дальше)", "над головой",
             "над спиной", "положить на спину", "отпустить, вверх", "вперёд-вверх (дальше)", "поджато"]
    allt = {**TARGETS, **TARGETS_ALT}
    def best_q(name):
        sols = ik(*allt[name])
        sc = []
        for qp, qe in sols:
            P_ = posed(parts, (0, qp, qe, 0, 0))
            sc.append((max(hits(P_[a], P_[b]) for a, b in ALL_PAIRS), qp, qe))
        return min(sc)[1:]
    qs = [best_q(n) for n in route]
    worst, where = 0.0, ""
    for (n0, a), (n1, b) in zip(zip(route, qs), zip(route[1:], qs[1:])):
        for k in range(1, 11):
            t = k / 10
            q = (0, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 0, 0)
            P_ = posed(parts, q)
            v = max(hits(P_[x], P_[y]) for x, y in ALL_PAIRS)
            if v > worst:
                worst, where = v, f"{n0} → {n1}, шаг {k}/10 (подъём {q[1]:.0f}°, локоть {q[2]:.0f}°)"
    print("Путь «телефон на спину» по суставам:", "без столкновений" if worst <= 0.5 else f"есть столкновение {worst:.1f} мм³: {where}")

    # ---------------- STL: правая клешня и зеркальная левая ----------------
    n_yaw = len(yaw_screws(yaw_bracket() + cyl(1, 1, 0, 0, -1000), -H1))   # уже просверленные — свободны
    PARTS = [  # имя файла, деталь, шт. на клешню, материал, что это
        ("01_base", base(), 1, "PETG", "основание плеча: в панцирь, держит J1"),
        ("02_yaw_bracket", yaw_bracket(), 1, "PETG", "поворотная стойка: на качалку J1, держит J2"),
        ("03_arm_plate_outer", arm_plate(-1), 1, "PETG", "пластина плеча наружная: фланец J2 → обхват J3"),
        ("04_arm_plate_inner", arm_plate(1), 1, "PETG", "пластина плеча внутренняя"),
        ("05_elbow_sleeve", elbow_sleeve(), 1, "PETG", "обхват привода локтя J3, 4 вставки M3"),
        ("06_forearm", forearm(), 1, "PETG", "предплечье: вилка на фланцах J3, держит J4"),
        ("07_hand", hand(), 1, "PETG", "кисть: на качалку J4, держит J5, нижний палец"),
        ("08_jaw", jaw(), 1, "PETG", "верхний палец на качалке J5"),
        ("09_pad_TPU", pads(), 2, "TPU 95A", "накладки на пальцы"),
    ]
    total = 0.0
    print("Детали (на одну клешню):")
    for name, m, n, mat, what in PARTS:
        tm = to_trimesh(m)
        ext = tm.bounds[1] - tm.bounds[0]
        g = tm.volume / 1000 * (1.21 if "TPU" in mat else 1.27)
        total += g * n
        print(f"  {name:20s} ×{n}  {ext[0]:5.1f} × {ext[1]:5.1f} × {ext[2]:5.1f} мм  {g:5.1f} г  цельная: {tm.is_watertight and len(m.decompose()) == 1}  — {what}")
        tm.export(f"stl/R_{name}.stl")
        to_trimesh(m.mirror([0, 1, 0])).export(f"stl/L_{name}.stl")
    st = test_stand()
    to_trimesh(st).export("stl/00_test_stand.stl")
    print(f"  00_test_stand (подставка для стола, общая) {to_trimesh(st).volume / 1000 * 1.27:5.1f} г")
    servo_g = 2 * 55 + 3 * 20.6
    print(f"Масса клешни: пластик ≈ {total:.0f} г (при 100 % заполнения; при 40 % ≈ {total * 0.6:.0f} г) + приводы {servo_g:.0f} г")
    print(f"Винты в качалку J1 сверху доступны в {n_yaw} местах из 8")
    pr = posed(parts, (0, 0, 0, 0, 0))
    scene = [to_trimesh(m) for lst in pr.values() for m in lst]
    import trimesh as _t
    _t.util.concatenate(scene).export("stl/_сборка_для_просмотра.stl")
