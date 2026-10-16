"""Харви, этап 1: детали стенда кисти клешни для 3D-печати (STL). Приводы — 2 × STS3032-C036.
Кисть: запястье (привод 21, вращение вокруг оси предплечья) и захват (привод 22, верхний палец
подвижный, нижний — неподвижный). Пальцы ~26 мм согнуты вниз на 30°, накладки из TPU.
Параметрическая модель: размеры привода — вверху файла, по чертежу даташита (с. 6).
Перед печатью сверить штангенциркулем значения с пометкой «ИЗМЕРИТЬ», при отличии поправить и запустить заново:
    pip install manifold3d trimesh numpy
    python harvey_hand_parts.py          # STL в папку stl/, проверка столкновений в консоли
Система координат привода (S): ось вала — z, начало — на оси вала в плоскости торца со стороны
рабочей качалки; корпус в z ∈ [−27,5; 0], по x от −17,3 до 5,7, по y ±6."""
import os, math
import numpy as np
from manifold3d import Manifold
import trimesh

# ---------------- параметры, мм ----------------
P = dict(
    body_L=23.0,          # длина корпуса поперёк вала (даташит 23)                       ИЗМЕРИТЬ
    body_T=12.0,          # толщина корпуса (даташит 12)                                  ИЗМЕРИТЬ
    body_D=27.5,          # корпус вдоль вала, между торцами (даташит 27,5)               ИЗМЕРИТЬ
    shaft_from_end=5.7,   # от оси вала до ближнего торца (по чертежу ~5,7)               ИЗМЕРИТЬ
    holes_x=(-14.8, -5.8, 3.2),  # резьбовые M2 на торце: шаг 9 мм вдоль корпуса (от оси вала) ИЗМЕРИТЬ
    holes_y=8.0,          # ряды отверстий через 16 мм                                    ИЗМЕРИТЬ
    horn_D=13.0,          # диск качалки (даташит Ø13)
    horn_pcd=10.0,        # 8 × M2 на окружности Ø10 (даташит)
    horn_top=4.8,         # от торца корпуса до плоскости качалки ((37,2 − 27,5) / 2)     ИЗМЕРИТЬ
    gap=0.3,              # зазор посадки
    m2=2.3,               # отверстие под винт M2
    m2_head=4.2,          # зенковка под головку M2 (DIN 912 — Ø3,8)
    m3=3.4, wood=4.5,     # M3; шурупы 4 мм в доску
    wrist_h=40.0,         # высота оси запястья над доской
    finger=26.0,          # длина пальца
    bend=30.0,            # пальцы согнуты вниз, °
    jaw_w=4.0,            # толщина пальца (поперёк плоскости захвата)
    pad=1.5,              # толщина накладки TPU
)
SEG = 72
X0 = -(P["body_L"] - P["shaft_from_end"])     # задний конец корпуса, x в системе привода
X1 = P["shaft_from_end"]


def box(sx, sy, sz, x=0, y=0, z=0):
    return Manifold.cube([sx, sy, sz], center=True).translate([x, y, z])


def boxr(x0, x1, y0, y1, z0, z1):
    return box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def cyl(h, r, x=0, y=0, z=0, axis="z"):
    c = Manifold.cylinder(h, r, r, SEG, True)
    if axis == "x": c = c.rotate([0, 90, 0])
    if axis == "y": c = c.rotate([90, 0, 0])
    return c.translate([x, y, z])


def place(m, cols, t):
    """Перенос из системы привода: cols — куда идут оси x, y, z привода; t — куда идёт начало."""
    R = np.array(cols, dtype=float).T
    return m.transform(np.hstack([R, np.array(t, dtype=float).reshape(3, 1)]))


def rot_y(m, deg, cx, cz):
    """Поворот вокруг оси, параллельной y, через точку (cx, cz). Плюс — нос детали вниз."""
    return m.translate([-cx, 0, -cz]).rotate([0, deg, 0]).translate([cx, 0, cz])


# ---------------- общие элементы в системе привода ----------------
def servo_body():
    """Корпус привода с обеими качалками — для проверки столкновений, не печатается."""
    b = boxr(X0, X1, -P["body_T"] / 2, P["body_T"] / 2, -P["body_D"], 0)
    for z in (P["horn_top"] / 2, -P["body_D"] - P["horn_top"] / 2):
        b += cyl(P["horn_top"], P["horn_D"] / 2, 0, 0, z)
    return b


def servo_plate(t=3.0):
    """Пластина на торец привода: 4 винта M2 в резьбу корпуса (два дальних столбца — у ближнего к валу
    места нет из-за качалки), окно под качалку. Пластина в z ∈ [0, t], головки винтов утоплены."""
    m = boxr(X0 - 2.0, X1 + 2.3, -11, 11, 0, t)
    m -= cyl(t + 2, P["horn_D"] / 2 + 0.5, 0, 0, t / 2)
    for x in P["holes_x"][:2]:
        for y in (P["holes_y"], -P["holes_y"]):
            m -= cyl(t + 2, P["m2"] / 2, x, y, t / 2)
            m -= cyl(1.6 + 0.01, P["m2_head"] / 2, x, y, t - 0.8 + 0.005)
    return m


def horn_disk(t=4.0, r=8.0, skip=()):
    """Диск на качалку: винты M2 в резьбу качалки на Ø10 (через 90°, k — номер отверстия, skip — какие
    не сверлить), по центру — доступ к винту качалки. Диск в z ∈ [0, t] (низ ложится на качалку)."""
    m = cyl(t, r, 0, 0, t / 2)
    m -= cyl(t + 2, 2.3, 0, 0, t / 2)
    for k in range(4):
        if k in skip:
            continue
        a = math.radians(90 * k)
        x, y = P["horn_pcd"] / 2 * math.cos(a), P["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(t + 2, P["m2"] / 2, x, y, t / 2)
        m -= cyl(1.2, P["m2_head"] / 2, x, y, t - 0.6 + 0.005)
    return m


# ---------------- размещение приводов ----------------
# Стойка (мир): доска z = 0, ось запястья вдоль +x на высоте wrist_h. Привод 21: вал → +x, корпус вверх.
W_COLS, W_T = [(0, 0, 1), (0, -1, 0), (1, 0, 0)], (0, 0, P["wrist_h"])
# Кисть (система кисти K): ось запястья — x, x = 0 на плоскости качалки привода 21.
# Привод 22: вал → −y, корпус назад к запястью, толщина по z. Плоскость пальцев — y ∈ [−2, 2].
G_X = 45.0
G_S = P["horn_top"] + P["jaw_w"] / 2                  # 6,8: торец привода 22 в y = +6,8, качалка в y = +2
G_COLS, G_T = [(1, 0, 0), (0, 0, 1), (0, -1, 0)], (G_X, G_S, 0)
CONTACT_Z, PIVOT_X = -8.5, 56.0                       # плоскость смыкания пальцев и место изгиба на 30°
HALF = P["jaw_w"] / 2


def finger_bar(z0, z1):
    """Палец: прямой корень до PIVOT_X и согнутая на bend часть длиной finger."""
    root = boxr(PIVOT_X - 2, PIVOT_X, -HALF, HALF, z0, z1)
    tip = rot_y(boxr(PIVOT_X, PIVOT_X + P["finger"], -HALF, HALF, z0, z1), P["bend"], PIVOT_X, CONTACT_Z)
    joint = Manifold.batch_hull([root, rot_y(boxr(PIVOT_X, PIVOT_X + 2, -HALF, HALF, z0, z1), P["bend"], PIVOT_X, CONTACT_Z)])
    m = root + tip + joint
    tip_end = rot_y(cyl(P["jaw_w"], (z1 - z0) / 2, PIVOT_X + P["finger"], 0, (z0 + z1) / 2, "y"), P["bend"], PIVOT_X, CONTACT_Z)
    return m + tip_end


def pad_groove(z_face, sign):
    """Паз под накладку TPU на рабочей грани пальца (глубина 0,5 мм)."""
    g = boxr(PIVOT_X + 2, PIVOT_X + P["finger"] - 1, -HALF + 0.6, HALF - 0.6, min(z_face, z_face + sign * 0.5), max(z_face, z_face + sign * 0.5))
    return rot_y(g, P["bend"], PIVOT_X, CONTACT_Z)


# ---------------- детали ----------------
def wrist_stand():
    """Стойка запястья: прикручивается к доске, держит привод 21 валом вперёд на высоте 40 мм.
    Печатать основанием на стол."""
    h = P["wrist_h"]
    m = place(servo_plate(3.0), W_COLS, W_T)                       # пластина в x ∈ [0, 3]
    m += boxr(0, 3, -11, 11, 0, h + X0 - 2.0 + 0.5)                 # стенка от доски до пластины
    base = boxr(-34, 22, -28, 28, 0, 4)
    for x in (-28, 16):
        for y in (22, -22):
            base -= cyl(10, P["wood"] / 2, x, y, 2)
    m += base
    for s in (1, -1):                                              # косынки за стенкой, мимо корпуса привода
        a = boxr(-26, 0, s * 14 - 1.5, s * 14 + 1.5, 4, 6)
        b = boxr(-3, 0, s * 14 - 1.5, s * 14 + 1.5, 4, h + 6)
        m += Manifold.batch_hull([a, b])
    m -= boxr(-2, 3.5, -4, 4, h + X0 - 6, h + X0 - 0.5)            # окно под кабель привода
    return m


def palm():
    """Ладонь: диск на качалку запястья (привод 21) → стенка → пластина привода захвата (22) →
    корень неподвижного нижнего пальца. Печатать стенкой (плоскость y = 6,8) на стол."""
    t = P["horn_top"]
    # 3 винта на качалку: отверстие k = 3 (y = +5) закрыла бы стенка, к нему не подлезть ключом
    disk = place(horn_disk(4.0, 8.0, skip=(3,)), W_COLS, (0, 0, 0))   # x ∈ [0, 4] — на качалке привода 21
    m = disk
    m += place(servo_plate(3.0), G_COLS, G_T)                      # пластина привода 22: y ∈ [3,8; 6,8]
    m += boxr(2, G_X + X0 - 2.0 + 0.5, 3.8, 6.8, -9.5, 9.5)         # стенка от диска до пластины
    m += boxr(2, G_X + X0, -1, 6.8, 7.3, 9.5)                       # рёбра жёсткости — мимо головок винтов (z ≤ 7,1)
    m += boxr(2, G_X + X0, -1, 6.8, -9.5, -7.3)
    lower_top = CONTACT_Z - P["pad"] - 0.5                         # верх нижнего пальца (−10,5)
    m += boxr(G_X - 5, PIVOT_X, -HALF, 6.8, lower_top - 5.5, lower_top)   # мост к нижнему пальцу
    m += boxr(G_X + 1, PIVOT_X, 3.8, 6.8, lower_top - 5.5, -7.5)   # мост врастает в пластину привода (мимо окна качалки и винтов)
    m += finger_bar(lower_top - 4, lower_top)
    m -= pad_groove(lower_top, -1)
    return m


def jaw():
    """Верхний подвижный палец: диск на качалку привода 22 и согнутый палец. Печатать плашмя."""
    m = place(horn_disk(P["jaw_w"], 7.5).translate([0, 0, P["horn_top"]]), G_COLS, G_T)   # y ∈ [−2; 2]
    upper_bot = CONTACT_Z + P["pad"] + 0.5                         # низ верхнего пальца (−6,5)
    arm = Manifold.batch_hull([cyl(P["jaw_w"], 5.5, G_X, 0, 0, "y"), boxr(PIVOT_X - 2, PIVOT_X, -HALF, HALF, upper_bot, upper_bot + 4)])
    m += arm + finger_bar(upper_bot, upper_bot + 4)
    for k in range(4):                                             # дырки диска не закрыты рукоятью
        a = math.radians(90 * k)
        x, z = G_X + P["horn_pcd"] / 2 * math.cos(a), P["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(10, P["m2"] / 2, x, 0, z, "y")
        m -= cyl(1.2, P["m2_head"] / 2, x, -HALF + 0.6 - 0.005, z, "y")   # головки — со стороны от привода
    m -= cyl(10, 2.3, G_X, 0, 0, "y")
    m -= pad_groove(upper_bot, 1)
    return m


def pad():
    """Накладка на палец из TPU 95A с насечкой (нужно 2 шт.), вклеить в паз. Печатать плашмя."""
    L, w = P["finger"] - 3.2, P["jaw_w"] - 1.4
    m = boxr(0, L, -w / 2, w / 2, 0, P["pad"] + 0.5)
    for i in range(7):
        m -= boxr(1.5 + i * 3.2, 2.3 + i * 3.2, -w, w, P["pad"] + 0.5 - 0.6, P["pad"] + 1)
    return m


def grip_lever():
    """Рычаг 25 мм на качалку STS3032 для замера силы захвата (замер 10): крючок весов — в отверстие."""
    t = 5.0
    m = horn_disk(t, 8.0) + Manifold.batch_hull([cyl(t, 6, 0, 0, t / 2), cyl(t, 4.5, 31, 0, t / 2)])
    m -= cyl(t + 2, 2.3, 0, 0, t / 2)
    for k in range(4):
        a = math.radians(90 * k)
        m -= cyl(t + 2, P["m2"] / 2, P["horn_pcd"] / 2 * math.cos(a), P["horn_pcd"] / 2 * math.sin(a), t / 2)
    m -= cyl(t + 2, P["m3"] / 2, 25, 0, t / 2)                     # ровно 25 мм от оси
    return m


def stand_cradle():
    """Держатель одиночного STS3032 валом вверх (для замеров 1 и 10 без кисти): к доске шурупами.
    Привод вставляется снизу через окно в основании, крепится 4 винтами M2 сверху, потом держатель — на доску."""
    zp = P["body_D"] + P["horn_top"] + 1.5                         # нижняя качалка не достаёт до доски
    m = servo_plate(3.0).translate([0, 0, zp])                     # пластина над корпусом
    for s in (1, -1):                                              # боковые стенки — за ушками корпуса (±9,5)
        m += boxr(X0 - 2.0, X1 + 2.3, min(s * 10, s * 12.5), max(s * 10, s * 12.5), 0, zp + 0.5)
    m += boxr(X0 - 14, X1 + 14, -16, 16, 0, 4)
    m -= boxr(X0 - 0.5, max(X1, P["horn_D"] / 2) + 1.0, -9.9, 9.9, -1, 5)   # окно под привод и нижнюю качалку
    for x in (X0 - 9, X1 + 9):
        for y in (11, -11):
            m -= cyl(10, P["wood"] / 2, x, y, 2)
    return m


PARTS = {"wrist_stand": wrist_stand, "palm": palm, "jaw": jaw, "pad_TPU_x2": pad,
         "grip_lever_25mm": grip_lever, "cradle_sts3032": stand_cradle}


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)


# ---------------- виртуальная сборка ----------------
def assembly(wrist_deg=0.0, open_deg=0.0):
    """Детали и корпуса приводов в мировой системе стойки. Возвращает (печатные, приводы)."""
    t = P["horn_top"]
    def hand(m):
        return m.rotate([wrist_deg, 0, 0]).translate([t, 0, P["wrist_h"]])
    j = jaw().translate([-G_X, 0, 0]).rotate([0, -open_deg, 0]).translate([G_X, 0, 0])
    printed = {"wrist_stand": wrist_stand(), "palm": hand(palm()), "jaw": hand(j)}
    servos = {"servo21": place(servo_body(), W_COLS, W_T), "servo22": hand(place(servo_body(), G_COLS, G_T))}
    return printed, servos


def check():
    """Пересечения деталей и приводов во всём ходе: запястье ±90°, захват 0…60°."""
    worst = 0.0
    for wd in (-90, -45, 0, 45, 90):
        for od in (0, 20, 40, 60):
            pr, sv = assembly(wd, od)
            items = list(pr.items()) + list(sv.items())
            for i in range(len(items)):
                for k in range(i + 1, len(items)):
                    (na, a), (nb, b) = items[i], items[k]
                    pair = {na, nb}
                    if pair in ({"wrist_stand", "servo21"}, {"palm", "servo22"}, {"palm", "servo21"}, {"jaw", "servo22"}):
                        continue                                    # посадка на свой привод — касание по плану
                    v = (a ^ b).volume()
                    if v > 0.5:
                        print(f"  ! пересечение {na} × {nb}: {v:.1f} мм³ (запястье {wd}°, захват {od}°)")
                        worst = max(worst, v)
    # отдельно: детали не залезают в корпуса своих приводов (кроме качалки)
    pr, sv = assembly(0, 0)
    for na, nb in (("wrist_stand", "servo21"), ("palm", "servo22"), ("palm", "servo21"), ("jaw", "servo22")):
        v = (pr[na] ^ sv[nb]).volume()
        print(f"  {na} в {nb}: {v:.1f} мм³ (норма — 0)")
        worst = max(worst, v)
    # зазор смыкания пальцев без накладок
    gap = (pr["palm"] ^ pr["jaw"]).volume()
    print(f"  пальцы сомкнуты без накладок, пересечение: {gap:.1f} мм³ (норма — 0)")
    worst = max(worst, gap)
    # доступ к винтам: над каждой головкой — свободный цилиндр диаметром гнезда головки (Ø4,2) на 15 мм
    p, j = palm(), jaw()
    hr = P["m2_head"] / 2 - 0.01
    for k, (y, z) in enumerate([(0, 5), (-5, 0), (0, -5)]):              # винты в качалку запястья, со стороны x > 0
        v = (p ^ cyl(15, hr, 2.8 + 0.01 + 7.5, y, z, "x")).volume()
        print(f"  доступ к винту качалки запястья {k + 1}: {v:.1f} мм³ (норма — 0)")
        worst = max(worst, v)
    for x in (G_X + P["holes_x"][0], G_X + P["holes_x"][1]):           # винты привода 22, со стороны пальцев (y < 3,8)
        for z in (P["holes_y"], -P["holes_y"]):
            v = ((p + j) ^ cyl(15, hr, x, 3.8 - 0.01 - 7.5, z, "y")).volume()
            print(f"  доступ к винту привода 22 (x {x:.1f}, z {z:+.0f}): {v:.1f} мм³ (норма — 0)")
            worst = max(worst, v)
    return worst


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs("stl", exist_ok=True)
    for name, fn in PARTS.items():
        tm = to_trimesh(fn())
        tm.export(f"stl/harvey_hand_{name}.stl")
        ext = tm.bounds[1] - tm.bounds[0]
        dens = 1.21 if "TPU" in name else 1.27
        print(f"{name:16s} {ext[0]:6.1f} × {ext[1]:5.1f} × {ext[2]:5.1f} мм, {tm.volume / 1000 * dens:5.1f} г (100%), водонепроницаем: {tm.is_watertight}")
    print("Проверка столкновений:")
    w = check()
    print("  итог:", "столкновений нет" if w <= 0.5 else f"есть пересечения до {w:.1f} мм³")
    pr, sv = assembly(0, 30)
    scene = trimesh.util.concatenate([to_trimesh(m) for m in list(pr.values()) + list(sv.values())])
    scene.export("stl/_сборка_для_просмотра.stl")
