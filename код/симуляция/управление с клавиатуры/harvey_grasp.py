"""Харви: настоящий захват пальцами (без «приваривания») и безопасность щипка.
Кисть: неподвижный палец + подвижный на STS3032, накладки TPU. Пальцы смыкаются вбок,
поэтому ручку удобно брать, когда она лежит вдоль направления клешни."""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import math, re, json
import numpy as np
import mujoco
import harvey_sim as H
import harvey_scenarios as S

DT = S.DT
# пальцы согнуты вниз на ~30° относительно кисти: у стола они стоят почти вертикально и обхватывают предмет по длине
FINGERS = '''<geom name="{n}_handg" type="capsule" fromto="0.006 0 0 0.018 0 0" size="0.009" mass="0.047" rgba=".85 .4 .25 1"/>
              <geom name="{n}_ffix" type="capsule" fromto="0.018 0.008 0 0.0416 0.006 -0.0175" size="0.0035" mass="0.004" friction="{mu} 0.01 0.001" rgba=".2 .2 .2 1"/>
              <body name="{n}_fmov" pos="0.018 -0.008 0">
                <joint name="{n}_g" type="hinge" axis="0.52 0 0.85" range="-45 14" armature="0.0004" damping="0.002"/>
                <geom name="{n}_fmovg" type="capsule" fromto="0 0 0 0.0236 0.003 -0.0175" size="0.0035" mass="0.004" friction="{mu} 0.01 0.001" rgba=".2 .2 .2 1"/>
              </body>'''


def build(obj="", extra="", mu=1.0, table_mu=0.8):
    xml = H.build_xml(0.0, obj=None)
    for n in "LR":
        xml = re.sub(rf'<geom name="{n}_handg"[^>]*/>', FINGERS.format(n=n, mu=mu), xml)
    xml = xml.replace('</worldbody>', obj + extra + '</worldbody>')
    xml = xml.replace('<actuator>', '<actuator><motor name="m_L_g" joint="L_g" ctrlrange="-0.44 0.44"/><motor name="m_R_g" joint="R_g" ctrlrange="-0.44 0.44"/>', 1)
    xml = xml.replace('<geom name="floor" type="plane" size="3 3 0.1" friction="0.8 0.01 0.001"/>',
                      f'<geom name="floor" type="plane" size="3 3 0.1" friction="{table_mu} 0.01 0.001"/>')
    return xml


class G(S.Sim3):
    def __init__(self, xml):
        self.m = mujoco.MjModel.from_xml_string(xml, getattr(H, "ASSETS", None) or None)   # текстуры и сетки мира — из памяти
        for g in range(self.m.ngeom):
            if self.m.geom_group[g] < 2:    # группа 2 — видимые детали из CAD (мир harvey_world), их не трогаем
                b = self.m.geom_bodyid[g]          # 1 — робот (всё, что растёт из корпуса), 0 — мир и предметы
                self.m.geom_group[g] = 1 if (b != 0 and self.m.body_rootid[b] == self.m.body('torso').id) else 0
        self.d = mujoco.MjData(self.m)
        names = [f"{n}_{j}" for n in H.MOUNTS for j in "cfk"] + H.ARM_JOINTS
        self.jid = {k: self.m.joint(k).qposadr[0] for k in names}
        self.vid = {k: self.m.joint(k).dofadr[0] for k in names}
        self.aid = {k: self.m.actuator(f"m_{k}").id for k in names}
        q = H.pose_targets(H.REACH_WORK, H.ZJ)
        for n, vals in q.items():
            for j, v in zip("cfk", vals): self.d.qpos[self.jid[f"{n}_{j}"]] = v
        self.arm_t = {n: self.tuck(n) for n in "LR"}
        for n in "LR":
            for j, v in zip("ype", H.arm_ik(n, self.arm_t[n])): self.d.qpos[self.jid[f"{n}_{j}"]] = v
        mujoco.mj_forward(self.m, self.d)
        self.kp, self.kd, self.kpa, self.kda, self.kp32, self.kd32 = 25.0, 0.3, 80.0, 0.6, 3.0, 0.05
        self.tscale, self.dead, self.lag, self.buf, self.noise = 1.0, set(), 0, [], 0.0
        self.rng = np.random.default_rng(0); self.tq = {}
        self.grip = {"L": -0.70, "R": -0.70}; self.glim = 0.44; self.arm_lim = None

    def step(self, q, arm=None, eye=0.0, armq=None):
        for n in "LR":   # захват: регулятор положения с ограничением момента (= ограничение тока STS3032)
            jq = self.m.joint(f"{n}_g"); e = self.grip[n] - self.d.qpos[jq.qposadr[0]]; w = self.d.qvel[jq.dofadr[0]]
            self.d.ctrl[self.m.actuator(f"m_{n}_g").id] = min(self.glim, max(-self.glim, float(4.0 * e - 0.02 * w)))
        if self.arm_lim:
            for n in "LR":
                for j in "pe": H.LIMITS[f"{n}_{j}"] = (self.arm_lim, H.W0)
        out = super().step(q, arm, eye, armq)
        if self.arm_lim:
            for n in "LR":
                for j in "pe": H.LIMITS[f"{n}_{j}"] = (H.TAU_STALL, H.W0)
        return out


def obj_forces(s, obj_geom, finger_geoms):
    m, d = s.m, s.d; gid = m.geom(obj_geom).id; fg = {m.geom(g).id for g in finger_geoms}; f = 0.0
    for i in range(d.ncon):
        c = d.contact[i]
        if (c.geom1 == gid and c.geom2 in fg) or (c.geom2 == gid and c.geom1 in fg):
            f6 = np.zeros(6); mujoco.mj_contactForce(m, d, i, f6); f += abs(f6[0])
    return f


def path(s, pts_by_time, hand="L"):
    """Список (точка, длительность) → движение кончика в пространстве суставов."""
    q = H.pose_targets(H.REACH_WORK, H.ZJ)
    if not hasattr(s, "armq_cur"):
        s.armq_cur = {n: np.array(H.arm_ik(n, s.arm_t[n])) for n in "LR"}
    cur = s.armq_cur      # продолжаем с того места, где клешни сейчас
    for pts, dur, grip in pts_by_time:
        tgt = {n: (np.array(H.arm_ik(n, pts[n])) if n in pts else cur[n]) for n in "LR"}
        st = {n: cur[n].copy() for n in "LR"}
        if grip is not None:
            for n in pts: s.grip[n] = grip
        steps = int(dur / DT)
        for i in range(steps):
            k = 0.5 - 0.5 * math.cos(math.pi * i / steps)
            s.step(q, None, 0.0, {n: st[n] + (tgt[n] - st[n]) * k for n in "LR"})
        cur = tgt
    s.armq_cur = cur
    return cur


def rel(s, body):
    tb = s.d.body("torso"); R = tb.xmat.reshape(3, 3)
    return R.T @ (s.d.body(body).xpos - tb.xpos)


# ---------------- 1. ручка одной клешнёй ----------------
def pen_test(glim, mu, slow=1.0):
    X, Y = 0.185, 0.030      # ручка лежит вдоль клешни; кончик — это концы отогнутых пальцев (как в CAD)
    TX = X
    pen = f'<body name="pen" pos="{X} {Y} 0.0046"><freejoint/><geom name="pen_g" type="capsule" fromto="-0.06 0 0 0.06 0 0" size="0.0045" mass="0.015" condim="6" friction="0.5 0.01 0.002" rgba=".1 .3 .8 1"/></body>'
    s = G(build(pen, mu=mu)); s.glim = glim
    Z = -(H.ZJ - 0.004)      # оси концов пальцев в 4 мм над столом (подбор: 4 мм — берёт, 6 мм — скользит по верху)
    fing = ["L_ffix", "L_fmovg"]
    path(s, [({"L": [0.205, Y, 0.020]}, 1.0 * slow, -0.70), ({"L": [TX, Y + 0.002, 0.0]}, 1.0 * slow, None),
             ({"L": [TX, Y + 0.002, Z + 0.012]}, 0.6 * slow, None), ({"L": [TX, Y + 0.002, Z]}, 0.6 * slow, None)])
    path(s, [({"L": [TX, Y + 0.002, Z]}, 0.8, 0.25)])                 # сжать
    grip_f = obj_forces(s, "pen_g", fing)
    path(s, [({"L": [0.205, Y, 0.060]}, 1.2 * slow, None)])
    lifted = rel(s, "pen")[2] > -0.02
    path(s, [({"L": [0.165, Y, 0.150]}, 1.5 * slow, None), ({"L": [0.110, Y, 0.175]}, 1.5 * slow, None),
             ({"L": [-0.008, Y, 0.168]}, 2.5 * slow, None), ({"L": [-0.008, Y, 0.088]}, 2.0 * slow, None)])
    held = bool(np.linalg.norm(rel(s, "pen") - rel(s, "L_tip")) < 0.03)
    path(s, [({"L": [-0.008, Y, 0.088]}, 0.6, -0.70), ({"L": [0.025, Y, 0.145]}, 1.0, None), ({"L": [0.165, Y, 0.150]}, 1.0, None), ({"L": s.tuck("L")}, 1.5, None)])
    on_back = rel(s, "pen")[2] > 0.055
    return dict(сила_сжатия_Н=round(grip_f, 1), поднял=bool(lifted), донёс=held, на_спине=bool(on_back))


# ---------------- 2. телефон двумя клешнями «в обхват» ----------------
def phone_test(glim, mu, phone_mu=0.5):
    ph = f'<body name="phone" pos="0.185 0 0.0045"><freejoint/><geom name="phone_g" type="box" size="0.0375 0.075 0.004" mass="0.2" friction="{phone_mu} 0.01 0.001" rgba=".1 .1 .12 1"/></body>'
    s = G(build(ph, mu=mu)); s.glim = glim
    Z = -(H.ZJ - 0.008)
    out = 0.092; inn = 0.066     # клешни подходят к коротким торцам и сжимают телефон с боков (стоя: поворот до 40°)
    fing = [f"{n}_{g}" for n in "LR" for g in ("ffix", "fmovg", "handg")]
    path(s, [({"L": [0.185, out, 0.0], "R": [0.185, -out, 0.0]}, 1.5, -0.2),
             ({"L": [0.185, out, Z], "R": [0.185, -out, Z]}, 1.0, None),
             ({"L": [0.185, inn, Z], "R": [0.185, -inn, Z]}, 1.0, None)])
    squeeze = obj_forces(s, "phone_g", fing)
    path(s, [({"L": [0.205, inn, 0.06], "R": [0.205, -inn, 0.06]}, 1.5, None)])
    lifted = rel(s, "phone")[2] > -0.02
    path(s, [({"L": [0.110, inn, 0.175], "R": [0.110, -inn, 0.175]}, 3.0, None),
             ({"L": [-0.005, inn, 0.168], "R": [-0.005, -inn, 0.168]}, 3.0, None),
             ({"L": [-0.005, inn, 0.092], "R": [-0.005, -inn, 0.092]}, 2.0, None)])
    held = rel(s, "phone")[2] > 0.06
    path(s, [({"L": [-0.005, out, 0.092], "R": [-0.005, -out, 0.092]}, 1.0, None),
             ({"L": [0.025, out, 0.145], "R": [0.025, -out, 0.145]}, 1.0, None), ({"L": s.tuck("L"), "R": s.tuck("R")}, 1.5, None)])
    on_back = rel(s, "phone")[2] > 0.055
    return dict(сжатие_с_боков_Н=round(squeeze, 1), поднял=bool(lifted), донёс=bool(held), на_спине=bool(on_back))


# ---------------- 3. безопасность: палец человека ----------------
FINGER = '<body name="human" pos="{x} {y} {z}"><geom name="human_g" type="capsule" fromto="0 0 -0.03 0 0 0.03" size="0.008" rgba="1 .8 .65 1" solref="0.01 1"/></body>'


def finger_mid(s):
    """Точка между концами пальцев левой клешни (там, где окажется палец человека)."""
    d, m = s.d, s.m
    def end(g):
        i = m.geom(g).id; c = d.geom_xpos[i]; R = d.geom_xmat[i].reshape(3, 3); h = m.geom_size[i][1]
        return c - R[:, 2] * h * 0.3
    return (end("L_ffix") + end("L_fmovg")) / 2


def pinch_test(glim):
    """Палец Ø16 мм между раскрытыми пальцами клешни; захват сжимается с ограничением момента."""
    X, Y = 0.194, 0.030; Z = -(H.ZJ - 0.035)
    s0 = G(build("")); path(s0, [({"L": [0.205, Y, 0.020]}, 1.0, -0.70), ({"L": [X, Y, Z]}, 1.0, None)])
    p = finger_mid(s0)
    s = G(build(FINGER.format(x=p[0], y=p[1], z=p[2]))); s.glim = glim
    path(s, [({"L": [0.205, Y, 0.020]}, 1.0, -0.70), ({"L": [X, Y, Z]}, 1.0, None)])
    before = obj_forces(s, "human_g", ["L_ffix", "L_fmovg", "L_handg"])
    s.grip["L"] = 0.25
    q = H.pose_targets(H.REACH_WORK, H.ZJ); peak = 0.0; last = 0.0
    for i in range(int(1.5 / DT)):
        s.step(q, None, 0.0, s.armq_cur)
        if i % 10 == 0:
            f = obj_forces(s, "human_g", ["L_ffix", "L_fmovg"]); peak = max(peak, f); last = f
    return dict(до_сжатия=round(before, 1), пик=round(peak, 1), удержание=round(last, 1))


def sweep_test(arm_lim, move_time=0.0):
    """Палец оказался на пути клешни, которая резко встаёт в позу «щит»."""
    SH = {"L": np.array([0.185, 0.030, 0.008]), "R": np.array([0.185, -0.030, 0.008])}
    s0 = G(build(""))
    # где пройдёт кончик левой клешни на середине движения (у клешни v2 локоть в «поджато» и «щите» почти на месте —
    # двигается кисть, её и проверяем)
    path(s0, [({"L": (s0.tuck("L") + SH["L"]) / 2}, 0.8, None)])
    p = s0.d.body("L_tip").xpos.copy() + np.array([0.012, 0, 0])          # кончик пальца человека чуть впереди пути кисти
    s = G(build(FINGER.format(x=p[0], y=p[1], z=p[2]).replace('fromto="0 0 -0.03 0 0 0.03"', 'fromto="0 0 -0.015 0 0 0.015"')))
    s.arm_lim = arm_lim
    q = H.pose_targets(H.REACH_WORK, H.ZJ); peak = 0.0
    tgt = {n: np.array(H.arm_ik(n, SH[n])) for n in "LR"}
    st = {n: np.array(H.arm_ik(n, s.tuck(n))) for n in "LR"}
    for i in range(int(2.0 / DT)):
        k = 1.0 if move_time == 0 else min(1.0, i * DT / move_time)
        s.step(q, None, 0.0, {n: st[n] + (tgt[n] - st[n]) * k for n in "LR"})
        if i % 10 == 0: peak = max(peak, obj_forces(s, "human_g", ["L_upg", "L_foreg", "L_handg", "L_ffix", "L_fmovg"]))
    return round(peak, 1)


if __name__ == "__main__":
    which = _sys.argv[1:] or ["pen", "phone", "pinch", "sweep"]
    res = {}
    if "pen" in which:
        for mu in (1.0, 0.5):
            for g in (0.03, 0.06, 0.12, 0.44):
                r = pen_test(g, mu); res[f"ручка, захват {g} Н·м, трение пальцев {mu}"] = r; print(f"ручка τ={g} μ={mu}:", r, flush=True)
    if "phone" in which:
        for mu in (1.0, 0.5):
            r = phone_test(0.2, mu); res[f"телефон, трение {mu}"] = r; print(f"телефон μ={mu}:", r, flush=True)
    if "pinch" in which:
        for g in (0.44, 0.12, 0.06):
            f = pinch_test(g); res[f"щипок пальца, захват {g} Н·м"] = f; print(f"щипок τ={g}: {f} Н", flush=True)
    if "sweep" in which:
        for lim in (None, 0.8, 0.4):
            f = sweep_test(lim); res[f"рука задевает палец, предел {lim or 'нет (2,94)'} Н·м"] = f; print(f"удар рукой, предел {lim}: {f} Н", flush=True)
    json.dump(res, open("grasp_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------- 4. присоска на левой клешне (телефон, бумага) ----------------
CUP = '''<body name="L_cup" pos="0.040 0 -0.016">
                <joint name="L_cupball" type="ball" damping="0.0005" stiffness="0.002"/>
                <geom name="L_cupg" type="cylinder" size="0.010 0.003" pos="0 0 -0.003" mass="0.008" friction="1.0 0.01 0.001" rgba=".9 .9 .95 1"/>
              </body>'''


def build_cup(obj, mu=1.0, force=8.0):
    xml = build(obj, mu=mu)
    tp = f'<body name="L_tip" pos="{H.TIP[0]} 0 {H.TIP[1]}">'
    xml = xml.replace(tp, CUP + tp, 1)
    xml = xml.replace('<actuator>', f'<actuator><adhesion name="suck" body="L_cup" ctrlrange="0 1" gain="{force}"/>', 1)
    return xml


def suction_test(force=8.0, x=0.185, y=0.030, rz=0.105, rx=-0.008):
    ph = '<body name="phone" pos="0.185 0 0.0045"><freejoint/><geom name="phone_g" type="box" size="0.0375 0.075 0.004" mass="0.2" friction="0.5 0.01 0.001" rgba=".1 .1 .12 1"/></body>'
    s = G(build_cup(ph, force=force)); a = s.m.actuator("suck").id
    cup = s.d.body("L_cup")
    # где окажется присоска, если кончик над точкой (x, y)
    Z0 = 0.0
    path(s, [({"L": [0.205, 0.03, 0.020]}, 1.0, -0.3), ({"L": [x + 0.012, y, Z0]}, 1.2, None)])
    # опускаем, пока присоска не коснётся телефона
    dz = (cup.xpos[2] - 0.0085) - 0.001
    path(s, [({"L": [x + 0.012, y, Z0 - dz]}, 1.0, None)])
    s.d.ctrl[a] = 1.0
    path(s, [({"L": [x + 0.012, y, Z0 - dz]}, 0.5, None), ({"L": [0.205, y, 0.060]}, 1.5, None)])
    lifted = rel(s, "phone")[2] > -0.02
    path(s, [({"L": [0.165, 0.03, 0.150]}, 1.5, None), ({"L": [0.110, 0.03, 0.175]}, 1.5, None), ({"L": [rx, y, 0.168]}, 3.0, None), ({"L": [rx, y, rz]}, 2.5, None)])
    held = rel(s, "phone")[2] > 0.06
    s.d.ctrl[a] = 0.0
    path(s, [({"L": [0.025, 0.03, 0.145]}, 1.0, None), ({"L": [0.165, 0.03, 0.150]}, 1.0, None), ({"L": s.tuck("L")}, 1.5, None)])
    on_back = rel(s, "phone")[2] > 0.055
    return dict(поднял=bool(lifted), донёс=bool(held), на_спине=bool(on_back), положение_мм=np.round(rel(s, "phone") * 1000).tolist())
