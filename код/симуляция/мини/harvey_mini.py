"""Харви «Компакт мини» — первая модель в MuJoCo: подходит ли размер и хватает ли приводов STS3032.

Все 28 приводов — STS3032 (23 × 12 × 27,5 мм, 20 г; пик 0,44 Н·м, номинал 0,147 Н·м, 0,09 с/60°):
6 ног × 3 сустава, 2 клешни × 4 сустава (поворот плеча, подъём, локоть, захват), 2 стебелька глаз.
Хвоста нет. Размеры — оценка до CAD: бедро 34 мм, голень 48 мм, корпус 95 × 80 × 40 мм.

    python harvey_mini.py           # все проверки, итог в mini_results.json
    python harvey_mini.py walk      # только ходьба (stand, walk, turn, pen, tip)
Проверки: стойка, ходьба трипод 6 см/с, разворот на месте, ручка (взять со стола, поднять, пронести шагом),
устойчивость с вытянутой клешнёй. Нагрузка — доля номинального и пикового момента STS3032."""
import math, sys, json, os
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco

# ---------------- приводы STS3032 ----------------
STALL, RATED = 0.44, 0.147                 # Н·м
W0 = math.radians(60) / 0.09               # рад/с без нагрузки

# ---------------- геометрия (м) ----------------
COX, FEM, TIB, FOOT_R = 0.025, 0.034, 0.048, 0.005
ZJ = TIB - FEM * math.sin(math.radians(20))           # оси бедра над столом в стойке: 36,4 мм
REACH = COX + FEM * math.cos(math.radians(20))        # 57 мм от оси поворота до стопы
MOUNTS = {"RF": (0.035, -0.035, -50), "RM": (0.0, -0.040, -90), "RB": (-0.035, -0.035, -130),
          "LF": (0.035, 0.035, 50), "LM": (0.0, 0.040, 90), "LB": (-0.035, 0.035, 130)}
TRIPOD_A = ("RF", "LM", "RB")
BODY = (0.0475, 0.040, 0.020)                          # полуразмеры корпуса; низ корпуса — на 12 мм ниже осей бедра
ARM_S = {"L": (0.050, 0.020, 0.024), "R": (0.050, -0.020, 0.024)}   # плечо клешни над осями бедра
A1, FORE, TIPX = 0.040, 0.030, 0.024                  # плечо, предплечье, кисть до середины губок
A2 = FORE + TIPX                                      # от локтя до губок: 54 мм
EYE = {"L": (0.030, 0.028, 0.022), "R": (0.030, -0.028, 0.022)}
DT = 0.0005

# ---------------- массы (кг) ----------------
SERVO = 0.020
M_COXA, M_FEM, M_TIB = SERVO + 0.004, SERVO + 0.004, 0.005            # звенья ног с приводами
M_UP, M_FORE, M_HAND = SERVO + 0.003, SERVO + 0.003, SERVO + 0.006     # клешня: подъём, локоть, захват
M_EYE = 0.008
TOTAL = 0.85                                                            # оценка всей массы (28 приводов = 0,56 кг)


def torso_mass(total):
    limbs = 6 * (M_COXA + M_FEM + M_TIB) + 2 * (M_UP + M_FORE + M_HAND) + 2 * M_EYE
    return total - limbs        # в корпусе: 6 приводов поворота ног, 2 — плеч, 2 — глаз, батарея, электроника, рама


def build_xml(total=TOTAL, pen=True):
    legs = ""
    for n, (x, y, yaw) in MOUNTS.items():
        legs += f"""
      <body name="{n}_coxa" pos="{x} {y} 0" euler="0 0 {yaw}">
        <joint name="{n}_c" axis="0 0 1" range="-55 55" armature="0.0015" damping="0.01"/>
        <geom type="box" size="0.012 0.008 0.008" pos="0.012 0 0" mass="{M_COXA}" rgba=".2 .2 .22 1" contype="2" conaffinity="0"/>
        <body name="{n}_femur" pos="{COX} 0 0">
          <joint name="{n}_f" axis="0 -1 0" range="-60 95" armature="0.0015" damping="0.01"/>
          <geom type="box" size="0.017 0.007 0.006" pos="0.017 0 0" mass="{M_FEM}" rgba=".9 .4 .2 1" contype="2" conaffinity="0"/>
          <body name="{n}_tibia" pos="{FEM} 0 0">
            <joint name="{n}_k" axis="0 -1 0" range="-130 30" armature="0.0015" damping="0.01"/>
            <geom type="capsule" fromto="0 0 0 {TIB - FOOT_R} 0 0" size="0.004" mass="{M_TIB}" rgba=".9 .4 .2 1" contype="2" conaffinity="0"/>
            <geom name="{n}_foot" type="sphere" pos="{TIB - FOOT_R} 0 0" size="{FOOT_R}" mass="0.001" friction="1.0 0.01 0.001" rgba=".1 .1 .1 1"/>
          </body>
        </body>
      </body>"""
    arms = ""
    for n, (x, y, z) in ARM_S.items():
        s = 1 if n == "L" else -1
        arms += f"""
      <body name="{n}_ay" pos="{x} {y} {z}">
        <joint name="{n}_y" axis="0 0 1" range="-40 70" armature="0.0015" damping="0.01"/>
        <geom type="cylinder" size="0.008 0.003" mass="0.003" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
        <body name="{n}_up">
          <joint name="{n}_p" axis="0 -1 0" range="-80 170" armature="0.0015" damping="0.01"/>
          <geom type="capsule" fromto="0.004 0 0 {A1} 0 0" size="0.006" mass="{M_UP}" rgba=".9 .4 .2 1"/>
          <body name="{n}_fore" pos="{A1} 0 0">
            <joint name="{n}_e" axis="0 -1 0" range="-140 120" armature="0.0015" damping="0.01"/>
            <geom type="capsule" fromto="0.004 0 0 {FORE - 0.004} 0 0" size="0.006" mass="{M_FORE}" rgba=".9 .4 .2 1"/>
            <body name="{n}_hand" pos="{FORE} 0 0">
              <geom name="{n}_jawfix" type="box" size="0.012 0.0025 0.004" pos="0.012 {0.006 * s} 0" mass="{M_HAND * 0.6}" friction="1.2 0.02 0.002" rgba=".1 .1 .1 1"/>
              <body name="{n}_jaw" pos="0.002 {-0.004 * s} 0">
                <joint name="{n}_g" axis="0 0 {s}" range="-55 12" armature="0.0005" damping="0.005"/>
                <geom name="{n}_jawmov" type="box" size="0.011 0.0025 0.004" pos="0.012 {-0.003 * s} 0" mass="{M_HAND * 0.4}" friction="1.2 0.02 0.002" rgba=".1 .1 .1 1"/>
              </body>
              <site name="{n}_tip" pos="{TIPX} 0 0" size="0.002"/>
            </body>
          </body>
        </body>
      </body>"""
    eyes = "".join(f"""
      <body name="{n}_eye" pos="{x} {y} {z}">
        <joint name="{n}_s" axis="{1 if n == 'L' else -1} 0 0" range="-90 20" armature="0.001" damping="0.005"/>
        <geom type="capsule" fromto="0 0 0 0 0 0.022" size="0.003" mass="{M_EYE * 0.4}" rgba=".3 .3 .33 1" contype="0" conaffinity="0"/>
        <geom type="cylinder" pos="0.004 0 0.032" euler="0 90 0" size="0.012 0.004" mass="{M_EYE * 0.6}" rgba=".1 .5 .6 1" contype="0" conaffinity="0"/>
      </body>""" for n, (x, y, z) in EYE.items())
    pen_xml = """
    <body name="pen" pos="0.122 0.020 0.0045"><freejoint/>
      <geom name="pen_g" type="capsule" fromto="-0.062 0 0 0.062 0 0" size="0.0045" mass="0.010" friction="0.8 0.01 0.002" condim="4" rgba=".1 .3 .8 1"/>
    </body>""" if pen else ""
    acts = "".join(f'<motor name="m_{j}" joint="{j}" ctrlrange="-{STALL} {STALL}"/>' for j in joint_names())
    return f"""<mujoco model="harvey_mini">
  <option timestep="{DT}" integrator="implicitfast"/>
  <default><joint type="hinge"/><geom contype="1" conaffinity="3"/></default>
  <worldbody>
    <light pos="0.2 -0.3 1" dir="-0.2 0.3 -1"/>
    <geom name="floor" type="plane" size="1 1 0.1" friction="0.8 0.01 0.001" rgba=".75 .62 .45 1"/>
    <body name="torso" pos="0 0 {ZJ + 0.003}">
      <freejoint/>
      <geom name="body" type="box" size="{BODY[0]} {BODY[1]} {BODY[2]}" pos="0 0 {BODY[2] - 0.012}" mass="{torso_mass(total):.4f}" rgba=".25 .26 .28 1" conaffinity="1"/>
      {arms}{eyes}{legs}
    </body>{pen_xml}
  </worldbody>
  <actuator>{acts}</actuator>
</mujoco>"""


def joint_names():
    return [f"{n}_{j}" for n in MOUNTS for j in "cfk"] + [f"{n}_{j}" for n in "LR" for j in "ypeg"] + ["L_s", "R_s"]


# ---------------- кинематика ----------------
def neutral(n, reach=REACH):
    x, y, yaw = MOUNTS[n]; a = math.radians(yaw)
    return np.array([x + reach * math.cos(a), y + reach * math.sin(a)])


def leg_ik(n, p, h):
    x, y, yaw = MOUNTS[n]; a = math.radians(yaw)
    dx, dy = p[0] - x, p[1] - y
    lx, ly = math.cos(a) * dx + math.sin(a) * dy, -math.sin(a) * dx + math.cos(a) * dy
    qc = math.atan2(ly, lx); rr = math.hypot(lx, ly) - COX; L2 = TIB - FOOT_R
    d = min(max(math.hypot(rr, h), abs(L2 - FEM) + 1e-4), FEM + L2 - 1e-4)
    qf = math.atan2(h, rr) + math.acos(max(-1, min(1, (FEM ** 2 + d ** 2 - L2 ** 2) / (2 * FEM * d))))
    qk = -(math.pi - math.acos(max(-1, min(1, (FEM ** 2 + L2 ** 2 - d ** 2) / (2 * FEM * L2)))))
    return qc, qf, qk


def arm_ik(n, p):
    """p — точка кончика пальцев в системе корпуса. Поворот плеча + плоская двухзвенная задача (локоть вверх)."""
    x, y, z = ARM_S[n]
    dx, dy, dz = p[0] - x, p[1] - y, p[2] - z
    qy = math.atan2(dy, dx); r = math.hypot(dx, dy)
    d = min(math.hypot(r, dz), A1 + A2 - 1e-4)
    qe = -math.acos(max(-1, min(1, (A1 ** 2 + A2 ** 2 - d ** 2) / (2 * A1 * A2)))) + math.pi
    qp = math.atan2(dz, r) + math.acos(max(-1, min(1, (A1 ** 2 + d ** 2 - A2 ** 2) / (2 * A1 * d))))
    return qy, qp, -qe


# ---------------- симуляция ----------------
class Mini:
    def __init__(self, total=TOTAL, pen=True):
        self.m = mujoco.MjModel.from_xml_string(build_xml(total, pen)); self.d = mujoco.MjData(self.m)
        self.j = {k: (self.m.joint(k).qposadr[0], self.m.joint(k).dofadr[0], self.m.actuator(f"m_{k}").id) for k in joint_names()}
        self.kp = {"c": 3.0, "f": 4.0, "k": 4.0, "y": 2.0, "p": 3.0, "e": 3.0, "g": 1.0, "s": 1.0}
        self.kd = 0.03
        self.grip_lim = 0.15                       # ограничение момента захвата (ток), Н·м
        self.q = {k: 0.0 for k in self.j}
        self.tq = {k: [] for k in self.j}
        st = self.stand_q(); self.q.update(st)
        for k, v in st.items(): self.d.qpos[self.j[k][0]] = v
        for n in "LR":
            a = arm_ik(n, self.tuck(n))
            for jj, v in zip("ype", a): self.q[f"{n}_{jj}"] = v; self.d.qpos[self.j[f"{n}_{jj}"][0]] = v
        mujoco.mj_forward(self.m, self.d)

    @staticmethod
    def tuck(n):
        return np.array([0.075, ARM_S[n][1], 0.010])

    def stand_q(self, h=None):
        h = -(ZJ - FOOT_R) if h is None else h
        out = {}
        for n in MOUNTS:
            for jj, v in zip("cfk", leg_ik(n, neutral(n), h)): out[f"{n}_{jj}"] = v
        return out

    def step(self, record=True):
        d = self.d
        for k, (qa, va, aid) in self.j.items():
            e = self.q[k] - d.qpos[qa]; w = d.qvel[va]; t = k[-1]
            tau = self.kp[t] * e - self.kd * w
            lim = self.grip_lim if t == "g" else STALL
            if (tau > 0) == (w > 0) and tau and w: lim = min(lim, STALL * max(0.0, 1 - abs(w) / W0))
            tau = min(lim, max(-lim, tau)); d.ctrl[aid] = tau
            if record: self.tq[k].append(abs(tau))
        mujoco.mj_step(self.m, d)

    def run(self, sec, fn=None, record=True):
        for i in range(int(sec / DT)):
            if fn: fn(i * DT)
            self.step(record)

    def tilt(self):
        R = self.d.body("torso").xmat.reshape(3, 3); return math.degrees(math.acos(max(-1, min(1, R[2, 2]))))

    def load(self, keys):
        """Средняя и пиковая (99-й перцентиль) нагрузка группы суставов, % номинала."""
        v = np.concatenate([np.array(self.tq[k]) for k in keys if self.tq[k]]) if keys else np.zeros(1)
        return {"средняя_%ном": round(float(v.mean() / RATED * 100)), "пик_%ном": round(float(np.percentile(v, 99) / RATED * 100)),
                "пик_%предела": round(float(np.percentile(v, 99) / STALL * 100))}

    def reset_load(self):
        self.tq = {k: [] for k in self.j}

    def gait(self, vx=0.06, wz=0.0, t_half=0.30, lift=0.015):
        h0 = -(ZJ - FOOT_R)
        def fn(t):
            ph = (t / (2 * t_half)) % 1.0
            for n in MOUNTS:
                p0 = neutral(n); pp = ph if n in TRIPOD_A else (ph + 0.5) % 1.0
                if pp < 0.5: u = 0.5 - 2 * pp; z = 0.0
                else:
                    s = (pp - 0.5) * 2; u = -0.5 + (s - math.sin(2 * math.pi * s) / (2 * math.pi)); z = lift * math.sin(math.pi * s)
                a = wz * t_half * u; c, sn = math.cos(a), math.sin(a)
                p = np.array([c * p0[0] - sn * p0[1], sn * p0[0] + c * p0[1]]) + np.array([vx * t_half * u, 0])
                for jj, v in zip("cfk", leg_ik(n, p, h0 + z)): self.q[f"{n}_{jj}"] = v
        return fn


LEGS_F = [f"{n}_f" for n in MOUNTS]; LEGS_K = [f"{n}_k" for n in MOUNTS]; LEGS_C = [f"{n}_c" for n in MOUNTS]


def test_stand_walk(total):
    s = Mini(total, pen=False); s.run(1.0, record=False); s.reset_load(); s.run(2.0)
    stand = {"бедро": s.load(LEGS_F), "колено": s.load(LEGS_K), "наклон": round(s.tilt(), 1),
             "высота_корпуса_мм": round(float(s.d.body("torso").xpos[2] - 0.012) * 1000)}
    x0 = s.d.body("torso").xpos.copy(); s.reset_load(); mx = 0
    fn = s.gait(0.06)
    for i in range(int(8.0 / DT)):
        fn(i * DT); s.step(); mx = max(mx, s.tilt()) if i % 100 == 0 else mx
    x1 = s.d.body("torso").xpos
    walk = {"скорость_см_с": round(float(x1[0] - x0[0]) / 8 * 100, 1), "увод_мм": round(float(x1[1] - x0[1]) * 1000),
            "наклон_макс": round(mx, 1), "на_ногах": bool(s.tilt() < 30), "бедро": s.load(LEGS_F), "колено": s.load(LEGS_K),
            "поворот_ноги": s.load(LEGS_C)}
    s2 = Mini(total, pen=False); s2.run(0.5, record=False)
    R0 = s2.d.body("torso").xquat.copy(); fn = s2.gait(0.0, wz=0.8); s2.run(4.0, fn)
    yaw = lambda q: math.degrees(math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2)))
    turn = {"градусов_в_с": round((yaw(s2.d.body("torso").xquat) - yaw(R0)) / 4, 1), "на_ногах": bool(s2.tilt() < 30)}
    return {"стойка": stand, "ходьба_6см_с": walk, "разворот": turn}


def test_pen(total):
    """Левая клешня: подвести к ручке, сжать, поднять на 50 мм, пронести 2 с шагом вперёд, подать вперёд-вверх."""
    s = Mini(total, pen=True); s.run(0.8, record=False)
    tb = s.d.body("torso")
    def to_body(pw):
        R = tb.xmat.reshape(3, 3); return R.T @ (np.array(pw) - tb.xpos)
    pen = s.d.body("pen").xpos.copy()
    over = to_body(pen + [0, 0, 0.030]); at = to_body(pen + [0, 0, 0.0005])
    def move(a, b, sec, grip=None):
        st = s.q.copy()
        def fn(t):
            k = min(1.0, t / sec); k = 0.5 - 0.5 * math.cos(math.pi * k); p = a + (b - a) * k
            for jj, v in zip("ype", arm_ik("L", p)): s.q[f"L_{jj}"] = v
            if grip is not None: s.q["L_g"] = grip
        s.run(sec, fn)
    tuck = Mini.tuck("L")
    s.q["L_g"] = math.radians(-50); s.run(0.3)
    crouch = s.stand_q(-(ZJ - FOOT_R) + 0.012)                     # присесть на 12 мм — клешня достаёт до стола
    st = {k: s.q[k] for k in crouch}
    s.run(0.6, lambda t: s.q.update({k: st[k] + (crouch[k] - st[k]) * min(1, t / 0.6) for k in crouch}))
    pen = s.d.body("pen").xpos.copy()
    over = to_body(pen + [0, 0, 0.030]); at = to_body(pen + [0, 0, 0.001])
    s.reset_load()
    move(tuck, over, 1.0); move(over, at, 0.8)
    s.q["L_g"] = 0.3; s.run(0.6)                                    # сжать: момент ограничен grip_lim
    stand = s.stand_q(); st = {k: s.q[k] for k in stand}
    s.run(0.6, lambda t: s.q.update({k: st[k] + (stand[k] - st[k]) * min(1, t / 0.6) for k in stand}))   # встать
    lifted = to_body(pen + [0, 0, 0.050]); move(at, lifted, 1.0)
    held_lift = float(s.d.body("pen").xpos[2] - pen[2])
    fn = s.gait(0.05); s.run(2.0, fn)                              # пронести шагом
    give = np.array([0.105, 0.020, 0.070]); move(lifted, give, 1.0) # подать вперёд-вверх
    s.run(1.0)
    pz = float(s.d.body("pen").xpos[2] - pen[2])
    tip = s.d.site("L_tip").xpos; dist = float(np.linalg.norm(s.d.body("pen").xpos - tip))
    arm = {k: s.load([f"L_{k}"]) for k in "ype"}
    return {"поднята_на_мм": round(held_lift * 1000), "после_шагов_и_подачи_над_столом_мм": round(pz * 1000),
            "в_пальцах": bool(dist < 0.03 and pz > 0.02), "наклон_корпуса": round(s.tilt(), 1),
            "нагрузка_клешни": {"поворот": arm["y"], "подъём": arm["p"], "локоть": arm["e"]}, "на_ногах": bool(s.tilt() < 30)}


def test_tip(total):
    """Обе клешни вытянуты вперёд-вниз до упора — не клюёт ли носом."""
    s = Mini(total, pen=False); s.run(0.5, record=False)
    for n in "LR":
        for jj, v in zip("ype", arm_ik(n, np.array([ARM_S[n][0] + A1 + A2 - 0.003, ARM_S[n][1], ARM_S[n][2]]))): s.q[f"{n}_{jj}"] = v
    s.reset_load(); s.run(1.5)
    return {"наклон": round(s.tilt(), 1), "плечо_подъём": s.load(["L_p", "R_p"]), "передние_колени": s.load(["LF_k", "RF_k"])}


if __name__ == "__main__":
    which = sys.argv[1:] or ["walk", "pen", "tip"]
    res = {}
    for total in (0.75, 0.85, 0.95):
        r = {}
        if "walk" in which: r.update(test_stand_walk(total))
        if "pen" in which: r["ручка"] = test_pen(total)
        if "tip" in which: r["клешни_вперёд"] = test_tip(total)
        res[f"масса {total} кг"] = r
        print(f"=== масса {total} кг", flush=True)
        for k, v in r.items(): print(f"  {k}: {v}", flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mini_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
