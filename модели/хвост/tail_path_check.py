"""Проверка путей хвоста из симуляции (harvey_tail.py) на модели деталей: каждая точка пути и промежуточные
положения (линейно по суставам, как в симуляции) — без столкновений деталей хвоста между собой.
    python tail_path_check.py"""
import math
import numpy as np
import harvey_tail_parts as TP

T_MOUNT = np.array([-80.0, 0.0, 72.0])
T1 = T2 = 70.0
CUP = 26.0


def tail_ik(p, branch="down"):
    """Как tail_ik в harvey_tail.py (мм, градусы): точка присоски в системе корпуса → (поворот, подъём, локоть, запястье)."""
    d = np.asarray(p, float) - T_MOUNT + np.array([0, 0, CUP])
    lx, ly, dz = -d[0], -d[1], d[2]
    if lx >= 0: yaw = math.atan2(ly, lx); r = math.hypot(lx, ly)
    else: yaw = math.atan2(-ly, -lx); r = -math.hypot(lx, ly)
    dist = min(max(math.hypot(r, dz), abs(T2 - T1) + 1e-4), T1 + T2 - 1e-4)
    a = math.acos(max(-1, min(1, (T1**2 + dist**2 - T2**2) / (2 * T1 * dist))))
    g = math.acos(max(-1, min(1, (T1**2 + T2**2 - dist**2) / (2 * T1 * T2))))
    base = math.atan2(dz, r)
    p_, e_ = (base + a, -(math.pi - g)) if branch == "up" else (base - a, math.pi - g)
    w = -math.pi / 2 - (p_ + e_)
    w = (w + math.pi) % (2 * math.pi) - math.pi
    return np.degrees([yaw, p_, e_, w])


ZJ = 52.6
ZT = -(ZJ - 8.5) - 1.5
REST = tail_ik([-40, 0, 95])
PATHS = {
    "телефон сзади → на спину": [([-170, 0, ZT + 40], "up"), ([-180, 0, ZT + 2], "up"), ([-150, 0, 60], "up"),
                                 ([-90, 0, 175], "down"), ([-15, 0, 140], "down"), ([-15, 0, 88], "down"),
                                 ([-50, 0, 140], "down"), (REST, None)],
    "передача телефона клешням": [([-170, 0, ZT + 40], "up"), ([-180, 0, ZT + 2], "up"), ([-150, 0, 60], "up"),
                                  ([-60, 0, 190], "down"), ([30, 0, 190], "down"), ([-40, 0, 140], "down"), (REST, None)],
    "переворот со спины (вбок 90°)": [(REST, None), ((90, 0, 0, 0), None), ((90, 92, -17, 0), None),
                                      ((90, 132, -11, 0), None), (REST, None)],
}

if __name__ == "__main__":
    parts = TP.link_parts()
    print("поза покоя:", np.round(REST, 1))
    for name, pts in PATHS.items():
        qs = [np.asarray(tail_ik(p, br) if br else p, float) for p, br in pts]
        bad = []
        for i in range(len(qs) - 1):
            for k in np.linspace(0, 1, 7)[:-1] if i < len(qs) - 2 else np.linspace(0, 1, 7):
                q = qs[i] + (qs[i + 1] - qs[i]) * k
                v, where = TP.worst(TP.posed(parts, tuple(q)))
                if v > 0.5:
                    bad.append((i, round(k, 2), np.round(q).tolist(), round(v), where))
        print(f"{name}: точки {[np.round(q).astype(int).tolist() for q in qs]}")
        print("   ", "без столкновений" if not bad else "\n    ".join(map(str, bad)))
