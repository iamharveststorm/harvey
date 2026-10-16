"""Харви «Компакт мини»: все детали для 3D-печати, приводы и электроника габаритами, сборка в любой позе.

Все 28 приводов — STS3032 (размеры и крепления — из модели стенда кисти, модели/стенд кисти/harvey_hand_parts.py;
перед печатью сверить штангенциркулем значения с пометкой «ИЗМЕРИТЬ» там и здесь).
    6 ног × 3 сустава: поворот (привод стоит в корпусе), бедро, колено;
    2 клешни × 4 сустава: поворот плеча (в корпусе), подъём, локоть, захват (губки смыкаются вбок);
    2 глаза: привод крена в корпусе, стебелёк с круглым дисплеем ~0,71″.
Система корпуса — как в симуляции (код/симуляция/мини/harvey_mini.py): начало — на уровне осей бедра в центре,
x — вперёд, y — влево, z — вверх; мм, углы суставов — как в симуляции (градусы).
    python harvey_mini_parts.py           # STL в stl/, масса, проверка столкновений во всех рабочих позах
    python harvey_mini_parts.py --fast    # только стойка и ходьба (быстро)

Звенья (каждое — в своей системе, как тела в симуляции):
  нога  — coxa: ось поворота, x наружу; femur: ось бедра, x к колену; tibia: ось колена, x к стопе.
          Ось бедра и колена — вдоль y звена, «+» — вверх (ось вращения −y).
  клешня — up: ось подъёма (совпадает с осью поворота плеча), x вдоль плеча; fore: ось локтя; hand: конец
          предплечья; jaw: подвижная губка (ось вдоль z кисти).
  глаз  — ось крена вдоль x, стебелёк вверх."""
import os, sys, math, json, itertools, importlib.util, functools, time
import numpy as np
from manifold3d import Manifold
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("hp", os.path.join(HERE, "..", "стенд кисти", "harvey_hand_parts.py"))
HP = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(HP)
S = HP.P                                   # размеры STS3032
box, boxr, cyl, place = HP.box, HP.boxr, HP.cyl, HP.place
SB, SD, ST = S["body_L"], S["body_D"], S["body_T"]       # 23 × 27,5 × 12
X0, X1 = HP.X0, HP.X1                                    # корпус по x в системе привода: −17,3 … 5,7
HT = S["horn_top"]                                       # 4,8 — качалка над торцом
HD = HT + 4.0                                            # диск на качалке: от торца привода до верха диска
HALF = SD / 2                                            # привод по оси вала симметрично: торцы в ±13,75

# ---------------- геометрия (мм) — общая с симуляцией ----------------
G = dict(
    cox=27.0, fem=30.0, tib=48.0, foot_r=5.0,
    a1=40.0, fore=30.0, tipx=24.0,
    mounts={"RF": (42.0, -38.0, -52.0), "RM": (0.0, -44.0, -90.0), "RB": (-42.0, -38.0, -135.0),
            "LF": (42.0, 38.0, 52.0), "LM": (0.0, 44.0, 90.0), "LB": (-42.0, 38.0, 135.0)},
    arm_s={"L": (57.0, 32.0, 38.5), "R": (57.0, -32.0, 38.5)},   # ось подъёма над крышкой: кронштейн плеча крутится над ней
    eye={"L": (12.0, 30.0, 31.0), "R": (12.0, -30.0, 31.0)},     # приводы глаз лежат на крышке
    body=(-50.0, 64.0, -44.0, 44.0, -15.0, 24.0),         # корпус: x, y, z (от осей бедра); крышка 20…24
    disp_d=24.0, disp_t=4.5, stalk=26.0,                  # дисплей 0,71″ круглый: модуль Ø24 × 4,5 мм   ИЗМЕРИТЬ
    wall=2.0, plate=3.0,
)
PLA = 1.24e-3        # г/мм³
INFILL = 0.45        # доля сплошного материала при печати (стенки 3 периметра + 25 % заполнения ≈ 0,45 для тонких деталей)
TPU = 1.21e-3


# ---------------- приводы ----------------
@functools.lru_cache(None)
def servo_sym():
    """STS3032 в системе привода, сдвинутой так, что торцы в z = ±13,75 (вал — z, рабочая качалка на +z).
    Обе качалки: рабочая на +z, вторая (опора) на −z."""
    return HP.servo_body().translate([0, 0, HALF])


def servo_at(cols, t):
    return place(servo_sym(), cols, t)


# привод с валом вдоль +y звена, корпус к −x (назад к предыдущему суставу), толщина по z
COLS_YB = [(1, 0, 0), (0, 0, -1), (0, 1, 0)]          # x_s → +x, y_s → −z, z_s → +y : корпус x ∈ [−17,3; 5,7]
COLS_YF = [(-1, 0, 0), (0, 0, 1), (0, 1, 0)]          # корпус к +x: x ∈ [−5,7; 17,3]
COLS_ZD = [(1, 0, 0), (0, -1, 0), (0, 0, -1)]         # вал вниз (−z), корпус x ∈ [−17,3; 5,7]
COLS_ZU = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]           # вал вверх


def plate_on_face(cols, t, side=+1, th=None, ext=(0, 0, 0, 0)):
    """Пластина на торец привода (рабочий side=+1 или опорный −1) с окном под качалку; ext — расширить
    (x−, x+, y−, y+) в системе привода."""
    th = th or G["plate"]
    m = boxr(X0 - 2.0 - ext[0], X1 + 2.3 + ext[1], -11 - ext[2], 11 + ext[3], 0, th)
    m -= cyl(th + 2, S["horn_D"] / 2 + 0.6, 0, 0, th / 2)
    for x in S["holes_x"][:2]:
        for y in (S["holes_y"], -S["holes_y"]):
            m -= cyl(th + 2, S["m2"] / 2, x, y, th / 2)
    if side > 0:
        m = m.translate([0, 0, HALF])
    else:
        m = m.mirror([0, 0, 1]).translate([0, 0, -HALF])
    return place(m, cols, t)


def disk_on_horn(cols, t, side=+1, r=8.0, th=4.0):
    """Диск на качалку (рабочую side=+1 или опорную −1) — к нему крепится следующее звено."""
    d = HP.horn_disk(th, r)
    if side > 0:
        d = d.translate([0, 0, HALF + HT + 0.2])
    else:
        d = d.mirror([0, 0, 1]).translate([0, 0, -HALF - HT - 0.2])
    return place(d, cols, t)


def hull(*ms):
    return Manifold.batch_hull(list(ms))


def rod(p0, p1, r):
    """Стержень от точки к точке (цилиндр с шарами на концах, через выпуклую оболочку)."""
    a = Manifold.sphere(r, 24).translate(list(p0)); b = Manifold.sphere(r, 24).translate(list(p1))
    return hull(a, b)


# ---------------- нога ----------------
# coxa: привод бедра в кронштейне, вал +y, корпус назад к оси поворота; ось бедра в (cox, 0, 0).
# Привод поворота стоит в корпусе валом вниз; кронштейн висит на его качалке под корпусом и поднимается к приводу бедра.
COXA_FACE = -HALF                 # торец привода поворота (рабочий, вал вниз) — на z = −13,75 в системе ноги


@functools.lru_cache(None)
def coxa_servo_leg():
    """Привод поворота ноги в системе ноги (стоит в корпусе): вал вниз, ось — z, корпус к оси корпуса (−x)."""
    return servo_at(COLS_ZD, (0, 0, 0))


@functools.lru_cache(None)
def coxa_bracket():
    """Кронштейн основания: диск на качалке привода поворота (снизу корпуса), полка наружу и стенка на опорном
    торце привода бедра. Печать — полкой на стол."""
    c = G["cox"]
    d = disk_on_horn(COLS_ZD, (0, 0, 0), +1, r=8.0)                       # под корпусом: z ∈ [−22,7; −18,7]
    z0 = -HALF - HT - 0.2 - 4.0; z1 = z0 + 4.0
    shelf = boxr(-6, c + 8.0, -8, 8, z0, z1)
    wall = plate_on_face(COLS_YB, (c, 0, 0), -1, ext=(0, 0, 3.0, 2.0))     # стенка на опорном торце (y = −13,75)
    web = boxr(c - 19.3, c + 8.0, -HALF - G["plate"], -HALF, z0, -6.0)     # стенка от полки до пластины
    gus = hull(boxr(c - 19.3, c - 15, -HALF - G["plate"], -8, z0, z1), boxr(c - 19.3, c - 15, -9, -8, z0, z1 + 0.1))
    m = d + shelf + wall + web + gus
    return m - cyl(30, 2.4, 0, 0, z0)                                       # доступ к винту качалки


@functools.lru_cache(None)
def femur_servo_coxa():
    return servo_at(COLS_YB, (G["cox"], 0, 0))


@functools.lru_cache(None)
def femur_link():
    """Бедро (в системе бедра: ось бедра в начале, колено в (fem, 0, 0)): диск на качалке привода бедра (+y),
    пластина к колену и пластина на опорном торце привода колена (вал колена −y, тибия — с −y).
    Печать — плашмя, диском на стол."""
    f = G["fem"]; t = HALF + HT + 0.2
    disk = disk_on_horn(COLS_YB, (0, 0, 0), +1, r=8.0)                     # y ∈ [18,7; 22,7]
    bar = boxr(0, f, t, t + 4.0, -5.5, 5.5)
    # привод колена: вал −y (рабочая качалка с −y), корпус назад к оси бедра; опорный торец в y = +13,75
    knee_plate = plate_on_face(COLS_KNEE, (f, 0, 0), -1)                   # y ∈ [13,75; 16,75]
    bridge = boxr(f - 19.3, f + 8.0, HALF + G["plate"] - 0.01, t + 4.0, -11, 11) - cyl(20, 7.2, f, HALF + 2.4, 0, "y")
    m = disk + bar + knee_plate + bridge
    return m - cyl(40, 2.4, 0, t + 2, 0, "y")


COLS_KNEE = [(1, 0, 0), (0, 0, 1), (0, -1, 0)]       # вал −y, корпус x ∈ [−17,3; 5,7]


@functools.lru_cache(None)
def knee_servo_femur():
    return servo_at(COLS_KNEE, (G["fem"], 0, 0))


@functools.lru_cache(None)
def tibia():
    """Голень (в системе голени: ось колена в начале, стопа в (tib − r, 0, 0)): диск на рабочей качалке колена (−y),
    рычаг, уходящий от привода на 20 мм, излом к плоскости ноги, стержень до стопы. Печать — диском на стол."""
    tb, r = G["tib"], G["foot_r"]; t = HALF + HT + 0.2
    disk = disk_on_horn(COLS_KNEE, (0, 0, 0), +1, r=8.0)                   # y ∈ [−22,7; −18,7]
    arm = hull(boxr(0, 2, -t - 4.0, -t, -5, 5), boxr(19, 21, -t - 4.0, -t, -4, 4))
    dog = hull(boxr(19, 21, -t - 4.0, -t, -4, 4), cyl(4, 3.6, 31, -3.0, 0, "x"))
    shaft = hull(cyl(2, 3.6, 31, -3.0, 0, "x"), cyl(2, 3.0, tb - r - 2.5, 0, 0, "x"))
    m = disk + arm + dog + shaft
    return m - cyl(40, 2.4, 0, -t - 2, 0, "y")


@functools.lru_cache(None)
def foot():
    """Стопа TPU: колпачок на конец голени."""
    tb, r = G["tib"], G["foot_r"]
    return Manifold.sphere(r, 32).translate([tb - r, 0, 0]) + cyl(5, 3.6, tb - r - 4.5, 0, 0, "x") - cyl(5, 3.1, tb - r - 5.5, 0, 0, "x")


# ---------------- клешня ----------------
# Ось поворота плеча — z (привод в корпусе, вал вверх), ось подъёма — y звена, обе через точку arm_s.
YAW_FACE_Z = -(6.0 + 1.0 + 4.0 + HT + 0.2)       # рабочий торец привода поворота плеча под осью подъёма: −16


COLS_YAW = [(0, 1, 0), (-1, 0, 0), (0, 0, 1)]       # вал вверх, корпус к средней линии (для левой клешни −y)


@functools.lru_cache(None)
def yaw_servo_arm():
    """Привод поворота плеча (для левой клешни): вал вверх, корпус уходит к средней линии корпуса."""
    return servo_at(COLS_YAW, (0, 0, YAW_FACE_Z - HALF))


@functools.lru_cache(None)
def yaw_bracket():
    """Кронштейн плеча: диск на качалке привода поворота, стенка на опорном торце привода подъёма."""
    d = disk_on_horn(COLS_ZU, (0, 0, YAW_FACE_Z - HALF), +1, r=8.0)        # z ∈ [−11; −7]
    z0 = YAW_FACE_Z + HT + 0.2; z1 = z0 + 4.0
    wall = plate_on_face(COLS_YB, (0, 0, 0), -1, ext=(0, 0, 3.0, 2.0))
    web = boxr(-19.3, 8.0, -HALF - G["plate"], -HALF, z0, -6.0)
    shelf = boxr(-8, 8, -HALF - G["plate"], 8, z0, z1)
    return d + wall + web + shelf - cyl(30, 2.4, 0, 0, z0)


@functools.lru_cache(None)
def lift_servo_arm():
    return servo_at(COLS_YB, (0, 0, 0))


@functools.lru_cache(None)
def upper_arm():
    """Плечо (в системе up): как бедро — диск на качалке подъёма (+y), пластина к локтю, привод локтя валом −y."""
    a = G["a1"]; t = HALF + HT + 0.2
    disk = disk_on_horn(COLS_YB, (0, 0, 0), +1, r=8.0)
    bar = boxr(0, a, t, t + 4.0, -5.0, 5.0)
    plate = plate_on_face(COLS_KNEE, (a, 0, 0), -1)
    bridge = boxr(a - 19.3, a + 8.0, HALF + G["plate"] - 0.01, t + 4.0, -11, 11) - cyl(20, 7.2, a, HALF + 2.4, 0, "y")
    return disk + bar + plate + bridge - cyl(40, 2.4, 0, t + 2, 0, "y")


@functools.lru_cache(None)
def elbow_servo_up():
    return servo_at(COLS_KNEE, (G["a1"], 0, 0))


# Захват: привод валом вниз (−z кисти) над губками, ось губки в (GX, GY, 0); неподвижная губка — на корпусе привода.
GX, GY = 6.0, -4.0                      # ось подвижной губки в системе кисти (для левой; правая — зеркальная)
GRIP_Z = 9.0                            # рабочий торец привода захвата над плоскостью губок


@functools.lru_cache(None)
def grip_servo_hand():
    return servo_at(COLS_ZD, (GX, GY, GRIP_Z + HALF))


@functools.lru_cache(None)
def forearm():
    """Предплечье (в системе fore): диск на качалке локтя (−y), излом к плоскости руки, пластина на опорном
    (верхнем) торце привода захвата."""
    f = G["fore"]; t = HALF + HT + 0.2
    disk = disk_on_horn(COLS_KNEE, (0, 0, 0), +1, r=8.0)                   # y ∈ [−22,7; −18,7]
    arm = hull(boxr(0, 2, -t - 4.0, -t, -5, 5), boxr(9, 11, -t - 4.0, -t, -5, 5))
    top = GRIP_Z + SD + 0.2                                                 # верх привода захвата в системе кисти
    hold = plate_on_face(COLS_ZD, (f + GX, GY, GRIP_Z + HALF), -1)          # пластина на верхнем торце
    up = hull(boxr(9, 11, -t - 4.0, -t, -5, 5), boxr(f + GX - 19.3, f + GX - 15.3, -t - 4.0, GY - 11, top, top + G["plate"]))
    return disk + arm + hold + up - cyl(40, 2.4, 0, -t - 2, 0, "y")


@functools.lru_cache(None)
def fixed_jaw(s=1):
    """Неподвижная губка — на корпусе привода захвата снизу (в системе кисти; s = +1 левая, −1 правая)."""
    j = boxr(GX - 4, GX + 26, 4.5, 7.5, -4.0, 4.0) + boxr(GX - 4, GX + 2, GY, 7.5, -4.0, GRIP_Z - 0.3)
    j = j + boxr(GX - 10, GX + 2, GY - 6, 7.5, GRIP_Z - 3.3, GRIP_Z - 0.3) - cyl(20, 7.0, GX, GY, GRIP_Z)
    return j if s > 0 else j.mirror([0, 1, 0])


@functools.lru_cache(None)
def moving_jaw(s=1):
    """Подвижная губка (в системе губки: ось — z через начало): диск на качалке захвата, губка вперёд."""
    d = HP.horn_disk(3.0, 7.5).mirror([0, 0, 1]).translate([0, 0, GRIP_Z - HT - 0.2])   # z ∈ [1,0; 4,0]
    j = boxr(-3, 27, -1.5 + 0, 1.5, -4.0, 4.0).translate([0, -2.5, 0])
    m = d + hull(cyl(3.0, 7.0, 0, 0, GRIP_Z - HT - 1.7), boxr(-2, 2, -4.0, -1.0, -4.0, 4.0)) + j
    return m if s > 0 else m.mirror([0, 1, 0])


def pads(s=1):
    """Накладки TPU на губки (вставляются в паз)."""
    a = boxr(GX + 8, GX + 25, 3.5, 4.5, -3.5, 3.5)
    b = boxr(8, 25, -1.5, -0.5, -3.5, 3.5).translate([GX, GY, 0])
    return (a if s > 0 else a.mirror([0, 1, 0])), (b if s > 0 else b.mirror([0, 1, 0]))


# ---------------- глаз ----------------
def eye_servo_body(s=1):
    """Привод крена глаза в системе глаза: вал +x (рабочая качалка спереди), корпус к оси корпуса (−y для левого)."""
    cols = [(0, 1, 0), (0, 0, 1), (1, 0, 0)]                 # x_s → +y: корпус к средней линии (−y), y_s → z, вал +x
    return servo_at(cols, (-HALF - HT - 0.2 - 4.0, 0, 0)), cols


@functools.lru_cache(None)
def eye_stalk(s=1):
    """Стебелёк: диск на качалке, стойка вверх, держатель дисплея (кольцо с пазом), дисплей смотрит вперёд."""
    _, cols = eye_servo_body(s)
    t0 = (-HALF - HT - 0.2 - 4.0, 0, 0)
    d = disk_on_horn(cols, t0, +1, r=7.0, th=3.0)                           # x ∈ [−4; −1]
    h = G["stalk"]; R = G["disp_d"] / 2
    post = hull(boxr(-4, -1, -4, 4, -4, 4), boxr(-4, -1, -3, 3, h - 2, h))
    ring = cyl(G["disp_t"] + 2.0, R + 1.6, -4 + (G["disp_t"] + 2.0) / 2, 0, h + R, "x") - cyl(G["disp_t"] + 0.2, R + 0.15, -4 + 1 + (G["disp_t"] + 0.2) / 2, 0, h + R, "x")
    ring -= cyl(3, R - 2.0, -4 + G["disp_t"] + 1.5, 0, h + R, "x")         # окно экрана спереди
    return d + post + ring


@functools.lru_cache(None)
def display(s=1):
    h = G["stalk"]; R = G["disp_d"] / 2
    return cyl(G["disp_t"], R, -4 + 1 + G["disp_t"] / 2, 0, h + R, "x")


# ---------------- корпус ----------------
def _leg_tf(n, m):
    x, y, yaw = G["mounts"][n]
    return m.rotate([0, 0, yaw]).translate([x, y, 0])


def coxa_servos():
    return {n: _leg_tf(n, coxa_servo_leg()) for n in G["mounts"]}


def yaw_servos():
    return {"L": yaw_servo_arm().translate(list(G["arm_s"]["L"])), "R": yaw_servo_arm().mirror([0, 1, 0]).translate(list(G["arm_s"]["R"]))}


def eye_servos():
    b, _ = eye_servo_body(1)
    return {"L": b.translate(list(G["eye"]["L"])), "R": b.mirror([0, 1, 0]).translate(list(G["eye"]["R"]))}


CAMERA_BOX = boxr(52.5, 61.5, -12.4, 12.4, -3.0, 20.0) + cyl(4.5, 4.5, 63.7, 0, 8.5, "x")   # плата 25 × 24 + объектив в окне стенки


@functools.lru_cache(None)
def electronics():
    """Габариты электроники (мм, в системе корпуса): между гнёздами приводов, в три этажа."""
    e = {}
    e["батарея 2S 18650"] = cyl(65, 9.3, 0, -9.4, -3.5, "x") + cyl(65, 9.3, 0, 9.4, -3.5, "x")      # 2 банки рядом, вдоль x
    e["Pi Zero 2 W"] = boxr(-32.5, 32.5, -15, 15, 6.5, 8.0) + boxr(-26, 26, -12, -7, 8.0, 14.0)       # плата + гребёнка
    e["RP2350-Zero"] = boxr(-20, 3.5, -9, 9, 15.0, 19.0)                                              # над Pi Zero
    e["DC-DC 6 В ≥ 6 А"] = boxr(33, 50.5, -11.5, 11.5, -12.5, -3.5)        # модуль ~17 × 23 × 9 мм между гнёздами плеч
    e["DC-DC 5 В 3 А"] = boxr(34, 47, -7.5, 7.5, -2.5, 3.5)
    e["BMS 2S + заряд"] = boxr(-47.5, -34, -16, 16, -12.5, -8.0)
    e["микрофоны + усилитель"] = boxr(-47.5, -34, -16, 2, -7, -3.0)
    e["IMU + INA226"] = boxr(-47.5, -38, 4, 16, -7, -3.0)
    e["камера Module 3"] = CAMERA_BOX
    e["динамик Ø20"] = cyl(5.0, 10.0, -32, 0, 17.0)
    return e


def edge_sensors():
    """6 датчиков VL53L4CD (модуль 13 × 18 × 4) снаружи стенок у дна: 2 вперёд, 2 назад, по 1 в стороны."""
    x0, x1, y0, y1, z0, z1 = G["body"]
    zc = z0 + 6.5
    out = [boxr(x1, x1 + 4, y - 6.5, y + 6.5, zc - 6, zc + 6) for y in (9.0, -9.0)]
    out += [boxr(x0 - 4, x0, y - 6.5, y + 6.5, zc - 6, zc + 6) for y in (9.0, -9.0)]
    out += [boxr(-27, -14, y1, y1 + 4, zc - 6, zc + 6), boxr(-27, -14, y0 - 4, y0, zc - 6, zc + 6)]
    return out


BELLY_Y = (16.0, -16.0)          # середины контактных пластин на дне
LID_SCREWS = ((-46.0, 0.0), (-20.0, 40.5), (-20.0, -40.5), (49.0, 0.0))   # винты крышки M2 во вставки ванны — там, где нет приводов
DOCK_H = 4.0                     # высота площадки станции
POGO_TOP = 11.0                  # верх подпружиненных контактов в свободном состоянии (ход 1,5 мм)
REST_DROP = 13.0                 # на станции Харви опускает корпус на 13 мм: кронштейны ног ещё в 2 мм над столом


@functools.lru_cache(None)
def dock_pad():
    """Станция-«гнездо», площадка 64 × 56 × 4 мм со скосами — помещается между кронштейнами ног, стопы на столе.
    Два гнезда под подпружиненные контакты (pogo Ø5, ход 1,5 мм) против пластин на брюхе. Печать — низом на стол."""
    top = boxr(-29, 29, -25, 25, DOCK_H - 0.01, DOCK_H); bot = boxr(-32, 32, -28, 28, 0, 0.01)
    m = Manifold.batch_hull([top, bot])
    for y in BELLY_Y:
        m -= cyl(DOCK_H + 2, 2.6, 0, y, DOCK_H / 2 + 0.5)                     # гнездо контакта
        m -= boxr(0, 33, y - 1.5, y + 1.5, -0.1, 1.6)                           # канал провода к башенке
    return m


def dock_pogo():
    return [cyl(POGO_TOP - 0.5, 2.5, 0, y, 0.5 + (POGO_TOP - 0.5) / 2) for y in BELLY_Y]


@functools.lru_cache(None)
def dock_tower():
    """Башенка станции позади площадки: метка AprilTag 30 × 30 мм (её ищет камера), ИК-светодиод маяка
    (его видит приёмник без ПК), разъём питания сзади. Харви заходит лицом к башенке: метка — на уровне камеры."""
    x0 = 140.0                                   # впереди: поджатые клешни (привод захвата торчит вперёд до 131 мм) не достают
    body = boxr(x0, x0 + 8, -30, 30, 0, 52) + boxr(x0 - 2, x0 + 20, -32, 32, 0, 3) + boxr(32, x0, -8, 8, 0, 2.0)   # перемычка с проводами
    body -= boxr(x0 - 0.5, x0 + 1.0, -16, 16, 14, 46)                           # окно метки
    body -= cyl(12, 2.6, x0 + 4, 0, 49, "x")                                     # ИК-светодиод
    body -= cyl(12, 4.0, x0 + 4, 0, 6, "x").translate([8, 0, 0])                 # разъём питания сзади
    return body


@functools.lru_cache(None)
def leg_stand():
    """Стенд одной ноги для первых тестов: гнездо привода поворота (как в корпусе) на высоте стойки,
    основание позади — нога свободно ходит вперёд ±30° и упирается стопой в стол. Крепится к столу 2 струбцинами
    или 2 шурупами. Печать — основанием на стол, поддержки под гнездо."""
    zj = G["tib"] - G["fem"] * math.sin(math.radians(20))
    sock = boxr(X0 - 2.2, 0.0, -ST / 2 - 2.2, ST / 2 + 2.2, -HALF - 1.0, HALF + 0.5)   # спереди открыто — как стенка корпуса по оси
    m = place(sock, COLS_ZD, (0, 0, zj))
    for y in (S["holes_y"], -S["holes_y"]):           # винты M2 снизу в рабочий торец привода (через дно гнезда)
        for x in S["holes_x"][:2]:
            m -= cyl(6, S["m2"] / 2, x, y, zj - HALF - 0.5)
    m += boxr(X0 - 2.2, -12.0, -ST / 2 - 2.2, ST / 2 + 2.2, 0, zj)            # колонна под гнездом (позади оси)
    m += boxr(-70, -12.0, -35, 35, 0, 4)                                        # основание
    m += Manifold.batch_hull([boxr(-30, -12.0, -3, 3, 4, 4.01), boxr(X0 - 2.2, -12.0, -3, 3, zj - 10, zj - 9.99)])   # косынка
    m -= servo_at(COLS_ZD, (0, 0, zj))
    for x, y in ((-60, 25), (-60, -25)):
        m -= cyl(10, 2.3, x, y, 2)                                              # шурупы в доску
    return m


@functools.lru_cache(None)
def chassis():
    """Корпус-ванна: дно, стенки, гнёзда шести приводов ног, двух плеч и двух глаз, стойки под платы,
    контакты зарядки снизу. Печать — дном на стол. Сверху — крышка (lid)."""
    x0, x1, y0, y1, z0, z1 = G["body"]; w = G["wall"]
    outer = boxr(x0, x1, y0, y1, z0, z1 - 4.0)
    m = outer - boxr(x0 + w, x1 - w, y0 + w, y1 - w, z0 + w, z1)
    # гнёзда приводов: обхват корпуса привода со стенкой 2,2 мм, сам привод — вырез
    sock = boxr(X0 - 2.2, X1 + 2.2, -ST / 2 - 2.2, ST / 2 + 2.2, -HALF - 1.0, HALF + 0.5)
    for n in G["mounts"]:
        m += _leg_tf(n, place(sock, COLS_ZD, (0, 0, 0)))
    for sd, sg in (("L", 1), ("R", -1)):
        y_ = place(sock, COLS_YAW, (0, 0, YAW_FACE_Z - HALF))
        m += (y_ if sg > 0 else y_.mirror([0, 1, 0])).translate(list(G["arm_s"][sd]))
    m = m ^ boxr(x0, x1, y0, y1, z0, z1 - 4.0)              # гнёзда не выходят за габарит ванны
    for sv in list(coxa_servos().values()) + list(yaw_servos().values()):
        m -= sv                                                      # гнездо точно по приводу (зазор — в допуске печати)
    for n in G["mounts"]:          # проход под качалки и кронштейны ног снизу
        m -= _leg_tf(n, cyl(20, 9.0, 0, 0, z0 - 1.0))
        for y in (S["holes_y"], -S["holes_y"]):        # 4 винта M2 снизу в рабочий торец привода поворота
            for x in S["holes_x"][:2]:
                m -= _leg_tf(n, cyl(6, S["m2"] / 2, x, y, -HALF - 0.5))
    m -= cyl(6, 5.0, x1 - 1.0, 0, 8.5, "x")          # окно объектива камеры
    for x, y in LID_SCREWS:                           # стойки Ø6 с отверстием под латунную вставку M2 × 3 (Ø3,2)
        cx = min(max(x, x0 + 3.0), x1 - 3.0); cy = min(max(y, y0 + 3.0), y1 - 3.0)
        top = z1 - 4.0; bottom = top - 8.0
        m += cyl(top - bottom, 3.0, cx, cy, (top + bottom) / 2) - cyl(5, 1.6, cx, cy, top - 2.0)
    # контакты зарядки: две латунные пластины 40 × 12 мм на дне (в пазах 0,8 мм), «+» слева, «−» справа
    for y in BELLY_Y:
        m -= boxr(-20, 20, y - 6, y + 6, z0 - 1, z0 + 0.8)
    return m


@functools.lru_cache(None)
def lid():
    """Крышка 4 мм на винтах M2 в стойки ванны: отверстия под качалки плеч, решётка динамика, площадки под
    приводы глаз. Печать — верхом на стол."""
    x0, x1, y0, y1, z0, z1 = G["body"]
    m = boxr(x0, x1, y0, y1, z1 - 4.0, z1)
    for sd in "LR":
        x, y, z = G["arm_s"][sd]
        m -= cyl(30, 7.8, x, y, z1)                  # качалка привода плеча выходит над крышкой
    for sv in yaw_servos().values():                  # верх привода плеча проходит сквозь крышку
        m -= sv
    for i in range(-2, 3):
        for j in range(-2, 3):
            m -= cyl(10, 0.9, -32 + 3.2 * i, 3.2 * j, z1)
    for sd in "LR":                                   # площадки под приводы глаз (привод лежит на крышке)
        b = eye_servos()[sd].bounding_box()
        m += boxr(b[0] + 1.5, b[3] - 1.5, b[1] + 1.0, b[4] - 1.0, z1 - 0.01, b[2] + 0.01) if b[2] > z1 else Manifold()
    for x, y in LID_SCREWS:
        m -= cyl(10, 1.15, x, y, z1)
    return m


# ---------------- сборка в позе ----------------
def leg_assembly(n, qc, qf, qk):
    """{звено: [(имя, деталь)]} в системе корпуса. Углы в градусах."""
    x, y, yaw = G["mounts"][n]
    def T_leg(m): return m.rotate([0, 0, yaw + qc]).translate([x, y, 0])
    def T_fem(m): return T_leg(m.rotate([0, -qf, 0]).translate([G["cox"], 0, 0]))
    def T_tib(m): return T_fem(m.rotate([0, -qk, 0]).translate([G["fem"], 0, 0]))
    return {"coxa": [("coxa_bracket", T_leg(coxa_bracket())), ("femur_servo", T_leg(femur_servo_coxa()))],
            "femur": [("femur_link", T_fem(femur_link())), ("knee_servo", T_fem(knee_servo_femur()))],
            "tibia": [("tibia", T_tib(tibia())), ("foot", T_tib(foot()))]}


def claw_assembly(s, qy, qp, qe, qg):
    """Клешня в системе корпуса. Правая — зеркало левой (углы те же, что в симуляции)."""
    sg = 1 if s == "L" else -1
    qy_l = qy                                  # «+» — наружу у обеих (у правой после зеркала — по часовой)
    def T_ay(m): return m.rotate([0, 0, qy_l])
    def T_up(m): return T_ay(m.rotate([0, -qp, 0]))
    def T_fore(m): return T_up(m.rotate([0, -qe, 0]).translate([G["a1"], 0, 0]))
    def T_hand(m): return T_fore(m.translate([G["fore"], 0, 0]))
    jaw = moving_jaw(1).rotate([0, 0, qg]).translate([GX, GY, 0])
    a = {"ay": [("yaw_bracket", T_ay(yaw_bracket())), ("lift_servo", T_ay(lift_servo_arm()))],
         "up": [("upper_arm", T_up(upper_arm())), ("elbow_servo", T_up(elbow_servo_up()))],
         "fore": [("forearm", T_fore(forearm())), ("grip_servo", T_hand(grip_servo_hand())), ("fixed_jaw", T_hand(fixed_jaw(1)))],
         "jaw": [("moving_jaw", T_hand(jaw))]}
    x, y, z = G["arm_s"][s]
    fin = (lambda m: m.translate([x, y, z])) if sg > 0 else (lambda m: m.mirror([0, 1, 0]).translate([x, y, z]))
    return {k: [(nm, fin(m)) for nm, m in v] for k, v in a.items()}


def eye_assembly(s, qs):
    """Глаз: крен qs (+ внутрь, − наружу), правый — зеркало левого."""
    sg = 1 if s == "L" else -1
    parts = [("eye_stalk", eye_stalk(1).rotate([qs, 0, 0])), ("display", display(1).rotate([qs, 0, 0]))]
    x, y, z = G["eye"][s]
    fin = (lambda m: m.translate([x, y, z])) if sg > 0 else (lambda m: m.mirror([0, 1, 0]).translate([x, y, z]))
    return {"eye": [(nm, fin(m)) for nm, m in parts]}


def fixed_parts():
    """Всё, что неподвижно в корпусе: ванна, крышка, приводы в корпусе, электроника, датчики края."""
    f = {"chassis": chassis(), "lid": lid()}
    for n, m in coxa_servos().items(): f[f"coxa_servo_{n}"] = m
    for s, m in yaw_servos().items(): f[f"yaw_servo_{s}"] = m
    for s, m in eye_servos().items(): f[f"eye_servo_{s}"] = m
    for k, m in electronics().items(): f[k] = m
    for i, m in enumerate(edge_sensors()): f[f"edge_{i}"] = m
    return f


# ---------------- проверка столкновений ----------------
def inter(a, b):
    """Объём пересечения, мм³ (с быстрым отсевом по габаритам)."""
    if a.is_empty() or b.is_empty():
        return 0.0
    ba, bb = a.bounding_box(), b.bounding_box()
    if any(ba[i] > bb[i + 3] or bb[i] > ba[i + 3] for i in range(3)):
        return 0.0
    return (a ^ b).volume()


def U(ms):
    import manifold3d
    ms = [m for m in ms if not m.is_empty()]
    return Manifold.batch_boolean(ms, manifold3d.OpType.Add) if len(ms) > 1 else (ms[0] if ms else Manifold())


STAND = (0.0, 20.0, -110.0)                 # стойка ног: бедро +20°, голень вертикально
LEG_POSES = [(20, -110), (40, -110), (0, -90), (-20, -70), (60, -130), (85, -130), (-45, -60), (20, -60), (50, -90)]
LEG_QC = [-20, -10, 0, 10, 20]
CLAW_TUCK = (8.0, 50.0, -130.0, 10.0)   # «поджато»: кисти подняты и чуть наружу — камере закрыто 18 % кадра (было 48 %), центр свободен, глаза видно


def _flat(asm):
    return [m for parts in asm.values() for _, m in parts]


RULES = """Правила движения «Компакт мини» (соблюдают симуляция и прошивка):
1. Клешни: подъём −20…+90° (вверх-назад на спину не нужно; до стола клешня достаёт, когда Харви приседает),
   локоть −140…+60°; поворот внутрь до −10° (другая клешня), наружу до 70°, но пока клешня ниже крышки —
   наружу не больше 8° (там передняя нога); поднятая выше 60° — только прямо или наружу (глаза).
2. Подъём клешни выше 60° — свой глаз отклонён наружу на 45°.
4. Локоть, запястье и губки ниже крышки не заходят за переднюю кромку корпуса (x ≤ 67 мм) — там камера, ноги и датчики.
3. Ноги: поворот ±20° (соседние ноги навстречу — не больше 20° суммарно сверх стойки), бедро −45…+85°, колено −130…−60°."""


def claw_points(s, qy, qp, qe):
    """Локоть, запястье и кончик губок клешни в системе корпуса (мм) — прямая кинематика."""
    x, y, z = G["arm_s"][s]
    a, b = math.radians(qp), math.radians(qp + qe)
    pts = [(G["a1"] * math.cos(a), G["a1"] * math.sin(a))]
    pts.append((pts[0][0] + G["fore"] * math.cos(b), pts[0][1] + G["fore"] * math.sin(b)))
    pts.append((pts[1][0] + (GX + 26) * math.cos(b), pts[1][1] + (GX + 26) * math.sin(b)))
    c, sn = math.cos(math.radians(qy)), math.sin(math.radians(qy)); sg = 1 if s == "L" else -1
    return [(x + r * c, y + sg * r * sn, z + h) for r, h in pts]


def claw_ok(qy, qp, qe, s="L"):
    """Разрешённые позы клешни (правила 1, 4, 5): на запрещённые проверку не тратим, прошивка их не даёт."""
    if not (-10 <= qy <= 70 and -20 <= qp <= 90 and -140 <= qe <= 60):
        return False
    x1, z1 = G["body"][1], G["body"][5]
    pts = claw_points(s, qy, qp, qe)
    low = any(pz <= z1 + 3 for _, _, pz in pts)
    if low and qy > 8:                         # низко: наружу ≤ 8° (передняя нога)
        return False
    if qp >= 60 and qy < 0:                    # поднята: только прямо или наружу (глаза)
        return False
    return all(px > x1 + 3 or pz > z1 + 3 for px, py, pz in pts)


def check(fast=False, verbose=True):
    """Столкновения в рабочих позах. Возвращает список (что, с чем, поза, мм³)."""
    t0 = time.time()
    fx = fixed_parts()
    body = U(list(fx.values()))
    hits = []
    def rec(a, b, pose, v):
        if v > 0.5: hits.append((a, b, pose, round(v, 1)))
    # 1. нога сама с собой и с корпусом
    n = "LM"; own = fx["coxa_servo_LM"]; body_wo = U([m for k, m in fx.items() if k != "coxa_servo_LM"])
    for qf, qk in (LEG_POSES[:3] if fast else LEG_POSES):
        for qc in ([0] if fast else LEG_QC):
            a = leg_assembly(n, qc, qf, qk)
            cx, fe, ti = U([m for _, m in a["coxa"]]), U([m for _, m in a["femur"]]), U([m for _, m in a["tibia"]])
            rec("нога: основание", "голень", (qc, qf, qk), inter(cx, ti))
            rec("нога: бедро", "корпус", (qc, qf, qk), inter(fe, body))
            rec("нога: голень", "корпус", (qc, qf, qk), inter(ti, body))
            rec("нога: основание", "корпус", (qc, qf, qk), inter(cx, body_wo))
            rec("нога: привод колена", "основание", (qc, qf, qk), inter(a["femur"][1][1], cx))
            rec("нога: голень", "бедро (без своего диска)", (qc, qf, qk), inter(a["tibia"][0][1], a["femur"][0][1]))
    # 2. соседние ноги одной стороны
    for na, nb in (("LF", "LM"), ("LM", "LB")):
        for qa in ([-20, 0, 20] if fast else LEG_QC):
            for qb in ([-20, 0, 20] if fast else LEG_QC):
                for qf, qk in (((20, -110),) if fast else ((20, -110), (60, -130))):
                    if qa - qb > 20: continue                       # правило 3: навстречу не больше 20°
                    A = U(_flat(leg_assembly(na, qa, qf, qk))); B = U(_flat(leg_assembly(nb, qb, qf, qk)))
                    rec(f"нога {na}", f"нога {nb}", (qa, qb, qf, qk), inter(A, B))
    # 3. клешни: с корпусом, передней ногой, глазом, другой клешнёй, сама с собой
    legF = U(_flat(leg_assembly("LF", 0, 20, -110))); legF2 = U(_flat(leg_assembly("LF", 30, 20, -110)))
    eye0 = U(_flat(eye_assembly("L", 0))); eye_out = U(_flat(eye_assembly("L", -45)))
    tuckR = U(_flat(claw_assembly("R", *CLAW_TUCK)))
    body_wo = U([m for k, m in fx.items() if k != "yaw_servo_L"])
    QY = [0, 30] if fast else [-10, 0, 8, 15, 30, 50, 70]
    QP = [0, 30] if fast else [-20, -10, 0, 10, 20, 30, 45, 60, 75, 90]
    QE = [-120, -60] if fast else [-140, -120, -100, -80, -60, -40, -20, 0, 20, 40, 60]
    for qy in QY:
        for qp in QP:
            for qe in QE:
                if not claw_ok(qy, qp, qe): continue
                a = claw_assembly("L", qy, qp, qe, 10.0)
                ay = U([m for _, m in a["ay"]]); rest = U([m for k in ("up", "fore", "jaw") for _, m in a[k]])
                arm = U([ay, rest]); pose = (qy, qp, qe)
                rec("клешня L", "корпус", pose, inter(rest, body))
                rec("клешня L: стойка плеча", "корпус", pose, inter(ay, body_wo))
                rec("клешня L", "нога LF", pose, inter(arm, legF)); rec("клешня L", "нога LF (вперёд 30°)", pose, inter(arm, legF2))
                rec("клешня L", "клешня R (поджата)", pose, inter(arm, tuckR))
                rec("клешня L", "глаз L", pose, inter(arm, eye_out if qp >= 60 else eye0))
                rec("клешня L: предплечье", "плечо и стойка", pose, inter(U([m for _, m in a["fore"]] + [a["jaw"][0][1]]), ay))
    # 4. глаза: крен −90 … +20 с поджатыми клешнями
    tuckL = U(_flat(claw_assembly("L", *CLAW_TUCK))); body_we = U([m for k, m in fx.items() if k != "eye_servo_L"])
    for qs in (-90, -60, -30, 0, 20):
        e = U(_flat(eye_assembly("L", qs)))
        rec("глаз L", "корпус", qs, inter(e, body_we))
        rec("глаз L", "клешня L (поджата)", qs, inter(e, tuckL))
        rec("глаз L", "нога LF", qs, inter(e, legF))
    # 5. корпус: детали внутри не пересекают друг друга
    keys = list(fx.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            rec(f"корпус: {keys[i]}", keys[j], "-", inter(fx[keys[i]], fx[keys[j]]))
    if verbose:
        print(f"проверка: {len(hits)} столкновений за {time.time() - t0:.0f} с")
        seen = {}
        for h in hits:
            seen.setdefault((h[0], h[1]), []).append((h[2], h[3]))
        for k, v in seen.items():
            print(f"  {k[0]} × {k[1]}: {len(v)} поз, напр. {v[0][0]} — до {max(x[1] for x in v)} мм³")
    return hits


# ---------------- масса ----------------
PRINTED = {   # деталь: (функция, сколько штук, материал)
    "coxa_bracket": (coxa_bracket, 6, "PLA"), "femur_link": (femur_link, 6, "PLA"), "tibia": (tibia, 6, "PLA"),
    "foot": (foot, 6, "TPU"), "yaw_bracket": (yaw_bracket, 2, "PLA"), "upper_arm": (upper_arm, 2, "PLA"),
    "forearm": (forearm, 2, "PLA"), "fixed_jaw": (lambda: fixed_jaw(1), 2, "PLA"), "moving_jaw": (lambda: moving_jaw(1), 2, "PLA"),
    "eye_stalk": (lambda: eye_stalk(1), 2, "PLA"), "chassis": (chassis, 1, "PLA"), "lid": (lid, 1, "PLA"),
    "dock_pad": (dock_pad, 1, "PLA"), "dock_tower": (dock_tower, 1, "PLA"), "leg_stand": (leg_stand, 1, "PLA"),
}
PARTS_G = {"STS3032 × 28": 28 * 20.0, "2 × 18650": 2 * 47.0, "Pi Zero 2 W": 11.0, "RP2350-Zero": 3.0, "DC-DC 6 В + 5 В": 18.0,
           "BMS + заряд 2S": 6.0, "IMU + INA226": 3.0, "камера Module 3 Wide": 4.0, "микрофоны + усилитель": 4.0, "динамик Ø20": 6.0,
           "6 × VL53L4CD": 9.0, "2 дисплея 0,71″": 10.0, "провода и разъёмы": 25.0, "винты M2, контакты зарядки": 18.0, "накладки TPU": 2.0}


def printed_mass():
    out = {}
    for k, (fn, n, mat) in PRINTED.items():
        if k.startswith("dock") or k == "leg_stand": continue   # станция и стенд — не на роботе
        v = fn().volume()
        out[k] = round(v * (TPU if mat == "TPU" else PLA * INFILL) * n, 1)
    return out


def check_dock(verbose=True):
    """Станция: стоя над ней — ноги и корпус её не задевают; лёжа (корпус ниже на REST_DROP) — пластины брюха
    ложатся на контакты, остальное не касается. Станция — в системе стола, Харви по центру, лицом к башенке."""
    z_stand = G["tib"] - G["fem"] * math.sin(math.radians(20))      # оси бедра над столом в стойке
    out = {}
    pad = U([dock_pad(), dock_tower()] + dock_pogo())
    for name, dz in (("стоя", 0.0), ("лёжа", REST_DROP)):
        zj = z_stand - dz
        robot = U([m.translate([0, 0, zj]) for m in fixed_parts().values()])
        legs = []
        for n in G["mounts"]:
            for parts in leg_assembly(n, 0, *leg_pose_for_drop(dz)).values():
                legs += [m.translate([0, 0, zj]) for _, m in parts]
        claws = [m.translate([0, 0, zj]) for sd in "LR" for parts in claw_assembly(sd, *CLAW_TUCK).values() for _, m in parts]
        out[name] = {"корпус × станция мм³": round(inter(robot, U([dock_pad(), dock_tower()])), 1),
                     "ноги × станция мм³": round(inter(U(legs), pad), 1), "клешни × станция мм³": round(inter(U(claws), pad), 1),
                     "зазор брюхо — контакты мм": round(zj + G["body"][4] - POGO_TOP, 1)}
    if verbose: print("станция:", out)
    return out


def check_stand(verbose=True):
    """Стенд ноги: нога во всех рабочих позах не задевает стенд; в стойке стопа на столе."""
    zj = G["tib"] - G["fem"] * math.sin(math.radians(20))
    st = leg_stand(); hits = 0
    for qf, qk in LEG_POSES:
        for qc in LEG_QC:                       # правило 3: поворот ±20°
            a = leg_assembly("LM", 0, qf, qk)   # стенд — в системе ноги: перенесём ногу в начало
            x, y, yaw = G["mounts"]["LM"]
            parts = [m.translate([-x, -y, 0]).rotate([0, 0, -yaw + qc]).translate([0, 0, zj]) for p_ in a.values() for _, m in p_]
            v = inter(U(parts), st)
            if v > 0.5: hits += 1
    if verbose: print(f"стенд ноги: {hits} столкновений из {len(LEG_POSES) * len(LEG_QC)} поз")
    return hits


def leg_pose_for_drop(dz):
    """Углы бедра и колена (градусы), чтобы стопа осталась на месте при корпусе ниже на dz мм."""
    f, t, r = G["fem"], G["tib"] - G["foot_r"], G["foot_r"]
    rr = G["fem"] * math.cos(math.radians(20)); h = -(G["tib"] - G["fem"] * math.sin(math.radians(20)) - r) + dz
    d = math.hypot(rr, h)
    qf = math.atan2(h, rr) + math.acos((f * f + d * d - t * t) / (2 * f * d))
    qk = -(math.pi - math.acos((f * f + t * t - d * d) / (2 * f * t)))
    return math.degrees(qf), math.degrees(qk)


def mass_report():
    pm = printed_mass(); tot = sum(pm.values()) + sum(PARTS_G.values())
    return {"печать_г": pm, "печать_всего_г": round(sum(pm.values())), "покупное_г": PARTS_G, "всего_г": round(tot)}


def link_masses():
    """Массы звеньев для симуляции (кг): деталь + приводы на этом звене."""
    pm = {k: v / PRINTED[k][1] for k, v in printed_mass().items()}
    sv = 0.020
    return {"coxa": pm["coxa_bracket"] / 1000 + sv, "femur": pm["femur_link"] / 1000 + sv, "tibia": (pm["tibia"] + pm["foot"]) / 1000,
            "ay": pm["yaw_bracket"] / 1000 + sv, "up": pm["upper_arm"] / 1000 + sv, "fore": pm["forearm"] / 1000,
            "hand": pm["fixed_jaw"] / 1000 + sv + 0.001, "jaw": pm["moving_jaw"] / 1000 + 0.0005, "eye": (pm["eye_stalk"] + 5.0) / 1000,
            "total": mass_report()["всего_г"] / 1000}


# ---------------- выгрузка ----------------
def to_tm(m):
    mm = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)


def export_stl(out=None):
    out = out or os.path.join(HERE, "stl"); os.makedirs(out, exist_ok=True)
    for k, (fn, n, mat) in PRINTED.items():
        to_tm(fn()).export(os.path.join(out, f"{k}{'_x' + str(n) if n > 1 else ''}_{mat}.stl"))
    for k, fn in (("fixed_jaw_R", lambda: fixed_jaw(-1)), ("moving_jaw_R", lambda: moving_jaw(-1)), ("eye_stalk_R", lambda: eye_stalk(1).mirror([0, 1, 0]))):
        to_tm(fn()).export(os.path.join(out, f"{k}_PLA.stl"))
    return out


def export_sim(out):
    """Видимые детали для симуляции: STL на тело (м), в системе тела — как в код/симуляция/мини/harvey_mini.py."""
    os.makedirs(out, exist_ok=True); man = {}
    def put(body, mat, ms):
        m = U(ms)
        if m.is_empty(): return
        tm = to_tm(m); tm.vertices = tm.vertices / 1000.0
        f = f"{body}__{mat}.stl"; tm.export(os.path.join(out, f)); man.setdefault(body, []).append([f, mat])
    fx = fixed_parts()
    put("torso", "grey", [fx["chassis"], fx["lid"]])
    put("torso", "servo", [m for k, m in fx.items() if "servo" in k])
    put("torso", "pcb", [m for k, m in fx.items() if k not in ("chassis", "lid") and "servo" not in k and "18650" not in k])
    put("torso", "battery", [fx["батарея 2S 18650"]])
    put("leg_coxa", "orange", [coxa_bracket()]); put("leg_coxa", "servo", [femur_servo_coxa()])
    put("leg_femur", "orange", [femur_link()]); put("leg_femur", "servo", [knee_servo_femur()])
    put("leg_tibia", "orange", [tibia()]); put("leg_tibia", "tpu", [foot()])
    for s, sg in (("L", 1), ("R", -1)):
        mir = (lambda m: m) if sg > 0 else (lambda m: m.mirror([0, 1, 0]))
        put(f"{s}_ay", "grey", [mir(yaw_bracket())]); put(f"{s}_ay", "servo", [mir(lift_servo_arm())])
        put(f"{s}_up", "orange", [mir(upper_arm())]); put(f"{s}_up", "servo", [mir(elbow_servo_up())])
        put(f"{s}_fore", "orange", [mir(forearm())])
        put(f"{s}_hand", "servo", [mir(grip_servo_hand())]); put(f"{s}_hand", "tpu", [mir(fixed_jaw(1))])
        put(f"{s}_jaw", "tpu", [mir(moving_jaw(1).translate([0, 0, 0]))])
        put(f"{s}_eye", "orange", [mir(eye_stalk(1))]); put(f"{s}_eye", "screen", [mir(display(1))])
    for k, fn in (("dock_pad", dock_pad), ("dock_tower", dock_tower)):
        tm = to_tm(fn()); tm.vertices = tm.vertices / 1000.0; tm.export(os.path.join(out, f"{k}.stl")); man.setdefault("dock", []).append([f"{k}.stl", "grey"])
    json.dump({"bodies": man, "G": G, "GX": GX, "GY": GY, "masses": link_masses(), "belly_y": BELLY_Y, "dock_h": DOCK_H,
               "pogo_top": POGO_TOP, "rest_drop": REST_DROP},
              open(os.path.join(out, "mini_visual.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    fast = "--fast" in sys.argv
    print(json.dumps(mass_report(), ensure_ascii=False, indent=1))
    hits = check(fast)
    check_dock(); check_stand()
    if not fast:
        print("STL:", export_stl())
        print("для симуляции:", export_sim(os.path.join(HERE, "..", "..", "код", "симуляция", "мини", "assets")))
    print(RULES)
