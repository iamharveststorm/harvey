"""Харви: глаз-стебелёк (2 шт., правый — зеркальный) — детали для печати (STL) и узел для проверок.
Глаза стоят на передних углах корпуса, снаружи от полос, где ходят клешни (руки переносят предметы через
голову на спину в полосе |y| = 8…52 мм). Привод STS3032 лежит вдоль корпуса, вал смотрит вперёд (+x):
глаз наклоняется вбок — «склоняет голову» (эмоции) и складывается наружу-вниз (переворот, перенос предметов).
На качалке — переходник с двумя магнитами 6 × 3 мм; к нему примагничен стебелёк (магнитная муфта: при ударе глаз
отскакивает, а не ломает привод; два конуса-фиксатора возвращают его ровно на место). Стебелёк — трубка Ø11
с каналом Ø6 под кабель, заодно с задней крышкой оправы круглого дисплея GC9A01 1,28″ (модуль Ø40 × 4 мм);
спереди — линза из поликарбоната Ø41,5 × 1,5 мм и бампер-кольцо из TPU.
Система глаза: начало — на оси привода в плоскости торца качалки, x — вперёд (по валу), z — вверх,
y — влево; глаз смотрит вперёд (+x).
    python harvey_eye_parts.py      # STL в stl/, проверка посадок в консоли"""
import os, math, importlib.util
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("harvey_claw_parts", os.path.join(HERE, "..", "клешни", "harvey_claw_parts.py"))
CP = importlib.util.module_from_spec(spec); spec.loader.exec_module(CP)
box, boxr, cyl, place, to_trimesh, hull = CP.box, CP.boxr, CP.cyl, CP.place, CP.to_trimesh, CP.hull
P32 = CP.P32

E = dict(
    stalk_up=60.0,      # от оси привода до центра дисплея — вверх
    stalk_fwd=21.0,     # … и вперёд (оправа — сразу перед муфтой)
    tube_d=11.0, chan_d=6.0,
    disp_d=40.0, disp_t=4.0,           # модуль GC9A01 (по продавцу — диск Ø40 × 4)
    lens_d=41.5, lens_t=1.5,           # линза ПК
    view_d=35.0,                       # окно (активная область дисплея Ø32,4)
    wall=2.4, back_depth=7.0,          # стенка оправы, глубина под разъём модуля и кабель
    bumper=3.0,                        # толщина бампера TPU по радиусу
    mag_d=6.0, mag_t=3.0, mag_r=6.5,   # магниты 6 × 3 мм на радиусе 6,5
    coup_t=4.0, coup_d=21.0,           # диски муфты
)
HT = P32["horn_top"]


def housing_radius():
    return E["lens_d"] / 2 + E["wall"]


def eye_center():
    return np.array([E["stalk_fwd"], 0.0, E["stalk_up"]])


def K(m):
    """Муфта строится с валом по +y (как у других узлов на STS3032) и поворачивается валом вперёд (+x)."""
    return m.rotate([0, 0, -90])


def horn_adapter():
    """Переходник на качалку STS3032 (4 × M2 на Ø10) с гнёздами двух магнитов и двумя ямками-фиксаторами.
    Диск в плоскости xz, y ∈ [0; coup_t] (качалка — с y < 0)."""
    t, R = E["coup_t"], E["coup_d"] / 2
    m = cyl(t, R, 0, t / 2, 0, "y")
    for k in range(4):
        a = math.radians(45 + 90 * k)
        x, z = P32["horn_pcd"] / 2 * math.cos(a), P32["horn_pcd"] / 2 * math.sin(a)
        m -= cyl(t + 2, P32["m2"] / 2, x, t / 2, z, "y")
        m -= cyl(1.8, P32["m2_head"] / 2, x, t - 0.9 + 0.01, z, "y")
    for a in (90, 270):                                    # магниты — сверху и снизу от оси
        x, z = E["mag_r"] * math.cos(math.radians(a)), E["mag_r"] * math.sin(math.radians(a))
        m -= cyl(E["mag_t"] + 0.2, E["mag_d"] / 2 + 0.1, x, t - (E["mag_t"] + 0.2) / 2 + 0.01, z, "y")
    for a in (0, 180):                                     # ямки-фиксаторы (конус 90°) — спереди и сзади
        x = 8.0 * math.cos(math.radians(a))
        m -= hull(cyl(0.01, 1.6, x, t + 0.01, 0, "y"), cyl(0.01, 0.01, x, t - 1.6, 0, "y"))
    m -= cyl(t + 2, 2.4, 0, t / 2, 0, "y")                 # центральный винт качалки
    return K(m)


def stalk():
    """Стебелёк с задней крышкой оправы (одна деталь): диск муфты (магниты + конусы-фиксаторы) → трубка Ø11 вверх →
    крышка оправы на 3 × M2. Кабель дисплея идёт в канале Ø6 и выходит у основания внутрь (к середине робота),
    петлёй с запасом на наклон."""
    t, R = E["coup_t"], E["coup_d"] / 2
    y0 = E["coup_t"] + 0.2                                  # диск стебелька — за диском переходника
    d = cyl(t, R, 0, y0 + t / 2, 0, "y")
    for a in (90, 270):
        x, z = E["mag_r"] * math.cos(math.radians(a)), E["mag_r"] * math.sin(math.radians(a))
        d -= cyl(E["mag_t"] + 0.2, E["mag_d"] / 2 + 0.1, x, y0 + (E["mag_t"] + 0.2) / 2 - 0.01, z, "y")
    for a in (0, 180):                                      # конусы-фиксаторы (входят в ямки переходника)
        x = 8.0 * math.cos(math.radians(a))
        d += hull(cyl(0.01, 1.5, x, y0 + 0.5, 0, "y"), cyl(0.01, 0.01, x, y0 - 1.5, 0, "y"))
    m = K(d)
    c = eye_center(); Rh = housing_radius()
    x0, x1 = housing_x()
    r, cr = E["tube_d"] / 2, E["chan_d"] / 2
    p0 = np.array([y0 + t / 2, 0.0, 0.0])
    p1 = np.array([x0 - 3.0, 0.0, c[2] - Rh + 6.5])          # к отверстию кабеля в крышке
    sph = lambda q, rr: Manifold.sphere(rr, 32).translate(list(q))
    tube = hull(sph(p0, r), sph(p1, r))
    tube -= boxr(-50, y0 + 0.01, -12, 12, -12, 12)                                  # не заходит в муфту
    tube -= cyl(x1 - x0 + 2, Rh, (x0 + x1) / 2 + 1, c[1], c[2], "x")                 # и в оправу
    tube -= cyl(12, Rh + E["bumper"] + 0.6, x1 - 4.0, c[1], c[2], "x")               # и в бампер
    m += tube + back_cover()
    m -= hull(sph(p0 + [0, 0, 7], cr), sph(p1, cr))
    m -= hull(sph(p1, cr), sph(p1 + [5, 0, 0], cr))                       # канал — в оправу
    m -= cyl(12, 2.2, p0[0], -6.0, 8.0, "y")                              # выход кабеля внутрь у основания
    return m


def housing_x():
    c = eye_center()
    L = E["lens_t"] + E["disp_t"] + E["back_depth"] + 1.6
    x1 = c[0] + E["lens_t"] + 1.6
    return x1 - L, x1


def housing():
    """Оправа дисплея: передняя губа (окно Ø35) → линза → модуль → отсек разъёма; крышка — сзади на 3 × M2."""
    c = eye_center()
    R = housing_radius()
    L = E["lens_t"] + E["disp_t"] + E["back_depth"] + 1.6       # губа 1,6
    x1 = c[0] + E["lens_t"] + 1.6                               # перед губы (дисплей — в плоскости x = c[0])
    x0 = x1 - L
    m = cyl(L, R, (x0 + x1) / 2, c[1], c[2], "x")
    m -= cyl(1.6 + 0.02, E["view_d"] / 2, x1 - 0.8, c[1], c[2], "x")                     # окно
    m -= cyl(E["lens_t"] + 0.02, E["lens_d"] / 2 + 0.15, x1 - 1.6 - E["lens_t"] / 2, c[1], c[2], "x")
    m -= cyl(E["disp_t"] + E["back_depth"] + 0.02, E["disp_d"] / 2 + 0.3, x1 - 1.6 - E["lens_t"] - (E["disp_t"] + E["back_depth"]) / 2 - 0.01, c[1], c[2], "x")
    for k in range(3):                                          # бобышки под винты крышки
        a = math.radians(90 + 120 * k)
        y, z = c[1] + (R - 1.2) * math.cos(a), c[2] + (R - 1.2) * math.sin(a)
        m += cyl(5.0, 2.6, x0 + 2.5, y, z, "x") - cyl(6.0, 0.9, x0 + 2.5, y, z, "x")      # под самонарез M2
    return m


def back_cover():
    """Задняя крышка оправы: диск на 3 × M2 + гнездо трубки стебелька снизу."""
    c = eye_center()
    R = housing_radius()
    L = E["lens_t"] + E["disp_t"] + E["back_depth"] + 1.6
    x1 = c[0] + E["lens_t"] + 1.6
    x0 = x1 - L
    m = cyl(2.0, R, x0 - 1.0, c[1], c[2], "x")
    for k in range(3):
        a = math.radians(90 + 120 * k)
        y, z = c[1] + (R - 1.2) * math.cos(a), c[2] + (R - 1.2) * math.sin(a)
        m -= cyl(4.0, 1.15, x0 - 1.0, y, z, "x")
    return m


def bumper():
    """Бампер-кольцо из TPU на переднюю часть оправы (натягивается)."""
    c = eye_center()
    R = housing_radius()
    x1 = c[0] + E["lens_t"] + 1.6
    m = cyl(9.0, R + E["bumper"], x1 - 4.5 + 1.0, c[1], c[2], "x") - cyl(12.0, R + 0.01, x1 - 4.5 + 1.0, c[1], c[2], "x")   # в печати — на 0,3 меньше (натяг TPU)
    m -= cyl(2.0, E["view_d"] / 2 + 1.0, x1 + 1.0, c[1], c[2], "x").translate([0.5, 0, 0])
    return m


def display():
    """Модуль GC9A01 + линза — для проверок и рендера."""
    c = eye_center()
    x1 = c[0] + E["lens_t"] + 1.6
    m = cyl(E["lens_t"], E["lens_d"] / 2, x1 - 1.6 - E["lens_t"] / 2, c[1], c[2], "x")
    m += cyl(E["disp_t"], E["disp_d"] / 2, x1 - 1.6 - E["lens_t"] - E["disp_t"] / 2 - 0.05, c[1], c[2], "x")
    return m


def magnets():
    t = E["coup_t"]
    m = Manifold()
    for y0 in (t - E["mag_t"] - 0.1, t + 0.2 + 0.1):
        for a in (90, 270):
            z = E["mag_r"] * math.sin(math.radians(a))
            m += cyl(E["mag_t"], E["mag_d"] / 2, 0, y0 + E["mag_t"] / 2, z, "y")
    return m


def servo_body():
    """STS3032 глаза в системе глаза: вал вперёд (+x), торец с качалкой при x = −HT, длинная часть корпуса вверх."""
    cols = [(0, 0, -1), (0, 1, 0), (1, 0, 0)]     # S: x → −z (длинная часть вверх: X0 < 0), y → y, вал → +x
    return place(CP.s32_body(), cols, (-HT, 0, 0))


def moving_parts():
    """Всё, что наклоняется вместе с глазом (для проверок)."""
    return [horn_adapter(), stalk(), housing(), bumper(), display()]


PARTS = [("01_horn_adapter", horn_adapter), ("02_stalk_with_cover", stalk), ("03_housing", housing), ("04_bumper_TPU", bumper)]

if __name__ == "__main__":
    os.chdir(HERE); os.makedirs("stl", exist_ok=True)
    mv = moving_parts(); sv = servo_body()
    names = ["переходник", "стебелёк с крышкой", "оправа", "бампер", "дисплей"]
    print("Пересечения деталей глаза между собой и с приводом (мм³):")
    for i in range(len(mv)):
        for j in range(i + 1, len(mv)):
            v = (mv[i] ^ mv[j]).volume()
            if v > 0.5:
                print(f"  {names[i]} × {names[j]}: {v:.1f}")
        v = (mv[i] ^ sv).volume()
        if v > 0.5:
            print(f"  {names[i]} × привод: {v:.1f}")
    print(f"центр дисплея от оси привода: {np.round(eye_center(), 1)} мм; наружный Ø оправы с бампером {2 * (housing_radius() + E['bumper']):.0f} мм")
    for side in ("L", "R"):
        for n, fn in PARTS:
            m = fn() if side == "L" else fn().mirror([0, 1, 0])     # правый: выход кабеля — тоже внутрь
            tm = to_trimesh(m)
            ok = tm.is_watertight and len(m.decompose()) == 1
            dens = 1.20 if "TPU" in n else 1.27
            if side == "L":
                print(f"  {n:18s} {tm.volume / 1000 * dens:5.1f} г, цельная: {ok}")
            tm.export(f"stl/{side}_{n}.stl")
