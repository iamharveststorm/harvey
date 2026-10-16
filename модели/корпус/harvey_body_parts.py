"""Харви: корпус — открытая рама (вариант «технический») — детали для печати (STL) и проверка совместимости.
Все детали строятся сразу на своих местах в системе корпуса (как в harvey_layout.py: начало — на уровне осей бедра
в центре, x — вперёд, y — влево, z — вверх; мм).

Рама:
  01 днище (z −14…−10) — на нём ячейки аккумулятора, Pi, Pico, насос, контакты зарядки снизу;
  02 верхнее кольцо (z 52,7…56,7) с шестью обхватами приводов оснований ног (как на стойке стенда ноги:
     задняя половина корпуса, удлинённые винты корпуса) и стойками до днища;
  03 передняя палуба (z 17…20): основания обеих клешней (кольца под диски поворота, J1 висят снизу),
     стенки до днища и кронштейны к кольцу;
  04 узел хвоста (z 24…27): основание хвоста, стенки до днища;
  05 поднос (z 64…66) с бортиком — сюда клешни и хвост кладут телефон; на 4 стойках от кольца;
  06 держатели глаз (2 шт.) — обхват задней части привода глаза, кронштейн к подносу;
  07 кронштейн камеры (привод наклона STS3032 в «голове» за стойками клешней);
  08 кронштейны датчиков края VL53L4CD (6 шт.: 2 вперёд, 2 назад, по одному вбок), луч вниз 2,3 : 1.
Электроника — габаритными блоками для проверок и рендера (electronics()).
    python harvey_body_parts.py        # STL в stl/, массы, проверка: рама × все конечности во всех рабочих позах
"""
import os, sys, math
import numpy as np
from manifold3d import Manifold, CrossSection

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harvey_layout as L

LP, CP, TP, EP = L.LP, L.CP, L.TP, L.EP
box, boxr, cyl, hull, to_trimesh = CP.box, CP.boxr, CP.cyl, CP.hull, CP.to_trimesh
P = LP.P
DROP = L.COXA_DROP

Z_BELLY = (-14.0, -10.0)
Z_RING = (52.7, 56.7)
Z_DECK = (L.ARM_S["L"][2] - CP.H1 - CP.HT, L.ARM_S["L"][2] - CP.H1 - CP.HT + 3.0)   # плоскость торца J1 клешней (≈17,0)
Z_TRAY = (64.0, 66.0)
INSERT = 4.0       # отверстие под латунную вставку M3
M3 = 3.4


def to_leg(m, name):
    """Из системы ноги (ось привода основания, верх фланца z = 0) — в систему корпуса."""
    x, y, yaw = L.MOUNTS[name]
    return m.translate([0, 0, DROP]).rotate([0, 0, yaw]).translate([x, y, 0])


def sleeve_leg():
    """Обхват задней части привода основания (как у стойки стенда ноги) в системе ноги."""
    Ls, W, H, g, w = P["servo_L"], P["servo_W"], P["servo_H"], P["gap"], P["wall"]
    sf, ft = P["shaft_from_end"], P["flange_t"]
    zc = -ft - H / 2
    ys = H / 2 + ft - 1.3
    x0, x1 = -(Ls - sf) - g, -14.0
    yo = W / 2 + g + w
    s = box(x1 - (x0 - w), 2 * yo, 2 * ys, (x0 - w + x1) / 2, 0, zc)
    s -= box(x1 + 1 - x0, W + 2 * g, H + 2 * g, (x0 + x1 + 1) / 2, 0, zc)
    s -= box(7.5, 16, 2 * ys + 2, x1 - 3.0, 0, zc)            # окно под разъёмы и кабель
    cx, cy = P["case_screw"]
    for sg in (1, -1):
        s -= cyl(2 * ys + 2, 1.1, cx, sg * cy, zc)
    return s, (x0 - w, x1, yo, zc - ys, zc + ys)


def leg_post():
    """Стойка под обхватом (система ноги): от днища до низа обхвата, у внутреннего конца."""
    _, (xa, xb, yo, za, zb) = sleeve_leg()
    return boxr(xa, xa + 12, -yo, yo, Z_BELLY[1] - 0.5 - DROP, za + 1.0)


def sleeves_world():
    return [to_leg(sleeve_leg()[0], n) for n in L.MOUNTS]


def ring_outline():
    """Контур верхнего кольца: оболочка внутренних концов обхватов."""
    pts = []
    _, (xa, xb, yo, za, zb) = sleeve_leg()
    for n, (x, y, yaw) in L.MOUNTS.items():
        a = math.radians(yaw)
        for lx, ly in ((xa, -yo), (xa, yo), (xb, -yo), (xb, yo)):
            pts.append((x + lx * math.cos(a) - ly * math.sin(a), y + lx * math.sin(a) + ly * math.cos(a)))
    return CrossSection.hull_points(pts)


def ring():
    """02 — верхнее кольцо + 6 обхватов + 6 стоек до днища + кронштейны к передней палубе и узлу хвоста."""
    z0, z1 = Z_RING
    cs = ring_outline()
    plate = cs.extrude(z1 - z0).translate([0, 0, z0])
    inner = cs.offset(-14)
    plate -= inner.extrude(10).translate([0, 0, z0 - 1])
    m = plate
    for n in L.MOUNTS:                       # кольцо не заходит в полости обхватов — там стоят сами приводы
        m -= to_leg(box(P["servo_L"] + 1, P["servo_W"] + 2 * P["gap"], P["servo_H"] + 2 * P["gap"],
                        -(P["servo_L"] / 2 - P["shaft_from_end"]), 0, -P["flange_t"] - P["servo_H"] / 2), n)
    m -= cyl(80, 26.0, L.T_MOUNT[0], L.T_MOUNT[1], 40)          # свободный круг колонны поворота хвоста
    for n in L.MOUNTS:
        m += to_leg(sleeve_leg()[0], n) + to_leg(leg_post(), n)
        # круг свободного хода кронштейна ноги над фланцем: кольцо ниже z 58 — не мешает, но вырез под фланец
        x, y, _ = L.MOUNTS[n]
        m -= cyl(10, P["flange_D"] / 2 + 1.0, x, y, DROP - 2)
    # перемычки к передней палубе и узлу хвоста
    m += boxr(44, 52, -22, -14, Z_DECK[0], z1) + boxr(44, 52, 14, 22, Z_DECK[0], z1)
    # вставки M3 под стойки подноса
    for x, y in TRAY_POSTS:
        m -= cyl(10, INSERT / 2, x, y, z1 - 3)
    return m


TRAY_POSTS = [(-38, -26), (-38, 26), (22, -24), (22, 24)]
TRAY_X = (-52.0, 35.0)       # сзади — до колонны поворота хвоста (её радиус 23 мм вокруг оси хвоста)


def belly():
    """01 — днище: контур по стойкам, вперёд под переднюю палубу, назад под хвост."""
    z0, z1 = Z_BELLY
    pts = []
    _, (xa, xb, yo, za, zb) = sleeve_leg()
    for n, (x, y, yaw) in L.MOUNTS.items():
        a = math.radians(yaw)
        for lx, ly in ((xa, -yo), (xa, yo), (xa + 12, -yo), (xa + 12, yo)):
            pts.append((x + lx * math.cos(a) - ly * math.sin(a), y + lx * math.sin(a) + ly * math.cos(a)))
    pts += [(124, 36), (124, -36), (60, 38), (60, -38), (-102, 24), (-102, -24)]
    cs = CrossSection([pts]).hull()
    m = cs.extrude(z1 - z0).translate([0, 0, z0])
    # контакты зарядки (2 пружинных контакта в гнездо) и решётка динамика
    for y in (-15, 15):
        m -= cyl(10, 3.2, -20, y, z0)
    for i in range(-2, 3):
        m -= boxr(70, 100, i * 5 - 1, i * 5 + 1, z0 - 1, z1 + 1)
    for x in (-60, -30, 0, 30):                                   # облегчение и вентиляция
        m -= boxr(x - 8, x + 8, -8, 8, z0 - 1, z1 + 1)
    return m


def claw_base_world(side):
    """Основание клешни (пластина + опорное кольцо) из модели клешни — на месте, обрезанное по палубе."""
    b = CP.base()
    if side == "R":
        b = b.mirror([0, 1, 0])
    return b.translate(list(L.ARM_S[side]))


def deck():
    """03 — передняя палуба: основания обеих клешней одной деталью, стенки до днища, J1 висят снизу."""
    z0, z1 = Z_DECK
    pts = [(49, -36), (49, 36), (92, 36), (100, 48), (126, 48), (130, 40), (130, -40), (126, -48), (100, -48), (92, -36)]   # |y| ≤ 48: мимо передних ног
    m = CrossSection([pts[::-1]]).extrude(z1 - z0).translate([0, 0, z0])     # обход против часовой — иначе контур считается дырой
    assert not m.is_empty()
    for s in "LR":
        x, y, z = L.ARM_S[s]
        sy = 1 if s == "L" else -1
        cb = claw_base_world(s)
        m += cb ^ CrossSection([pts[::-1]]).extrude(14).translate([0, 0, z0 + 0.02])   # кольцо и пластина основания — в контуре палубы (зазор 0,02 мм до торца J1)
        m -= cyl(10, P32["horn_D"] / 2 + 0.5, x, y, z0)                    # окно под качалку J1
        for hx in P32["holes_x"][:2]:                                      # 4 × M2 в торец J1 (J1 висит снизу)
            for hy in (P32["holes_y"], -P32["holes_y"]):
                m -= cyl(10, P32["m2"] / 2, x + hx, y + hy, z0)
                m -= cyl(1.6 + 0.01, P32["m2_head"] / 2, x + hx, y + hy, z1 - 0.8 + 0.005)
    for sy in (1, -1):                                                     # стенки до днища
        m += boxr(49, 84, sy * 33 - 3, sy * 33 + 3, Z_BELLY[1] - 0.5, z1) if sy > 0 else boxr(49, 84, -36, -30, Z_BELLY[1] - 0.5, z1)   # до x 84 — дальше висят J1 клешней
    m += boxr(122, 128, -22, 22, Z_BELLY[1] - 0.5, z1)                     # передняя стенка (за ней — датчики края)
    for x in (60, 80):
        for sy in (1, -1):
            m -= cyl(20, 2.5, x, sy * 33, 5.0, "y")                         # окна под жгуты
    return m


P32 = CP.P32


def tail_mount():
    """04 — узел хвоста: основание (пластина + кольцо) из модели клешни, обрезанное по ширине, стенки до днища."""
    x, y, z = L.T_MOUNT
    b = CP.base().rotate([0, 0, 180]).translate([x, y, z])
    m = b ^ boxr(-106, -54, -24, 24, -100, 100)
    m += boxr(-104, -56, -24, -18, Z_BELLY[1] - 0.5, z - CP.H1 - CP.HT + 3)
    m += boxr(-104, -56, 18, 24, Z_BELLY[1] - 0.5, z - CP.H1 - CP.HT + 3)
    m += boxr(-104, -98, -24, 24, Z_BELLY[1] - 0.5, z - CP.H1 - CP.HT + 3)
    m -= cyl(20, 3.0, -101, 0, 8, "x")                                     # трубка насоса к хвосту
    return m


def tray():
    """05 — поднос 87 × 105 с бортиком (задний 4 мм, передний и боковые 3 мм), на 4 стойках."""
    z0, z1 = Z_TRAY
    xa, xb = TRAY_X
    m = boxr(xa, xb, -52.5, 52.5, z0, z1)
    m += boxr(xa, xa + 4, -52.5, 52.5, z1, z1 + 4) + boxr(xb - 3, xb, -52.5, 52.5, z1, z1 + 3)
    m += boxr(xa, xb, 50.5, 52.5, z1, z1 + 3) + boxr(xa, xb, -52.5, -50.5, z1, z1 + 3)
    m -= cyl(40, 27.0, L.T_MOUNT[0], L.T_MOUNT[1], z0)          # колонна поворота хвоста
    for x, y in TRAY_POSTS:
        m += cyl(Z_TRAY[0] - Z_RING[1] + 0.5, 4.0, x, y, (Z_RING[1] + Z_TRAY[0]) / 2 - 0.25)
        m -= cyl(30, M3 / 2, x, y, z0)
        m -= cyl(2.5, 3.1, x, y, z1 - 1.0)
    # накладка TPU (антискольжение) — отдельной деталью не делаем: лист силикона 1 мм на клей
    return m


def eye_mount(side):
    """06 — держатель глаза: обхват задней части привода глаза + кронштейн к подносу (над кронштейнами ног)."""
    px, py, pz = L.EYE_PIVOT[side]
    sy = 1 if side == "L" else -1
    # привод глаза: x от px−37,1 до px, y ±6,5, z pz−6,5 … pz+17,3
    xa, xb = px - 37.1 - 3.0, px - 18.0
    cl = boxr(xa, xb, -9.5, 9.5, -9.5, 20.3) - boxr(xa + 2.5, xb + 1, -6.7, 6.7, -7.0, 17.8)
    cl -= boxr(xa - 1, xa + 4, -4, 4, -4, 4)                                # выход кабеля привода
    for zz in (2.0, 12.0):                                                  # 2 винта M2 сквозь стенки — прижим корпуса
        cl -= cyl(30, 1.15, xa + 9, 0, zz, "y")
    cl = cl.translate([0, py, pz])
    yi, yo_ = sy * 40.0, py - sy * 9.0                                    # от подноса (|y| ≤ 52) до обхвата
    arm = boxr(xa, xa + 12, min(yi, sy * 52), max(yi, sy * 52), Z_TRAY[1] - 0.01, Z_TRAY[1] + 4)
    arm += boxr(xa, xa + 12, min(sy * 46, yo_), max(sy * 46, yo_), Z_TRAY[1], Z_TRAY[1] + 4)
    m = cl + arm
    for x in (xa + 6,):
        for y in (sy * 44, sy * 49):
            m -= cyl(20, M3 / 2, x, y, Z_TRAY[1])
    return m


def camera_mount():
    """07 — кронштейн камеры: привод наклона STS3032 (вал по y) на передней палубе в «голове»,
    камера Raspberry Pi Camera Module 3 Wide (25 × 24 мм) на качалке смотрит вперёд."""
    xs, zs = 60.0, 40.0
    # привод: корпус вдоль −y от торца с качалкой (y = +6), длинная часть вниз
    m = boxr(xs - 9, xs + 9, -26, 10, Z_DECK[1] - 0.01, Z_DECK[1] + 3)     # основание на палубу
    m += boxr(xs - 9, xs + 9, -26, -22, Z_DECK[1], zs + 8)                  # стенка у заднего торца привода
    m -= cyl(10, P32["horn_D"] / 2 + 1, xs, -26, zs, "y")
    for zz in (zs - 8, zs + 1):
        for xx in (xs - 8, xs + 8):
            pass
    for xx in (xs - 5, xs + 5):
        m -= cyl(10, M3 / 2, xx, 0, Z_DECK[1])
    return m


def camera_assembly(tilt=0.0):
    """Привод наклона + камера (для проверок и рендера)."""
    xs, zs = 60.0, 40.0
    servo = CP.place(CP.s32_body(), [(0, 0, 1), (1, 0, 0), (0, 1, 0)], (xs, 6.0 - 4.8, zs)) if False else \
        boxr(xs - 6, xs + 6, -22, 6, zs - 17.3, zs + 5.7)
    cam = boxr(xs + 4, xs + 16, -12.5, 12.5, zs - 12, zs + 12) + cyl(6, 4.5, xs + 18, 0, zs, "x")
    holder = boxr(xs - 2, xs + 4, 6, 12, zs - 10, zs + 10) + boxr(xs - 2, xs + 4, -12.5, 12, zs + 10, zs + 13)
    return [servo], [CP.rot(cam + holder, "y", -tilt, (xs, 0, zs))]


def edge_sensors():
    """08 — кронштейны датчиков края (плата VL53L4CD ~13 × 18 мм), луч вниз-наружу 2,3 : 1 (≈ 23,5° ниже горизонта)."""
    spots = [(127, 12, 0), (127, -12, 0), (-104, 14, 180), (-104, -14, 180), (-28, 52, 90), (-28, -52, -90)]   # боковые — между средней и задней ногой
    ms = []
    for x, y, yaw in spots:
        b = boxr(-3, 3, -9, 9, Z_BELLY[1] - 0.5, 8) + boxr(0, 3, -9, 9, 0, 14).rotate([0, 23.5, 0])
        ms.append(b.rotate([0, 0, yaw]).translate([x, y, 0]))
    return ms


def electronics():
    """Габариты электроники (для проверок и рендера), имя → manifold."""
    E = {}
    E["Pi 5 + AI HAT+ (стоит ребром)"] = boxr(-42.5, 42.5, -14, 14, -8, 48)
    E["ячейка 21700 слева"] = cyl(70, 10.6, 0, 36, 1.5, "x")
    E["ячейка 21700 справа"] = cyl(70, 10.6, 0, -36, 1.5, "x")
    E["ячейка 21700 спереди"] = cyl(70, 10.6, 84, 0, 1.5, "x")
    E["BMS 3S + плата питания"] = boxr(-40, 10, 50 - 52, 50 - 2, -9, -2) ^ boxr(-100, 100, 20, 30, -10, 10)
    E["DC-DC 5 В / 6 В"] = boxr(-30, 10, -30, -20, -9, 10)
    E["Pico 2"] = boxr(-100, -92, 8, 23, -8, 18)
    E["насос + клапан"] = boxr(-100, -88, -23, -8, -8, 20)
    E["динамик Ø28"] = cyl(6, 14, 85, 0, -6) ^ boxr(-200, 200, -200, 200, -9, 0)
    E["кнопка аварийной остановки"] = cyl(14, 8, -111, -14, 12, "x")       # на задней стенке, справа от трубки хвоста
    return E


PARTS = [("01_belly", belly), ("02_ring_frame", ring), ("03_front_deck", deck), ("04_tail_mount", tail_mount),
         ("05_tray", tray), ("06_eye_mount_L", lambda: eye_mount("L")), ("06_eye_mount_R", lambda: eye_mount("R")),
         ("07_camera_mount", camera_mount)]


def frame_parts():
    return [(n, fn()) for n, fn in PARTS] + [(f"08_edge_sensor_{i + 1}", m) for i, m in enumerate(edge_sensors())]


def fixed_hardware():
    """Неподвижные приводы, которые держит рама: 6 оснований ног, J1 клешней и хвоста, приводы глаз."""
    out = []
    for n in L.MOUNTS:
        out += L.leg(n, 0, 20, -110)["base"]
    for s in "LR":
        out += L.claw(s, (0, 0, 0, 0, 0))["base"]
        out += L.eye(s, 0)["fixed"]
    out += L.tail((0, 66, 126, 78))["base"]
    return out


def check(frame=None, verbose=True):
    """Рама и электроника × все подвижные звенья во всех рабочих позах (с правилами движения из harvey_layout)."""
    frame = frame or frame_parts()
    fm = [m for _, m in frame] + list(electronics().values()) + [m for m in camera_assembly(0)[0] + camera_assembly(0)[1]]
    names = [n for n, _ in frame] + list(electronics().keys()) + ["привод камеры", "камера"]
    bad = []
    def test(label, ms):
        for i, f in enumerate(fm):
            v = L.inter([f], ms)
            if v > 0.5:
                bad.append((names[i], label, round(v)))
    for n in L.MOUNTS:
        for qc in L.LEG_QC:
            for qf, qk in L.LEG_POSES:
                if qf > 90 and (n[1] == "F" or qc != 0):   # бедро выше 90° — только при перевороте (основание 0°), передние — не выше 90°
                    continue
                test(f"нога {n} {qc},{qf},{qk}", L.flat(L.leg(n, qc, qf, qk), skip=("base",)))
    for s in "LR":
        for yw in L.CLAW_YAW:
            for qp, qe in L.CLAW_POSES:
                if abs(yw) > 15 and qp < 80:     # правило: в низких позах поворот клешни ±15°
                    continue
                if yw < 0 and qp >= 80:          # правило: над головой и на спину — без поворота внутрь
                    continue
                test(f"клешня {s} {yw},{qp},{qe}", L.flat(L.claw(s, (yw if s == "L" else -yw, qp, qe, 0, 0)), skip=("base",)))
        for tilt in (20, 0, -20, -75):
            test(f"глаз {s} {tilt}", L.eye(s, tilt)["moving"])
    for ty, tq in [(a, b) for a in L.TAIL_YAW for b in L.TAIL_HIGH] + [(a, b) for a in L.TAIL_YAW_LOW for b in L.TAIL_LOW]:
        test(f"хвост {ty},{tq}", L.flat(L.tail((ty,) + tq), skip=("base",)))
    # рама × неподвижные приводы (посадки)
    fx = fixed_hardware()
    for i, f in enumerate(fm):
        v = L.inter([f], fx)
        if v > 0.5:
            bad.append((names[i], "неподвижные приводы", round(v)))
    if verbose:
        import collections
        c = collections.Counter((b[0], b[1].split(" ")[0] + " " + b[1].split(" ")[1] if " " in b[1] else b[1]) for b in bad)
        for k, v in c.most_common(40):
            print("  ", k, v, [b for b in bad if b[0] == k[0] and b[1].startswith(k[1])][:2])
        print("всего:", len(bad))
    return bad


if __name__ == "__main__":
    os.chdir(HERE); os.makedirs("stl", exist_ok=True)
    total = 0.0
    for n, m in frame_parts():
        tm = to_trimesh(m)
        ok = tm.is_watertight and len(m.decompose()) == 1
        g = tm.volume / 1000 * 1.27 * 0.45                     # PETG, заполнение ~40 %
        total += g
        bb = m.bounding_box()
        print(f"  {n:22s} {bb[3]-bb[0]:6.1f} × {bb[4]-bb[1]:6.1f} × {bb[5]-bb[2]:5.1f} мм  ≈{g:5.1f} г  цельная: {ok}")
        tm.export(f"stl/{n}.stl")
    print(f"рама ≈ {total:.0f} г")
    check()
