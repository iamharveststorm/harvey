"""Харви: компоновка — все конечности (готовые модели ног, клешней, хвоста) в системе корпуса.
Система корпуса как в симуляции (harvey_sim.py): начало — на уровне осей бедра в центре корпуса,
x — вперёд, y — влево, z — вверх; мм. Числа точек крепления — здесь и в симуляции одинаковые.
    python harvey_layout.py          # проверка: задевают ли соседние конечности друг друга во всех рабочих ходах
"""
import os, sys, math, importlib.util
import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def load(name, rel):
    path = os.path.join(ROOT, rel)
    d = os.path.dirname(path)
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return m


LP = load("harvey_leg_parts", "стенд ноги/harvey_leg_parts.py")
_argv = sys.argv; sys.argv = sys.argv[:1]
LC = load("leg_check", "стенд ноги/leg_check.py")
sys.argv = _argv
CP = load("harvey_claw_parts", "клешни/harvey_claw_parts.py")
TP = load("harvey_tail_parts", "хвост/harvey_tail_parts.py")
EP = load("harvey_eye_parts", "глаза/harvey_eye_parts.py")

# ---------------- точки крепления (мм, градусы) ----------------
MOUNTS = {  # ось привода основания ноги: x, y, направление ноги
    "RF": (55.0, -58.0, -50.0), "RM": (0.0, -66.0, -90.0), "RB": (-55.0, -58.0, -130.0),
    "LF": (55.0, 58.0, 50.0), "LM": (0.0, 66.0, 90.0), "LB": (-55.0, 58.0, 130.0),
}
COXA_DROP = LP.P["coxa_drop"]          # фланец привода основания выше осей бедра
ARM_S = {"L": (105.0, 30.0, 65.0), "R": (105.0, -30.0, 65.0)}   # плечо клешни (ось подъёма ∩ ось поворота): впереди передних ног
T_MOUNT = (-80.0, 0.0, 72.0)            # хвост: ось подъёма ∩ ось поворота; хвост смотрит назад
EYE_PIVOT = {"L": (70.0, 80.0, 76.0), "R": (70.0, -80.0, 76.0)}   # глаза на передних углах, снаружи от полос клешней; ось — вдоль x


def _to_world(ms, rz, t):
    return [m.rotate([0, 0, rz]).translate(list(t)) for m in ms]


def leg(name, qc, qf, qk, links=None):
    """Нога в системе корпуса: {звено: [детали + приводы]}; основание — только привод (держит корпус)."""
    lk = links or LEG_LINKS
    x, y, yaw = MOUNTS[name]
    P_ = LC.posed(lk, qc, qf, qk)
    return {k: _to_world([m.translate([0, 0, COXA_DROP]) for m in v], yaw, (x, y, 0)) for k, v in P_.items()}


def _mirror_y(m):
    return m.mirror([0, 1, 0])


def claw(side, q, parts=None):
    """Клешня: q = (поворот, подъём, локоть, запястье, захват) — углы как в симуляции. Правая — зеркальная."""
    pr = parts or CLAW_PARTS
    if side == "L":
        P_ = CP.posed(pr, q)
        return {k: [m.translate(list(ARM_S["L"])) for m in v] for k, v in P_.items()}
    q2 = (-q[0], q[1], q[2], -q[3], q[4])
    P_ = CP.posed(pr, q2)
    return {k: [_mirror_y(m).translate(list(ARM_S["R"])) for m in v] for k, v in P_.items()}


def tail(q, parts=None):
    """Хвост: q = (поворот, подъём, локоть, запястье), углы как в симуляции (harvey_tail.py)."""
    P_ = TP.posed(parts or TAIL_PARTS, q)
    return {k: _to_world(v, 180.0, T_MOUNT) for k, v in P_.items()}


def eye(side, tilt, parts=None):
    """Глаз: tilt — крен стебелька, градусы: 0 — вверх, + внутрь (к середине), − наружу (−135 — сложен наружу-вниз).
    {"fixed": [привод], "moving": [...]}; правый — зеркальный."""
    mv, sv = parts or EYE_PARTS
    out = {"fixed": [sv], "moving": [CP.rot(m, "x", tilt) for m in mv]}
    if side == "L":
        return {k: [m.translate(list(EYE_PIVOT["L"])) for m in v] for k, v in out.items()}
    return {k: [m.mirror([0, 1, 0]).translate(list(EYE_PIVOT["R"])) for m in v] for k, v in out.items()}


def links_without_tower():
    lk = LC.links()
    lk["base"] = ([], lk["base"][1])
    return lk


def claw_parts_chassis():
    """Клешня без пластины основания (её роль играет рама корпуса): неподвижна только J1."""
    pr = CP.link_parts()
    pr["base"] = ([], pr["base"][1])
    return pr


def tail_parts_chassis():
    pr = TP.link_parts()
    pr["base"] = ([], pr["base"][1])
    return pr


LEG_LINKS = links_without_tower()
CLAW_PARTS = claw_parts_chassis()
TAIL_PARTS = tail_parts_chassis()
EYE_PARTS = (EP.moving_parts(), EP.servo_body())


def flat(d, skip=()):
    return [m for k, v in d.items() if k not in skip for m in v]


def union(ms):
    return Manifold.batch_boolean(ms, OpType_Add) if ms else Manifold()


try:
    from manifold3d import OpType
    OpType_Add = OpType.Add
except Exception:  # старые версии
    OpType_Add = None


def inter(a, b):
    v = 0.0
    for x in a:
        bx = x.bounding_box()
        for y in b:
            by = y.bounding_box()
            if bx[0] > by[3] or by[0] > bx[3] or bx[1] > by[4] or by[1] > bx[4] or bx[2] > by[5] or by[2] > bx[5]:
                continue
            v += (x ^ y).volume()
    return v


# ---------------- рабочие ходы (из симуляции и проверок деталей) ----------------
LEG_POSES = [(20, -110), (52, -127), (46.2, -125), (100, -60), (-53, -36), (15, -153)]
LEG_QC = (-25, 0, 25)
CLAW_POSES = [(14, -102), (36, -95), (-5, -61), (75, -99), (129, -94), (156, -88), (119, 38), (105, 101), (70, 104), (89, 72), (81, 126), (0, 0), (-12, -40)]   # путь «на спину» v2: (119;38), (105;101), (70;104)
CLAW_YAW = (-30, -15, 0, 25, 50, 75)        # левая клешня: + наружу; внутрь не больше 30°
TAIL_LOW = [(-25, -33, -32), (12, -84, -18), (71, -119, -42)]          # к столу — только назад (поворот ±30°)
TAIL_HIGH = [(66, 126, 78), (98, 0, 172), (132, -11, 0), (20, 0, 0), (91, 113, 66)]   # над корпусом и вбок — ±120°
TAIL_POSES = TAIL_HIGH + TAIL_LOW
TAIL_YAW = (-100, -90, -60, 0, 60, 90, 100)   # вбок до ±100° — только поднятым над горизонталью на 20° и больше
TAIL_YAW_LOW = (-30, 0, 30)


# ---------------- правила движения (их же соблюдает симуляция и прошивка) ----------------
RULES = """1. Клешни: в низких позах (подъём < 80°) поворот ±15°; наружу до 75° — только с поднятой рукой;
   над головой и при укладке на спину — без поворота внутрь; внутрь обе клешни одновременно не поворачиваются.
2. Хвост: к столу — только назад (поворот ±30°) и когда робот стоит (основания ног 0°);
   вбок до ±100° — только поднятым над горизонталью на 20° и больше.
3. Ноги: бедро выше 90° — только при перевороте (основание 0°); у передних ног — не выше 90°.
4. Глаза: крен наружу до −75° (сложены), внутрь до +20° — пока своя клешня внизу; когда своя клешня
   поднята (подъём ≥ 60°), глаз отклонён наружу не меньше чем на 20°."""


def leg_ok(n, qc, qf, qk):
    return not (qf > 90 and (n[1] == "F" or qc != 0))


def claw_ok(yw, qp, qe):
    if abs(yw) > 15 and qp < 80:
        return False
    if yw < 0 and qp >= 80:
        return False
    return True


def eye_ok(tilt, claw_q):
    return not (claw_q[1] >= 60 and tilt > -20)


def check(verbose=True):
    """Пары соседних конечностей во всех комбинациях поз, разрешённых правилами RULES."""
    bad = []
    EYE_TILTS = (20, 0, -20, -75)
    for side, legn in (("L", "LF"), ("R", "RF")):
        legs = [(qc, qf, qk, leg(legn, qc, qf, qk)) for qc in LEG_QC for qf, qk in LEG_POSES if leg_ok(legn, qc, qf, qk)]
        for yw in CLAW_YAW:
            for qp, qe in CLAW_POSES:
                if not claw_ok(yw, qp, qe):
                    continue
                cm = flat(claw(side, (yw if side == "L" else -yw, qp, qe, 0, 0)))
                for qc, qf, qk, lg in legs:
                    v = inter(flat(lg), cm)
                    if v > 0.5:
                        bad.append((f"клешня {side}", legn, (yw, qp, qe), (qc, qf, qk), round(v)))
    for legn in ("LB", "RB"):
        legs = [(qc, qf, qk, leg(legn, qc, qf, qk)) for qc in LEG_QC for qf, qk in LEG_POSES if leg_ok(legn, qc, qf, qk)]
        for ty, tq, low in [(a, b, False) for a in TAIL_YAW for b in TAIL_HIGH] + [(a, b, True) for a in TAIL_YAW_LOW for b in TAIL_LOW]:
            tm = flat(tail((ty,) + tq), skip=("base",))
            for qc, qf, qk, lg in legs:
                if low and qc != 0:
                    continue
                v = inter(flat(lg, skip=("base",)), tm)
                if v > 0.5:
                    bad.append(("хвост", legn, (ty,) + tq, (qc, qf, qk), round(v)))
    for qp, qe in CLAW_POSES:
        v = inter(flat(claw("L", (0, qp, qe, 0, 0))), flat(claw("R", (0, qp, qe, 0, 0))))
        if v > 0.5:
            bad.append(("клешня L", "клешня R", (0, qp, qe), None, round(v)))
    for side, legn in (("L", "LF"), ("R", "RF")):
        for tilt in EYE_TILTS:
            em = flat(eye(side, tilt))
            for yw in (-15, 0, 15):
                for qp, qe in CLAW_POSES:
                    if not claw_ok(yw, qp, qe):
                        continue
                    for cs in "LR":
                        if cs == side and not eye_ok(tilt, (yw, qp, qe)):
                            continue
                        v = inter(em, flat(claw(cs, (yw if cs == "L" else -yw, qp, qe, 0, 0))))
                        if v > 0.5:
                            bad.append((f"глаз {side}", f"клешня {cs}", (yw, qp, qe), tilt, round(v)))
            for qc in LEG_QC:
                for qf, qk in LEG_POSES:
                    if not leg_ok(legn, qc, qf, qk):
                        continue
                    v = inter(em, flat(leg(legn, qc, qf, qk), skip=("base",)))
                    if v > 0.5:
                        bad.append((f"глаз {side}", legn, (qc, qf, qk), tilt, round(v)))
            for ty in TAIL_YAW:
                for tq in TAIL_HIGH:
                    v = inter(em, flat(tail((ty,) + tq), skip=("base",)))
                    if v > 0.5:
                        bad.append((f"глаз {side}", "хвост", (ty,) + tq, tilt, round(v)))
    for t1 in (20, 0):
        for t2 in (20, 0):
            v = inter(flat(eye("L", t1)), flat(eye("R", t2)))
            if v > 0.5:
                bad.append(("глаз L", "глаз R", t1, t2, round(v)))
    if verbose:
        for b in bad[:60]:
            print(" ", b)
        print(f"всего столкновений: {len(bad)}")
    return bad


def top_view(path, qsets=None):
    """Вид сверху: заметаемые области (проекции) приводов и деталей у корпуса."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 9))
    def draw(ms, color, alpha=0.15):
        for m in ms:
            if m.is_empty():
                continue
            for poly in m.project().to_polygons():
                p = np.asarray(poly)
                ax.fill(p[:, 0], p[:, 1], color=color, alpha=alpha, lw=0)
    for n in MOUNTS:
        for qc in LEG_QC:
            for qf, qk in LEG_POSES[:3]:
                lg = leg(n, qc, qf, qk)
                draw(lg["base"], "k", 0.05); draw(lg["coxa"], "tab:blue", 0.05)
    for side in "LR":
        for yw in CLAW_YAW:
            for qp, qe in CLAW_POSES[:4]:
                c = claw(side, (yw if side == "L" else -yw, qp, qe, 0, 0))
                draw(c["base"], "k", 0.05); draw(c["yaw"], "tab:orange", 0.05); draw(c["up"], "tab:red", 0.03)
    for ty in TAIL_YAW:
        t = tail((ty,) + TAIL_POSES[0])
        draw(t["base"], "k", 0.05); draw(t["yaw"], "tab:green", 0.05)
    ax.add_patch(plt.Rectangle((-75, -70), 150, 140, fill=False, ec="k", ls="--"))
    ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.set_xlim(-170, 190); ax.set_ylim(-150, 150)
    ax.set_title("Харви, вид сверху: заметаемые области у корпуса (пунктир — корпус 150 × 140)")
    fig.savefig(path, dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    os.chdir(HERE)
    top_view("компоновка_вид_сверху.png")
    check()
