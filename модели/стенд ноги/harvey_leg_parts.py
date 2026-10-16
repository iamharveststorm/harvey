"""Харви, этап 1: детали стенда одной ноги для 3D-печати (STL).
Параметрическая модель: размеры привода и фланца — вверху файла. Перед печатью сверить
штангенциркулем значения с пометкой «ИЗМЕРИТЬ» и при отличии поправить и запустить заново:
    pip install manifold3d trimesh numpy
    python harvey_leg_parts.py          # STL в папку stl/
Детали держат привод не за его крепёжные отверстия, а обхватом корпуса, а к фланцам
крепятся через радиальные пазы — подходят при любом шаге отверстий фланца от 11 до 19 мм."""
import os, math
import numpy as np
from manifold3d import Manifold
import trimesh

# ---------------- параметры, мм ----------------
P = dict(
    servo_L=45.2,        # длина корпуса STS3215 (даташит 45,23)            ИЗМЕРИТЬ
    servo_W=24.7,        # ширина корпуса (даташит 24,73)                   ИЗМЕРИТЬ
    servo_H=32.0,        # толщина корпуса между плоскостями фланцев        ИЗМЕРИТЬ
    shaft_from_end=12.5, # от оси вала до ближнего торца корпуса (даташит)   ИЗМЕРИТЬ
    flange_D=20.0,       # диаметр алюминиевого фланца                      ИЗМЕРИТЬ
    flange_t=3.1,        # толщина фланца (даташит)
    gap=0.3,             # зазор посадки корпуса в обхват
    wall=3.0,            # стенки обхватов
    plate=4.0,           # толщина пластин
    m3=3.4,              # отверстие под винт M3
    insert=4.0,          # отверстие под латунную вставку M3 (вплавить паяльником)
    coxa=40.0,
    femur=51.0,          # было 45: привод колена упирался в привод бедра и в кронштейн (leg_check.py);
                         # 51 — чтобы задний торец привода колена обходил угол корпуса привода бедра (17,6 мм от оси)
    tibia=62.5, foot_r=7.5,
    case_screw=(-30.7, 10.1),   # задние винты корпуса STS3215 (8 × PA2.0, чертёж даташита): от вала x и ±z;
                                # их меняют на винты длиннее на 1,5 мм — держат привод колена в обхвате   ИЗМЕРИТЬ
    coxa_drop=58.0,      # от плоскости фланца основания до оси бедра (в спецификации 50 — см. примечание в PDF)
)
SEG = 72


def box(sx, sy, sz, x=0, y=0, z=0):
    return Manifold.cube([sx, sy, sz], center=True).translate([x, y, z])


def cyl(h, r, x=0, y=0, z=0, axis="z"):
    c = Manifold.cylinder(h, r, r, SEG, True)
    if axis == "x": c = c.rotate([0, 90, 0])
    if axis == "y": c = c.rotate([90, 0, 0])
    return c.translate([x, y, z])


def flange_cut(t, face="bottom", depth=1.3):
    """Вырез под фланец в пластине толщиной t (пластина в z ∈ [0, t]), ось — z через начало координат.
    Гнездо по диаметру фланца, центральное отверстие и 4 радиальных паза под винты M3."""
    pz = depth / 2 - 0.01 if face == "bottom" else t - depth / 2 + 0.01
    cut = cyl(depth + 0.02, P["flange_D"] / 2 + 0.3, z=pz)
    cut += cyl(t + 2, 3.6, z=t / 2)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p1 = cyl(t + 2, P["m3"] / 2, 5.5 * math.cos(a), 5.5 * math.sin(a), t / 2)
        p2 = cyl(t + 2, P["m3"] / 2, 9.5 * math.cos(a), 9.5 * math.sin(a), t / 2)
        cut += Manifold.batch_hull([p1, p2])
    return cut


def rounded_bar(x0, x1, w, t, r_end=None):
    """Пластина вдоль x от x0 до x1 шириной w, толщиной t (z ∈ [0, t]), со скруглёнными концами."""
    r0 = r_end or w / 2
    a = cyl(t, r0, x0, 0, t / 2); b = cyl(t, w / 2, x1, 0, t / 2)
    return Manifold.batch_hull([a, b])


# ---------------- детали ----------------
def lever():
    """Рычаг 100 мм для замеров момента, люфта и нагрева. Ставится на фланец привода."""
    t = 6
    m = Manifold.batch_hull([cyl(t, 15, 0, 0, t / 2), cyl(t, 6, 112, 0, t / 2)])
    m -= flange_cut(t, "bottom")
    m -= cyl(t + 2, P["m3"] / 2, 100, 0, t / 2)          # крючок весов / нить с грузом — ровно 100 мм от оси
    m -= box(10, 3.5, t + 2, 112, 0, t / 2)              # прорезь под лазерную указку (стяжкой)
    return m


def cradle(height=22):
    """Держатель привода валом вверх: прикручивается к доске, привод вставляется сверху."""
    L, W, g, w = P["servo_L"], P["servo_W"], P["gap"], P["wall"]
    sx = P["servo_L"] / 2 - P["shaft_from_end"]          # ось вала — в начале координат
    base = box(L + 2 * w + 34, W + 2 * w + 20, 4, sx, 0, 2)
    outer = box(L + 2 * g + 2 * w, W + 2 * g + 2 * w, height, sx, 0, 4 + height / 2)
    inner = box(L + 2 * g, W + 2 * g, height + 1, sx, 0, 4 + height / 2 + 0.5)
    m = base + outer - inner
    m -= cyl(10, 9, 0, 0, 2)                              # под задней опорной осью привода
    for s in (1, -1):                                     # прорези под кабель на обоих торцах
        m -= box(8, 12, 12, sx + s * (L / 2 + g + w / 2), 0, 4 + 6 + 0.01)
    for x in (sx - (L / 2 + w + 12), sx + (L / 2 + w + 12)):
        for y in ((W / 2 + w + 6), -(W / 2 + w + 6)):
            m -= cyl(10, 2.25, x, y, 2)                   # крепление к доске шурупами 4 мм
    return m


def coxa_bracket():
    """Кронштейн основания: сверху — на фланец привода основания, одна стенка вниз, снизу — обхват
    ЗАДНЕЙ половины привода бедра (вал бедра горизонтально, на coxa от оси основания и coxa_drop ниже фланца).
    Со стороны бедра ничего нет — путь привода колена свободен (раньше в него упирались внешняя стенка и
    канал до самого вала). Привод бедра вдвигается в обхват снаружи и держится задней стенкой и
    4 удлинёнными винтами корпуса. Печатать вверх ногами: плоскостью фланца на стол."""
    L, W, H, g, w, t = P["servo_L"], P["servo_W"], P["servo_H"], P["gap"], P["wall"], 5.0
    cx, cz = P["coxa"], -P["coxa_drop"]
    ys = H / 2 + P["flange_t"] - 1.3                       # стенки обхвата — заподлицо с плоскостью фланцев
    xa = cx - (L - P["shaft_from_end"]) - g - w            # задняя стенка (к оси основания)
    xb = cx - 15.0                                         # обхват кончается за 15 мм до вала бедра (диск пластины бедра — R14)
    zt = cz + W / 2 + g + w                                # верх обхвата
    top = Manifold.batch_hull([cyl(t, 15, 0, 0, t / 2), box(8, 2 * ys, t, xb - 4, 0, t / 2)])
    top -= flange_cut(t, "bottom")
    xw = 18.5                                              # стенка не ближе 18,5 мм к оси основания: угол корпуса
    web = box(xb - xw, 2 * ys, t - zt, (xw + xb) / 2, 0, (t + zt) / 2)   # привода основания — на 17,6 мм (поворот ±60°)
    outer = box(xb - xa, 2 * ys, W + 2 * g + 2 * w, (xa + xb) / 2, 0, cz)
    inner = box(xb + 1 - (xa + w), H + 2 * g, W + 2 * g, (xa + w + xb + 1) / 2, 0, cz)
    m = top + web + (outer - inner)
    m -= box(w + 2, 12, 10, xa + w / 2, 0, cz)               # выход кабеля привода бедра
    ccx, ccy = P["case_screw"]
    for s in (1, -1):                                      # удлинённые винты корпуса привода бедра
        m -= cyl(2 * ys + 2, 1.1, cx + ccx, 0, cz + s * ccy, "y")
    return m


def strap():
    """Планка-фиксатор снизу обхвата привода бедра (2 винта M3 во вставки)."""
    L, g, w = P["servo_L"], P["gap"], P["wall"]
    span = L + 2 * g + 2 * w + 8
    m = box(span + 8, 10, 4, 0, 0, 2)
    for s in (1, -1): m -= cyl(10, P["m3"] / 2, s * span / 2, 0, 2)
    return m


def femur_plate():
    """Пластина бедра (нужно 2 шт.): у оси бедра — на фланец привода бедра (основной или опорный),
    к колену — прикручивается к обхвату привода колена. Конец у колена не доходит до вала колена на 14 мм,
    чтобы не мешать вилке голени."""
    t = P["plate"]
    end = P["femur"] - 27                                  # конец пластины дальше от вилки голени — колено складывается сильнее
    m = Manifold.batch_hull([cyl(t, 14, 0, 0, t / 2), cyl(t, 9, end, 0, t / 2)])
    m -= flange_cut(t, "bottom")
    for x in (P["femur"] - 20, P["femur"] - 28):        # к обхвату привода колена
        m -= cyl(t + 2, P["m3"] / 2, x, 0, t / 2)
    cx, cy = P["case_screw"]
    for s in (1, -1):                                    # карманы под головки винтов корпуса привода колена
        m -= cyl(3.6, 2.2, P["femur"] + cx, s * cy, 0)
    return m


def knee_sleeve():
    """Обхват задней части привода колена: держит корпус, к его боковым стенкам с двух сторон
    прикручиваются пластины бедра. Начало координат — ось вала колена, корпус вдоль −x.
    Задней стенки нет (она упиралась в торец кронштейна): корпус держат 4 удлинённых винта корпуса
    сквозь боковые стенки."""
    L, W, H, g, w = P["servo_L"], P["servo_W"], P["servo_H"], P["gap"], P["wall"]
    x0, x1 = -(L - P["shaft_from_end"]) - g, -14.0         # от заднего торца до 14 мм от вала
    xc, lx = (x0 + x1) / 2, x1 - x0
    ys = H / 2 + P["flange_t"] - 1.3                       # боковые стенки — заподлицо с плоскостью фланца: пластины бедра ровные
    outer = box(lx, 2 * ys, W + 2 * g + 2 * w, xc, 0, 0)
    inner = box(lx + 2, H + 2 * g, W + 2 * g, xc, 0, 0)
    m = outer - inner
    for x in (P["femur"] - 20 - P["femur"], P["femur"] - 28 - P["femur"]):
        m -= cyl(2 * ys + 2, P["insert"] / 2, x, 0, 0, "y")
    cx, cy = P["case_screw"]
    for s in (1, -1):                                      # удлинённые винты корпуса — сквозь боковые стенки
        m -= cyl(2 * ys + 2, 1.1, cx, 0, s * cy, "y")
    return m


def tibia_fork():
    """Голень-вилка: два «уха» на фланцах привода колена (основном и опорном), мост под корпусом привода
    и стержень вниз до стопы. Печатать стоя, мостом на стол (ухи вверх) — без поддержек."""
    H, g, t = P["servo_H"], P["gap"], P["plate"]
    BR = 38.0                                              # мост — дальше угла корпуса привода (35 мм от вала): колено сгибается сильнее
    yi = H / 2 + P["flange_t"] - 1.3                       # внутренняя плоскость уха: фланец утоплен в гнездо на 1,3 мм
    m = Manifold()
    for s in (1, -1):
        ear = Manifold.batch_hull([cyl(t, 13, 0, 0, 0, "y"), box(16, t, 1, 0, 0, -BR)])
        ear = ear.translate([0, s * (yi + t / 2), 0])
        cut = flange_cut(t, "bottom").rotate([-90 if s > 0 else 90, 0, 0])
        cut = cut.translate([0, s * yi, 0])
        m += ear - cut
    bridge = box(16, 2 * (yi + t), 8, 0, 0, -BR)
    rod = Manifold.batch_hull([cyl(1, 8, 0, 0, -BR - 3), cyl(1, 6, 0, 0, -(P["tibia"] - P["foot_r"]) + 0.5)])
    m = m + bridge + rod
    m -= cyl(9, 2.0, 0, 0, -(P["tibia"] - P["foot_r"]) + 4)   # гнездо под ножку стопы
    return m


def foot():
    """Стопа: шар Ø15 со срезом 1 мм снизу (для печати) и ножкой Ø3,8 — печатать из TPU ножкой вверх, вклеить в голень."""
    r = P["foot_r"]
    s = Manifold.sphere(r, SEG) - box(3 * r, 3 * r, 2, 0, 0, -r)
    stem = cyl(8, 1.9, 0, 0, r + 3)
    return (s + stem).translate([0, 0, r - 1])


def leg_tower(stance_h=None):
    """Стойка ноги для стенда: держит привод основания валом вверх так, что нога в рабочей стойке встаёт
    на стол. Фланец привода основания — на (coxa_drop + высота осей бедра) над столом. Держит только
    заднюю часть корпуса (вдвижной обхват, 4 удлинённых винта корпуса сверху и снизу): перед приводом —
    свободный круг R18 для кронштейна ноги (поворот ±60°). Колонна и плита — позади ноги.
    Начало координат — ось привода основания в плоскости верха фланца. Печатать плитой на стол."""
    L, W, H, g, w = P["servo_L"], P["servo_W"], P["servo_H"], P["gap"], P["wall"]
    sf, ft = P["shaft_from_end"], P["flange_t"]
    if stance_h is None:
        stance_h = P["tibia"] + P["foot_r"] - P["femur"] * math.sin(math.radians(20))
    table = -P["coxa_drop"] - stance_h
    zc = -ft - H / 2                                       # центр корпуса привода основания
    ys = H / 2 + ft - 1.3                                  # стенки вдоль вала — заподлицо с плоскостью фланца
    x0, x1 = -(L - sf) - g, -14.0
    yo = W / 2 + g + w
    sleeve = box(x1 - (x0 - w), 2 * yo, 2 * ys, (x0 - w + x1) / 2, 0, zc)
    sleeve -= box(x1 + 1 - x0, W + 2 * g, H + 2 * g, (x0 + x1 + 1) / 2, 0, zc)
    sleeve -= box(7.5, 16, 2 * ys + 2, x1 - 3.0, 0, zc)        # окно под разъёмы (снизу у вала) и кабель
    cx, cy = P["case_screw"]
    for s in (1, -1):                                      # удлинённые винты корпуса — сверху и снизу
        sleeve -= cyl(2 * ys + 2, 1.1, cx, s * cy, zc)
    zb = zc - ys                                           # низ обхвата
    xc0, xc1 = -62.0, x1                                    # колонна — позади ноги
    zt, zl = zb + 1.0, table + 3.0                          # колонна заходит на 1 мм в обхват и в плиту
    col = box(xc1 - xc0, 2 * yo, zt - zl, (xc0 + xc1) / 2, 0, (zt + zl) / 2)
    plate = box(110, 90, 4, -60, 0, table + 2)
    for x in (-100, -25):
        for y in (35, -35):
            plate -= cyl(10, 2.25, x, y, table + 2)          # шурупы 4 мм в доску (или струбцина за край)
    m = sleeve + col + plate
    hz0, hz1 = table - 1, zt - 5                            # колонна полая, полость открыта вниз сквозь плиту
    m -= box(xc1 - xc0 - 8, 2 * yo - 8, hz1 - hz0, (xc0 + xc1) / 2 - 1, 0, (hz0 + hz1) / 2)
    return m


PARTS = {"lever_100mm": lever, "cradle_servo": cradle, "coxa_bracket": coxa_bracket, "leg_tower": leg_tower,
         "femur_plate_x2": femur_plate, "knee_sleeve": knee_sleeve, "tibia_fork": tibia_fork, "foot_TPU": foot}
# планка coxa_strap больше не нужна: новый кронштейн держит привод бедра винтами корпуса


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=True)


if __name__ == "__main__":
    os.makedirs("stl", exist_ok=True)
    for name, fn in PARTS.items():
        tm = to_trimesh(fn())
        tm.export(f"stl/harvey_{name}.stl")
        ext = tm.bounds[1] - tm.bounds[0]
        print(f"{name:16s} {ext[0]:6.1f} × {ext[1]:5.1f} × {ext[2]:5.1f} мм, {tm.volume / 1000 * 1.27:5.1f} г PETG (100%), водонепроницаем: {tm.is_watertight}")
