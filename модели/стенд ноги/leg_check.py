"""Харви: полная проверка ноги — посадки, все пары деталей и приводов между звеньями, ходы суставов
(пределы симуляции), позы симуляции: рабочая стойка, покой, весь цикл шага.
    python leg_check.py                 # текущие размеры из harvey_leg_parts.py
    python leg_check.py --femur 47      # примерить другую длину бедра
Звенья: «основание» (привод основания, неподвижен) → «коксa» (кронштейн + привод бедра) →
«бедро» (2 пластины + обхват колена + привод колена) → «голень» (вилка + стопа).
Углы как в симуляции: бедро 0 — горизонтально, + вверх; колено 0 — голень продолжает бедро, − вниз."""
import sys, math, argparse
import numpy as np
from manifold3d import Manifold
import harvey_leg_parts as LP

ap = argparse.ArgumentParser()
ap.add_argument("--femur", type=float, default=None)
args = ap.parse_args()
P = LP.P
if args.femur:
    P["femur"] = args.femur
L, W, H, SF = P["servo_L"], P["servo_W"], P["servo_H"], P["shaft_from_end"]
CZ = -P["coxa_drop"]
TIB_FOOT = P["tibia"] + P["foot_r"]          # от оси колена до низа стопы (в симуляции 70)


def servo():
    """STS3215: корпус вдоль −x от вала, вал — y, фланцы с обеих сторон, головки винтов корпуса (если есть)."""
    b = LP.box(L, H, W, -(L / 2 - SF), 0, 0)
    for s in (1, -1):
        b += LP.cyl(P["flange_t"], P["flange_D"] / 2, 0, s * (H / 2 + P["flange_t"] / 2), 0, "y")
    if "case_screw" in P:
        cx, cy = P["case_screw"]
        for sz in (1, -1):
            for sy in (1, -1):
                b += LP.cyl(1.6, 1.9, cx, sy * (H / 2 + P["flange_t"] - 1.3 + 0.8), sz * cy, "y")
    return b


def coxa_servo():
    return LP.box(L, W, H, -(L / 2 - SF), 0, -P["flange_t"] - H / 2) + LP.cyl(P["flange_t"], P["flange_D"] / 2, 0, 0, -P["flange_t"] / 2)


def plates():
    m = Manifold()
    yi = H / 2 + P["flange_t"]
    for s in (1, -1):
        pl = LP.femur_plate().rotate([-90 if s > 0 else 90, 0, 0]).translate([0, s * (yi - 1.3), 0])
        m += pl
    return m


def links():
    """Детали и приводы в системах своих звеньев. Бедро — от оси бедра, голень — от оси колена (стержень вниз)."""
    return {
        "base": ([LP.leg_tower()], [coxa_servo()]),
        "coxa": ([LP.coxa_bracket()], [servo().translate([P["coxa"], 0, CZ])]),
        "femur": ([plates(), LP.knee_sleeve().translate([P["femur"], 0, 0])], [servo().translate([P["femur"], 0, 0])]),
        "tibia": ([LP.tibia_fork(), LP.foot().translate([0, 0, -(P["tibia"] - P["foot_r"]) - P["foot_r"] + 1 - 4])], []),
    }


def posed(lk, qc, qf, qk):
    out = {}
    for name, (pr, sv) in lk.items():
        ms = []
        for m in pr + sv:
            if name == "tibia":
                m = m.rotate([0, -90 - qk, 0]).translate([P["femur"], 0, 0])
            if name in ("tibia", "femur"):
                m = m.rotate([0, -qf, 0]).translate([P["coxa"], 0, CZ])
            if name != "base":
                m = m.rotate([0, 0, qc])
            ms.append(m)
        out[name] = ms
    return out


PAIRS = [("base", "coxa"), ("base", "femur"), ("base", "tibia"), ("coxa", "femur"), ("coxa", "tibia"), ("femur", "tibia")]


def worst(P_):
    best, where = 0.0, ""
    for a, b in PAIRS:
        for i, x in enumerate(P_[a]):
            for j, y in enumerate(P_[b]):
                v = (x ^ y).volume()
                if v > best:
                    best, where = v, f"{a}[{i}] × {b}[{j}]"
    return best, where


def ik(rr, hz):
    """Стопа (центр сферы) на rr от оси бедра по горизонтали и hz по вертикали → (бедро, колено), как в симуляции."""
    FEM, L2 = P["femur"], P["tibia"]
    d = min(max(math.hypot(rr, hz), abs(L2 - FEM) + 1e-4), FEM + L2 - 1e-4)
    qf = math.atan2(hz, rr) + math.acos(max(-1, min(1, (FEM ** 2 + d ** 2 - L2 ** 2) / (2 * FEM * d))))
    gam = math.acos(max(-1, min(1, (FEM ** 2 + L2 ** 2 - d ** 2) / (2 * FEM * L2))))
    return math.degrees(qf), -math.degrees(math.pi - gam)


if __name__ == "__main__":
    lk = links()
    FEM = P["femur"]
    print(f"Бедро {FEM:.1f} мм, голень до низа стопы {TIB_FOOT:.1f} мм, ось бедра ниже фланца основания на {-CZ:.0f} мм")
    print("Посадки на свои приводы:")
    for name, (pr, sv) in lk.items():
        for i, p in enumerate(pr):
            for s in sv:
                print(f"  {name}[{i}] × свой привод: {(p ^ s).volume():.1f} мм³")
    print("Нулевая поза (бедро 0°, колено −90°):", worst(posed(lk, 0, 0, -90)))
    badc = []
    for name_, (qf_, qk_) in (("стойка", (20, -110)), ("нога поднята", (52, -127)), ("покой", (46.2, -125)), ("бедро вниз", (-60, -30))):
        for qc in range(-60, 61, 5):
            v, w = worst(posed(lk, qc, qf_, qk_))
            if v > 0.5: badc.append((name_, qc, round(v), w))
    print("Поворот основания −60…+60° (стойка, нога поднята, покой, бедро вниз) со стойкой стенда:",
          "без столкновений" if not badc else badc)
    tb = LP.leg_tower().bounding_box()
    print(f"Стойка стенда: {tb[3]-tb[0]:.0f} × {tb[4]-tb[1]:.0f} × {tb[5]-tb[2]:.0f} мм, плита на z = {tb[2]:.1f} (стол)")
    # бедро во всём ходе симуляции, голень вертикально
    bad = []
    for qf in range(-60, 101, 10):
        v, w = worst(posed(lk, 0, qf, -(90 + qf)))
        if v > 0.5: bad.append((qf, round(v), w))
    print("Бедро −60…+100° (голень вертикально):", "без столкновений" if not bad else bad)
    ok = []
    for qk in range(-160, 31, 10):
        v, w = worst(posed(lk, 0, 20, qk))
        ok.append((qk, v <= 0.5))
    good = [q for q, g in ok if g]
    print(f"Колено при бедре 20° (симуляция −160…+30): без столкновений {min(good) if good else '—'}…{max(good) if good else '—'}",
          "" if all(g for _, g in ok) else f"; столкновения при {[q for q, g in ok if not g]}")
    # позы симуляции
    COX, ZJR, RR = P["coxa"], 32.0, 87.4                   # покой «на корточках», как в симуляции
    ZJ = TIB_FOOT - FEM * math.sin(math.radians(20))         # высота стойки — из длин (бедро +20°, голень вертикально)
    RW = P["coxa"] + FEM * math.cos(math.radians(20))
    poses = {"рабочая стойка": ik(RW - COX, -(ZJ - P["foot_r"])), "покой": ik(RR - COX, -(ZJR - P["foot_r"]))}
    for k in range(0, 20):                                   # цикл шага: ход 56 мм, подъём 25 мм
        ph = k / 20
        if ph < 0.5:
            u, z = 0.5 - 2 * ph, 0.0
        else:
            s = (ph - 0.5) * 2; u = -0.5 + (s - math.sin(2 * math.pi * s) / (2 * math.pi)); z = 25 * math.sin(math.pi * s)
        poses[f"шаг {k:2d}/20"] = ik(RW - COX + 56 * u * 0.0, -(ZJ - P["foot_r"]) + z)
        for qc in (-25, 25):                                  # шаг — это и поворот основания: стопа едет вдоль корпуса
            pass
    res = []
    for name, (qf, qk) in poses.items():
        v, w = worst(posed(lk, 0, qf, qk))
        res.append((name, qf, qk, v, w))
    n_bad = sum(1 for r in res if r[3] > 0.5)
    for name, qf, qk, v, w in res[:2]:
        print(f"  {name}: бедро {qf:6.1f}°, колено {qk:7.1f}° — {'ok' if v <= 0.5 else f'столкновение {v:.0f} мм³ ({w})'}")
    print(f"  цикл шага (подъём 25 мм): {'все позы без столкновений' if all(r[3] <= 0.5 for r in res[2:]) else [r for r in res[2:] if r[3] > 0.5]}")
