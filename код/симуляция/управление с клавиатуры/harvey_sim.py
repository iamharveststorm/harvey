"""Физическая проверка робота Харви «Компакт» v2 (клешни 5 суставов) в MuJoCo.

Модель: корпус 150×140×70 мм, 6 ног (основание 40 мм, бедро 45, голень 70),
сервоприводы STS3215 (12 В): пик 2,94 Н·м, номинал 0,98 Н·м,
скорость без нагрузки 60° за 0,222 с, редуктор 1:345.
Запуск: pip install mujoco numpy; python harvey_sim.py
"""
import math, sys
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco

# ---------------- параметры ----------------
COX, FEM, TIB = 0.040, 0.051, 0.070
ZJ = TIB - FEM * math.sin(math.radians(20))   # высота осей бедра в рабочей стойке (бедро +20°, голень вертикально)
FOOT_R = 0.0075
TAU_STALL, TAU_RATED = 2.94, 0.98  # Н·м
W0 = math.radians(60) / 0.222      # рад/с без нагрузки
KT = TAU_STALL / 2.7               # Н·м/А по выходному валу
MOUNTS = {  # имя: (x вперёд, y влево, yaw ноги, градусы)
    "RF": (0.055, -0.058, -50), "RM": (0.0, -0.066, -90), "RB": (-0.055, -0.058, -130),
    "LF": (0.055, 0.058, 50),  "LM": (0.0, 0.066, 90),  "LB": (-0.055, 0.058, 130),
}
TRIPOD_A, TRIPOD_B = ("RF", "LM", "RB"), ("LF", "RM", "LB")
# клешни: поворот плеча (STS3032), подъём плеча и локоть (STS3215), вращение запястья и захват (STS3032)
ARM_S = {"L": (0.105, 0.030, 0.065), "R": (0.105, -0.030, 0.065)}   # плечо в системе корпуса (компоновка v2: впереди передних ног)
TIP = (0.0416, -0.0175)          # кончик пальцев в системе кисти: вперёд 41,6, вниз 17,5 мм (пальцы отогнуты, как в CAD)
A1 = 0.054                       # плечо 54 мм — как в модели клешни (модели/клешни)
A2 = math.hypot(0.060 + TIP[0], TIP[1])     # от локтя до кончика: 103,1 мм
TIP_DELTA = math.atan2(TIP[1], 0.060 + TIP[0])   # кончик ниже линии предплечья на 9,8°
TAU32_STALL, TAU32_RATED = 0.44, 0.147
W32 = math.radians(60) / 0.09
REACH_WORK = COX + FEM * math.cos(math.radians(20))   # 82,3 мм: тибия вертикально
REACH_REST = 0.0874               # покой «на корточках»: стопы на месте, колено −125° (сильнее не складывается)
ZJ_REST = 0.032


def arm_xml(n, s):
    x, y, z = ARM_S[n]
    return f"""
      <body name="{n}_ay" pos="{x} {y} {z}">
        <joint name="{n}_y" type="hinge" axis="0 0 1" range="-70 70" armature="0.002" damping="0.02"/>
        <geom type="box" size="0.006 0.0116 0.014" mass="0.020" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
        <body name="{n}_up">
          <joint name="{n}_p" type="hinge" axis="0 -1 0" range="-15 175" armature="0.01" damping="0.05"/>
          <geom type="box" size="0.0226 0.0124 0.0175" pos="0.012 0 0" mass="0.055" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
          <geom name="{n}_upg" type="capsule" fromto="0.02 0 0 {A1} 0 0" size="0.008" mass="0.010" rgba=".85 .4 .25 1"/>
          <body name="{n}_fore" pos="{A1} 0 0">
            <joint name="{n}_e" type="hinge" axis="0 -1 0" range="-105 130" armature="0.01" damping="0.05"/>
            <geom name="{n}_foreg" type="capsule" fromto="0.012 0 0 0.060 0 0" size="0.008" mass="0.072" rgba=".85 .4 .25 1"/>
            <body name="{n}_hand" pos="0.060 0 0">
              <joint name="{n}_r" type="hinge" axis="1 0 0" range="-90 90" armature="0.002" damping="0.02"/>
              <geom name="{n}_handg" type="capsule" fromto="0.006 0 0 0.030 0 -0.009" size="0.009" mass="0.055" rgba=".85 .4 .25 1"/>
              <body name="{n}_tip" pos="{TIP[0]} 0 {TIP[1]}"><geom type="sphere" size="0.003" mass="0.001" contype="0" conaffinity="0"/></body>
            </body>
          </body>
        </body>
      </body>"""


EYE_PIVOT = (0.070, 0.080, 0.076)   # глаза-стебельки на передних углах (компоновка v2), ось наклона — вдоль x


def eye_xml(n, s):
    """Крен стебелька: 0 — вверх, + внутрь (до 20°), − наружу: −75° — сложен (ходьба), −105° — только при перевороте
    (ноги в стойке): дисплей уходит ниже арки хвоста, Харви лежит на хвосте, а не на глазах."""
    x, y, z = EYE_PIVOT
    return f"""
      <geom name="{n}_eyeservo" type="box" size="0.0185 0.0065 0.0115" pos="{x - 0.0185} {s*y} {z + 0.0058}" mass="0.020" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
      <body name="{n}_eye" pos="{x} {s*y} {z}">
        <joint name="{n}_s" type="hinge" axis="{s} 0 0" range="-105 20" armature="0.002" damping="0.02"/>
        <geom name="{n}_stalk" type="capsule" fromto="0.006 0 0 0.008 0 0.038" size="0.0055" mass="0.012" rgba=".3 .33 .36 1"/>
        <geom name="{n}_disp" type="cylinder" pos="0.017 0 0.060" euler="0 90 0" size="0.026 0.0075" mass="0.022" rgba=".1 .1 .12 1"/>
      </body>"""


def build_xml(payload=0.5, body_mass=1.18, claw_mass=0.0, obj=None):
    legs = []
    for n, (x, y, yaw) in MOUNTS.items():
        legs.append(f"""
      <body name="{n}_coxa" pos="{x} {y} 0" euler="0 0 {yaw}">
        <joint name="{n}_c" type="hinge" axis="0 0 1" range="-60 60" armature="0.01" damping="0.05"/>
        <geom name="{n}_coxag" type="box" size="0.022 0.015 0.012" pos="0.03 0 0" mass="0.065" rgba=".2 .2 .22 1" contype="2" conaffinity="0"/>
        <body name="{n}_femur" pos="{COX} 0 0">
          <joint name="{n}_f" type="hinge" axis="0 -1 0" range="-60 {90 if n[1] == 'F' else 100}" armature="0.01" damping="0.05"/>
          <geom name="{n}_femg" type="box" size="0.0225 0.017 0.009" pos="0.0225 0 0" mass="0.063" rgba=".85 .4 .25 1" contype="2" conaffinity="0"/>
          <body name="{n}_tibia" pos="{FEM} 0 0">
            <joint name="{n}_k" type="hinge" axis="0 -1 0" range="-130 30" armature="0.01" damping="0.05"/>
            <geom name="{n}_tibg" type="capsule" fromto="0 0 0 {TIB - FOOT_R} 0 0" size="0.007" mass="0.012" rgba=".85 .4 .25 1" contype="2" conaffinity="0"/>
            <geom name="{n}_foot" type="sphere" pos="{TIB - FOOT_R} 0 0" size="{FOOT_R}" mass="0.003" friction="1.0 0.01 0.001" rgba=".15 .15 .15 1"/>
          </body>
        </body>
      </body>""")
    payload_xml = "" if payload <= 0 else f"""
    <body name="payload" pos="-0.02 0 {ZJ + 0.070 + 0.02}">
      <freejoint/>
      <geom type="box" size="0.03 0.025 0.02" mass="{payload}" friction="0.6 0.01 0.001" rgba=".3 .5 .8 1"/>
    </body>"""
    act = "".join(f'<motor name="m_{n}_{j}" joint="{n}_{j}" ctrlrange="-{TAU_STALL} {TAU_STALL}"/>'
                  for n in MOUNTS for j in "cfk")
    act += "".join(f'<motor name="m_{n}_{j}" joint="{n}_{j}" ctrlrange="-{TAU_STALL} {TAU_STALL}"/>' for n in "LR" for j in "pe")
    act += "".join(f'<motor name="m_{n}_{j}" joint="{n}_{j}" ctrlrange="-{TAU32_STALL} {TAU32_STALL}"/>' for n in "LR" for j in "yr")
    act += "".join(f'<motor name="m_{n}_s" joint="{n}_s" ctrlrange="-{TAU32_STALL} {TAU32_STALL}"/>' for n in "LR")
    eq = ""
    if obj:
        eq = '<equality><weld name="gL" body1="L_tip" body2="obj" active="false"/><weld name="gR" body1="R_tip" body2="obj" active="false"/></equality>'
        eq += '<contact><exclude body1="obj" body2="L_hand"/><exclude body1="obj" body2="R_hand"/><exclude body1="obj" body2="L_fore"/><exclude body1="obj" body2="R_fore"/></contact>'
    act = act + "</actuator>" + eq + "<actuator>"
    return f"""<mujoco model="harvey">
  <option timestep="0.0005" integrator="implicitfast"/>
  <!-- столкновения: мир, предметы, клешни, хвост, глаза — тип 1, сродство 1|2; звенья ног — тип 2 (сталкиваются с миром,
       предметами, клешнями и хвостом, но не друг с другом и не с корпусом); корпус — сродство 1 (ноги его не трогают) -->
  <default><geom contype="1" conaffinity="3"/></default>
  <worldbody>
    <light pos="0 0 1"/>
    <geom name="floor" type="plane" size="3 3 0.1" friction="0.8 0.01 0.001"/>
    <body name="torso" pos="0 0 {ZJ + 0.002}">
      <freejoint/>
      <!-- рама v2 (модели/корпус): ядро с приводами ног и электроникой, передняя палуба, узел хвоста, поднос -->
      <geom name="shell" type="box" size="0.045 0.050 0.035" pos="0 0 0.021" mass="{body_mass * 0.80:.4f}" rgba=".25 .26 .28 1" conaffinity="1"/>
      <geom name="deck" type="box" size="0.0395 0.036 0.017" pos="0.0885 0 0.003" mass="{body_mass * 0.12:.4f}" rgba=".25 .26 .28 1" conaffinity="1"/>
      <geom name="tailmount" type="box" size="0.024 0.024 0.0205" pos="-0.080 0 0.0065" mass="{body_mass * 0.06:.4f}" rgba=".25 .26 .28 1" conaffinity="1"/>
      <geom name="camera" type="box" size="0.013 0.0125 0.015" pos="0.067 0 0.038" mass="0.025" contype="0" conaffinity="0" rgba=".1 .1 .1 1"/>
      <geom name="tray" type="box" size="0.0435 0.0525 0.001" pos="-0.0085 0 0.065" mass="0.030" friction="0.9 0.01 0.001" rgba=".9 .45 .2 1" conaffinity="1"/>
      <geom name="rim_b" type="box" size="0.002 0.0525 0.002" pos="-0.050 0 0.068" mass="0.003" conaffinity="1"/>
      <geom name="rim_f" type="box" size="0.0015 0.0525 0.0015" pos="0.0335 0 0.0675" mass="0.003" conaffinity="1"/>
      <geom name="rim_l" type="box" size="0.0435 0.001 0.0015" pos="-0.0085 0.0515 0.0675" mass="0.003" conaffinity="1"/>
      <geom name="rim_r" type="box" size="0.0435 0.001 0.0015" pos="-0.0085 -0.0515 0.0675" mass="0.003" conaffinity="1"/>
      {arm_xml("L", 1)}{arm_xml("R", -1)}{eye_xml("L", 1)}{eye_xml("R", -1)}
      {''.join(legs)}
    </body>{payload_xml}{obj or ""}
  </worldbody>
  <actuator>{act}</actuator>
</mujoco>"""


# ---------------- кинематика ----------------
def neutral(name, reach):
    x, y, yaw = MOUNTS[name]
    a = math.radians(yaw)
    return np.array([x + (reach) * math.cos(a), y + (reach) * math.sin(a)])


def ik(name, foot_xy, h):
    """foot_xy в системе корпуса, h — высота стопы относительно осей бедра (<0)."""
    x, y, yaw = MOUNTS[name]
    a = math.radians(yaw)
    dx, dy = foot_xy[0] - x, foot_xy[1] - y
    lx = math.cos(a) * dx + math.sin(a) * dy      # вдоль ноги
    ly = -math.sin(a) * dx + math.cos(a) * dy     # поперёк
    qc = math.atan2(ly, lx)
    rr = math.hypot(lx, ly) - COX
    hz = h + FOOT_R * 0  # центр сферы стопы
    L2 = TIB - FOOT_R
    d = min(max(math.hypot(rr, hz), abs(L2 - FEM) + 1e-4), FEM + L2 - 1e-4)
    qf = math.atan2(hz, rr) + math.acos(max(-1.0, min(1.0, (FEM**2 + d**2 - L2**2) / (2 * FEM * d))))
    gam = math.acos(max(-1.0, min(1.0, (FEM**2 + L2**2 - d**2) / (2 * FEM * L2))))
    qk = -(math.pi - gam)
    # joint convention: femur axis (0,-1,0) => +up; same for knee
    return qc, qf, qk


def pose_targets(reach, zj, phase=None, stroke=0.0, lift=0.025, turn=0.0):
    q = {}
    for n in MOUNTS:
        p0 = neutral(n, reach)
        h = -(zj - FOOT_R)
        if phase is not None:
            ph = phase if n in TRIPOD_A else (phase + 0.5) % 1.0
            if ph < 0.5:   # опора: стопа едет назад
                u = 0.5 - 2 * ph            # +0.5 .. -0.5
                z = 0.0
            else:          # перенос
                s = (ph - 0.5) * 2
                u = -0.5 + (s - math.sin(2 * math.pi * s) / (2 * math.pi))
                z = lift * math.sin(math.pi * s)
            if turn:
                ang = -turn * u * 2 * 0.5 * -1
                c, s_ = math.cos(ang), math.sin(ang)
                p = np.array([c * p0[0] - s_ * p0[1], s_ * p0[0] + c * p0[1]])
            else:
                p = p0 + np.array([stroke * u, 0.0])
            h = h + z
        else:
            p = p0
        q[n] = ik(n, p, h)
    return q


# ---------------- симуляция ----------------
class Sim:
    def __init__(self, payload=0.5):
        self.m = mujoco.MjModel.from_xml_string(build_xml(payload))
        self.d = mujoco.MjData(self.m)
        self.jid = {f"{n}_{j}": self.m.joint(f"{n}_{j}").qposadr[0] for n in MOUNTS for j in "cfk"}
        self.vid = {f"{n}_{j}": self.m.joint(f"{n}_{j}").dofadr[0] for n in MOUNTS for j in "cfk"}
        self.aid = {f"{n}_{j}": self.m.actuator(f"m_{n}_{j}").id for n in MOUNTS for j in "cfk"}
        q = pose_targets(REACH_WORK, ZJ)
        for n, (qc, qf, qk) in q.items():
            for j, v in zip("cfk", (qc, qf, qk)):
                self.d.qpos[self.jid[f"{n}_{j}"]] = v
        mujoco.mj_forward(self.m, self.d)
        self.kp, self.kd = 25.0, 0.3
        self.log = []

    def step(self, q):
        d = self.d
        torques = {}
        for n, vals in q.items():
            for j, qd in zip("cfk", vals):
                k = f"{n}_{j}"
                e = qd - d.qpos[self.jid[k]]
                w = d.qvel[self.vid[k]]
                tau = self.kp * e - self.kd * w
                lim = TAU_STALL * max(0.0, 1 - abs(w) / W0) if np.sign(tau) == np.sign(w) else TAU_STALL
                tau = float(np.clip(tau, -lim, lim))
                d.ctrl[self.aid[k]] = tau
                torques[k] = (tau, w)
        mujoco.mj_step(self.m, d)
        return torques

    def torso(self):
        b = self.d.body("torso")
        return b.xpos.copy(), b.xquat.copy()

    def com_margin(self):
        """Расстояние проекции центра масс до края опорного многоугольника (м)."""
        com = self.d.subtree_com[0][:2]
        pts = []
        for n in MOUNTS:
            g = self.m.geom(f"{n}_foot").id
            if self.d.geom_xpos[g][2] < FOOT_R + 0.003:
                pts.append(self.d.geom_xpos[g][:2].copy())
        if len(pts) < 3:
            return -1.0
        pts = np.array(pts)
        c = pts.mean(0)
        pts = pts[np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))]
        md = 1e9
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            e = b - a
            nrm = np.array([e[1], -e[0]]) / np.linalg.norm(e)
            dist = np.dot(com - a, nrm)
            md = min(md, -dist)
        return md


def rpy(qt):
    w, x, y, z = qt
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = math.asin(max(-1, min(1, 2 * (w * y - z * x))))
    return math.degrees(roll), math.degrees(pitch)


def power(torques):
    """Оценка электрической мощности приводов, Вт (12 В)."""
    I = sum(0.03 + abs(t) / KT + 0.15 * abs(w) / W0 for t, w in torques.values())
    return 12.0 * I


def run_stand(payload):
    s = Sim(payload)
    q = pose_targets(REACH_WORK, ZJ)
    T = []
    for i in range(int(3.0 / s.m.opt.timestep)):
        tq = s.step(q)
        if i * s.m.opt.timestep > 2.0:
            T.append(tq)
    mx = {j: max(abs(t[f"{n}_{j}"][0]) for t in T for n in MOUNTS) for j in "cfk"}
    pos, _ = s.torso()
    return mx, pos[2], s.com_margin(), np.mean([power(t) for t in T])


def run_sit_stand(payload):
    s = Sim(payload)
    dt = s.m.opt.timestep
    peak = {j: 0.0 for j in "cfk"}
    seq = [(0, 1.0, "hold"), (1.0, 2.0, "down"), (2.0, 3.0, "hold_r"), (3.0, 4.0, "up"), (4.0, 5.0, "hold")]
    t = 0.0
    while t < 5.0:
        for a, b, mode in seq:
            if a <= t < b:
                k = (t - a) / (b - a)
                k = 0.5 - 0.5 * math.cos(math.pi * k)
                if mode == "hold": u = 0.0
                elif mode == "down": u = k
                elif mode == "hold_r": u = 1.0
                else: u = 1 - k
        reach = REACH_WORK + (REACH_REST - REACH_WORK) * u
        zj = ZJ + (ZJ_REST - ZJ) * u
        tq = s.step(pose_targets(reach, zj))
        for n in MOUNTS:
            for j in "cfk":
                peak[j] = max(peak[j], abs(tq[f"{n}_{j}"][0]))
        t += dt
    pos, _ = s.torso()
    return peak, pos[2]


def run_walk2(payload, t_half, **kw):
    return run_walk(payload, t_half, sim_cls=Sim2, **kw)


def run_walk(payload, t_half, stroke=0.056, turn=0.0, seconds=8.0, sim_cls=None):
    s = (sim_cls or Sim)(payload)
    dt = s.m.opt.timestep
    period = 2 * t_half
    # плавный разгон 1 с
    p0, q0 = s.torso()
    margins, rolls, pitches, pw, peak, rms = [], [], [], [], {j: 0 for j in "cfk"}, {j: [] for j in "cfk"}
    yaw_acc, yaw_prev = 0.0, None
    yaw0 = None
    n_steps = int(seconds / dt)
    start_x = None
    for i in range(n_steps):
        t = i * dt
        ramp = min(1.0, t / 1.0)
        ph = (t / period) % 1.0
        q = pose_targets(REACH_WORK, ZJ, phase=ph, stroke=stroke * ramp, turn=turn * ramp)
        tq = s.step(q)
        if t > 2.0:
            pos, qt = s.torso()
            if start_x is None:
                start_x, t_start, quat_start = pos.copy(), t, qt.copy()
            r, p = rpy(qt); rolls.append(abs(r)); pitches.append(abs(p))
            yw = math.degrees(math.atan2(2*(qt[0]*qt[3]+qt[1]*qt[2]), 1-2*(qt[2]**2+qt[3]**2)))
            if yaw_prev is not None: yaw_acc += (yw - yaw_prev + 540) % 360 - 180
            yaw_prev = yw
            pw.append(power(tq))
            for n in MOUNTS:
                for j in "cfk":
                    v = abs(tq[f"{n}_{j}"][0]); peak[j] = max(peak[j], v); rms[j].append(v)
            if i % 20 == 0:
                margins.append(s.com_margin())
    pos, qt = s.torso()
    dist = pos[:2] - start_x[:2]
    speed = np.linalg.norm(dist) / (seconds - t_start)
    # курс
    def yaw(q): return math.degrees(math.atan2(2*(q[0]*q[3]+q[1]*q[2]), 1-2*(q[2]**2+q[3]**2)))
    dyaw = yaw_acc
    payload_ok = True
    if payload > 0:
        pz = s.d.body("payload").xpos[2]
        payload_ok = pz > pos[2] + 0.05
    return dict(speed=speed * 100, yaw_rate=dyaw / (seconds - t_start), peak=peak,
                rms={j: float(np.sqrt(np.mean(np.square(v)))) for j, v in rms.items()},
                over={j: 100.0 * float(np.mean(np.array(v) > TAU_RATED)) for j, v in rms.items()},
                roll=max(rolls), pitch=max(pitches), margin=min(margins) * 1000,
                power=float(np.mean(pw)), payload_ok=payload_ok, height=pos[2])



# ---------------- клешни ----------------
def arm_ik(n, t, branch=None):
    """t — точка кончика клешни в системе корпуса; запястье прямое.
    Ниже плеча — «локоть вверх», выше и за спину — «локоть вперёд» (рука не ложится на панцирь)."""
    sx, sy, sz = ARM_S[n]
    dx, dy, dz = t[0] - sx, t[1] - sy, t[2] - sz
    if dx >= 0:
        yaw = math.atan2(dy, dx); r = math.hypot(dx, dy)
    else:                          # тянемся назад через верх: поворот небольшой, подъём больше 90°
        yaw = math.atan2(-dy, -dx); r = -math.hypot(dx, dy)
    d = min(math.hypot(r, dz), A1 + A2 - 1e-4)
    up = (dz < 0 or r > 0) if branch is None else branch == "up"     # впереди плеча — «локоть вверх» (как в модели клешни)
    a = math.acos(max(-1, min(1, (A1**2 + d**2 - A2**2) / (2 * A1 * d))))
    gam = math.acos(max(-1, min(1, (A1**2 + A2**2 - d**2) / (2 * A1 * A2))))
    if up:
        qp = math.atan2(dz, r) + a; qe = -(math.pi - gam)
    else:
        qp = math.atan2(dz, r) - a; qe = (math.pi - gam)
    return yaw, qp, qe - TIP_DELTA      # кончик ниже линии предплечья: локоть разгибается на 9,8° больше


ARM_JOINTS = [f"{n}_{j}" for n in "LR" for j in "ypre"] + ["L_s", "R_s"]
LIMITS = {**{f"{n}_{j}": (TAU_STALL, W0) for n in "LR" for j in "pe"},
          **{f"{n}_{j}": (TAU32_STALL, W32) for n in "LR" for j in "yr"},
          "L_s": (TAU32_STALL, W32), "R_s": (TAU32_STALL, W32)}


class Sim2(Sim):
    def __init__(self, payload=0.0, obj=None):
        self.m = mujoco.MjModel.from_xml_string(build_xml(payload, obj=obj))
        self.d = mujoco.MjData(self.m)
        names = [f"{n}_{j}" for n in MOUNTS for j in "cfk"] + ARM_JOINTS
        self.jid = {k: self.m.joint(k).qposadr[0] for k in names}
        self.vid = {k: self.m.joint(k).dofadr[0] for k in names}
        self.aid = {k: self.m.actuator(f"m_{k}").id for k in names}
        q = pose_targets(REACH_WORK, ZJ)
        for n, (qc, qf, qk) in q.items():
            for j, v in zip("cfk", (qc, qf, qk)):
                self.d.qpos[self.jid[f"{n}_{j}"]] = v
        self.arm_t = {n: self.tuck(n) for n in "LR"}
        self.eye_t = 0.0
        for n in "LR":
            for j, v in zip("ype", arm_ik(n, self.arm_t[n])):
                self.d.qpos[self.jid[f"{n}_{j}"]] = v
        mujoco.mj_forward(self.m, self.d)
        self.kp, self.kd = 25.0, 0.3       # ноги
        self.kpa, self.kda = 80.0, 0.6     # STS3215 в клешнях
        self.kp32, self.kd32 = 3.0, 0.05

    @staticmethod
    def tuck(n):
        return np.array([0.143, 0.030 if n == "L" else -0.030, -0.024])   # «поджато»: локоть −104° (предел −105°), в покое кончики на 8 мм над столом

    def step(self, q, arm=None, eye=0.0, armq=None):
        d = self.d
        tq = {}
        tgt = {}
        for n, vals in q.items():
            for j, v in zip("cfk", vals): tgt[f"{n}_{j}"] = v
        for n in "LR":
            y, p, e = armq[n] if armq else arm_ik(n, (arm or self.arm_t)[n])
            tgt[f"{n}_y"], tgt[f"{n}_p"], tgt[f"{n}_e"], tgt[f"{n}_r"] = y, p, e, 0.0
        if isinstance(eye, dict): tgt["L_s"], tgt["R_s"] = eye["L"], eye["R"]     # у каждого глаза своя цель (рефлекс по стороне падения)
        else: tgt["L_s"] = tgt["R_s"] = eye
        for n in "LR":     # правило: пока своя клешня поднята (подъём ≥ 60°), глаз отклонён наружу ≥ 20°
            if tgt[f"{n}_p"] >= math.radians(60):
                tgt[f"{n}_s"] = min(tgt[f"{n}_s"], math.radians(-20))
        for k, qd in tgt.items():
            e = qd - d.qpos[self.jid[k]]; w = d.qvel[self.vid[k]]
            stall, w0 = LIMITS.get(k, (TAU_STALL, W0))
            kp, kd = (self.kp32, self.kd32) if stall < 1 else ((self.kpa, self.kda) if k[0] in "LR" and k[1] == "_" else (self.kp, self.kd))
            tau = kp * e - kd * w
            lim = stall * max(0.0, 1 - abs(w) / w0) if np.sign(tau) == np.sign(w) else stall
            tau = float(np.clip(tau, -lim, lim))
            d.ctrl[self.aid[k]] = tau
            tq[k] = (tau, w)
        mujoco.mj_step(self.m, d)
        return tq

    def tip(self, n):
        # кончик в системе корпуса
        b = self.d.body("torso"); R = b.xmat.reshape(3, 3)
        return R.T @ (self.d.body(f"{n}_tip").xpos - b.xpos)

    def weld(self, name, on):
        i = self.m.equality(name).id
        if on:
            b1 = self.d.body(name.replace("g", "") + "_tip"); b2 = self.d.body("obj")
            R1 = b1.xmat.reshape(3, 3)
            rel = R1.T @ (b2.xpos - b1.xpos)
            q1i = np.zeros(4); mujoco.mju_negQuat(q1i, b1.xquat)
            qr = np.zeros(4); mujoco.mju_mulQuat(qr, q1i, b2.xquat)
            self.m.eq_data[i][3:6] = rel; self.m.eq_data[i][6:10] = qr
        self.d.eq_active[i] = 1 if on else 0

    def contacts(self, a_prefix, b_names):
        hits = 0
        for c in self.d.contact[: self.d.ncon]:
            n1 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom1) or ""
            n2 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom2) or ""
            b1 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, self.m.geom_bodyid[c.geom1]) or ""
            b2 = mujoco.mj_id2name(self.m, mujoco.mjtObj.mjOBJ_BODY, self.m.geom_bodyid[c.geom2]) or ""
            if (b1.startswith(a_prefix) and (n2 in b_names or b2 in b_names)) or (b2.startswith(a_prefix) and (n1 in b_names or b1 in b_names)):
                if c.dist < -0.0005: hits += 1
        return hits


def smooth(a, b, k):
    k = 0.5 - 0.5 * math.cos(math.pi * min(1, max(0, k)))
    return a + (b - a) * k


def run_carry(obj_xml, waypoints, two_hands=True, eye_fold=0.0, settle_walk=True, label=""):
    """Клешни берут предмет со стола, переносят по точкам и кладут на спину; потом робот идёт 3 с."""
    s = Sim2(0.0, obj=obj_xml)
    dt = s.m.opt.timestep
    hands = "LR" if two_hands else "L"
    peak = {k: 0.0 for k in ("p", "e", "y", "r")}
    margins, eye_peak = [], 0.0
    hits_body = hits_eyes = 0
    hit_where = []
    released = False
    q_stand = pose_targets(REACH_WORK, ZJ)
    curq = {n: np.array(arm_ik(n, s.arm_t[n])) for n in "LR"}
    t = 0.0
    eye = 0.0
    for idx, (pts, dur, action) in enumerate(waypoints):
        startq = {n: curq[n].copy() for n in "LR"}
        endq = {n: (np.array(arm_ik(n, pts[n])) if n in pts else startq[n]) for n in "LR"}
        e0 = eye
        e1 = eye_fold if action in ("fold_eyes",) else (0.0 if action == "unfold_eyes" else eye)
        steps = int(dur / dt)
        for i in range(steps):
            k = i / steps
            armq = {n: smooth(startq[n], endq[n], k) for n in "LR"}
            eye = smooth(e0, e1, k)
            tq = s.step(q_stand, None, eye, armq)
            for n in "LR":
                for j in "pery":
                    if j in "pe" or j in "yr":
                        peak[j] = max(peak[j], abs(tq[f"{n}_{j}"][0]))
            eye_peak = max(eye_peak, abs(tq["L_s"][0]), abs(tq["R_s"][0]))
            if i % 40 == 0:
                margins.append(s.com_margin())
                hb = s.contacts("obj", {"shell", "L_stalk", "R_stalk", "L_disp", "R_disp"}) if not released else 0
                if hb: hit_where.append(idx)
                hits_body += hb
                hits_eyes += s.contacts("L_", {"L_disp", "R_disp", "L_stalk", "R_stalk"}) + s.contacts("R_", {"L_disp", "R_disp", "L_stalk", "R_stalk"})
        curq = endq
        if action == "grasp":
            for n in hands: s.weld(f"g{n}", True)
        if action == "release":
            for n in hands: s.weld(f"g{n}", False)
            released = True
    # где лежит предмет
    tb = s.d.body("torso"); R = tb.xmat.reshape(3, 3)
    obj_rel = R.T @ (s.d.body("obj").xpos - tb.xpos)
    on_back = obj_rel[2] > 0.055 and -0.075 < obj_rel[0] < 0.03
    # прогулка с предметом на спине
    stays = None
    if settle_walk and on_back:
        period = 0.9; arm = {n: s.tuck(n) for n in "LR"}
        for i in range(int(3.0 / dt)):
            tt = i * dt
            q = pose_targets(REACH_WORK, ZJ, phase=(tt / period) % 1.0, stroke=0.056 * min(1, tt))
            s.step(q, arm, 0.0)
        tb = s.d.body("torso"); R = tb.xmat.reshape(3, 3)
        rel2 = R.T @ (s.d.body("obj").xpos - tb.xpos)
        stays = bool(rel2[2] > 0.055 and -0.075 < rel2[0] < 0.04 and abs(rel2[1]) < 0.08)
    return dict(peak=peak, eye_peak=eye_peak, margin=min(margins) * 1000, hits_body=hits_body,
                hits_arm_eyes=hits_eyes, hit_where=sorted(set(hit_where)), on_back=on_back, stays=stays, obj_rel=obj_rel)


def reach_table():
    """Как далеко перед корпусом кончик достаёт до стола (5 мм над столом)."""
    sx, sy, sz = ARM_S["L"]
    h = -(ZJ - 0.005) - sz
    r = math.sqrt((A1 + A2) ** 2 - h ** 2)
    return sx + r


def run_square(size=0.02, speed=0.02):
    """Кончик клешни обводит квадрат над столом: ошибка слежения без учёта люфта."""
    s = Sim2(0.0)
    dt = s.m.opt.timestep
    c = np.array([0.15, 0.050, -(ZJ - 0.015)])
    corners = [c + np.array(v) * size / 2 for v in ((1, 1, 0), (1, -1, 0), (-1, -1, 0), (-1, 1, 0), (1, 1, 0))]
    arm = {n: s.tuck(n) for n in "LR"}
    q = pose_targets(REACH_WORK, ZJ)
    for i in range(int(1.0 / dt)):
        arm["L"] = smooth(s.tuck("L"), corners[0], i * dt / 1.0); s.step(q, arm)
    errs = []
    for a, b in zip(corners[:-1], corners[1:]):
        steps = int(size / speed / dt)
        for i in range(steps):
            p = a + (b - a) * i / steps
            arm["L"] = p; s.step(q, arm)
            errs.append(np.linalg.norm(s.tip("L") - p))
    errs = np.array(errs[200:])
    return errs.mean() * 1000, errs.max() * 1000


def run_extend_hold(mass=0.2):
    """Одна клешня держит груз на вытянутой вперёд горизонтальной руке."""
    obj = f'<body name="obj" pos="0.3 0 0.3"><freejoint/><geom type="box" size="0.01 0.01 0.01" mass="{mass}" contype="0" conaffinity="0"/></body>'
    s = Sim2(0.0, obj=obj)
    dt = s.m.opt.timestep
    tgt = np.array([ARM_S["L"][0] + (A1 + A2) * 0.98, ARM_S["L"][1], ARM_S["L"][2]])
    q = pose_targets(REACH_WORK, ZJ)
    arm = {n: s.tuck(n) for n in "LR"}
    for i in range(int(1.0 / dt)):
        arm["L"] = smooth(s.tuck("L"), tgt, i * dt); s.step(q, arm)
    # переносим груз в кончик и приваривам
    s.d.qpos[s.m.joint(s.m.body("obj").jntadr[0]).qposadr[0]: s.m.joint(s.m.body("obj").jntadr[0]).qposadr[0] + 3] = s.d.body("L_tip").xpos
    mujoco.mj_forward(s.m, s.d); s.weld("gL", True)
    pk = {"p": 0, "e": 0, "y": 0}
    for i in range(int(2.0 / dt)):
        tq = s.step(q, arm)
        if i * dt > 1.0:
            for j in pk: pk[j] = max(pk[j], abs(tq[f"L_{j}"][0]))
    return pk, s.com_margin() * 1000


if __name__ == "__main__":
    out = []
    P = lambda *a: (print(*a, flush=True), out.append(" ".join(str(x) for x in a)))
    P(f"REACH: кончик достаёт до стола на {reach_table()*1000:.0f} мм от центра корпуса ({reach_table()*1000-75:.0f} мм перед панцирем); полный вылет {(A1+A2)*1000:.0f} мм")
    pk, mg = run_extend_hold(0.2)
    P(f"HOLD 0,2 кг на вытянутой клешне: τ подъём={pk['p']:.2f} локоть={pk['e']:.2f} поворот={pk['y']:.3f} Н·м; запас устойчивости={mg:.0f} мм")
    me, mx = run_square()
    P(f"SQUARE 20 мм: ошибка слежения средняя={me:.2f} мм, макс={mx:.2f} мм (без люфта)")
    G = -0.0386       # кончик 16 мм над столом: пальцы обхватывают край предмета
    phone = '<body name="obj" pos="0.185 0 0.0045"><freejoint/><geom name="obj_g" type="box" size="0.0375 0.075 0.004" mass="0.2" friction="0.8 0.01 0.001" rgba=".1 .1 .1 1"/></body>'
    Y = 0.030          # клешни в своих полосах (компоновка v2: плечи на ±30 мм) — без поворота
    # точки — от плеча (105; 65) те же, что проверены на модели клешни: над предметом (80; −65), взять (80; −104),
    # поднять (100; −5), вперёд-вверх (60; 85), над головой (5; 110), над спиной (−113; 103), положить (−113; 23)
    wp_phone = [
        ({"L": [0.185, Y, 0.0], "R": [0.185, -Y, 0.0]}, 1.0, ""),
        ({"L": [0.185, Y, G], "R": [0.185, -Y, G]}, 0.8, "grasp"),
        ({"L": [0.205, Y, 0.060], "R": [0.205, -Y, 0.060]}, 0.8, ""),
        ({"L": [0.165, Y, 0.150], "R": [0.165, -Y, 0.150]}, 1.0, ""),
        ({"L": [0.110, Y, 0.175], "R": [0.110, -Y, 0.175]}, 1.0, ""),
        ({"L": [-0.008, Y, 0.168], "R": [-0.008, -Y, 0.168]}, 1.2, ""),
        ({"L": [-0.008, Y, 0.088], "R": [-0.008, -Y, 0.088]}, 1.0, "release"),
        ({"L": [0.025, Y, 0.145], "R": [0.025, -Y, 0.145]}, 0.8, ""),
        ({"L": [0.165, Y, 0.150], "R": [0.165, -Y, 0.150]}, 0.8, ""),
        ({"L": Sim2.tuck("L"), "R": Sim2.tuck("R")}, 1.0, ""),
    ]
    r = run_carry(phone, wp_phone, two_hands=True, eye_fold=0.0)
    P(f"PHONE 200 г двумя клешнями на спину: τ пик подъём={r['peak']['p']:.2f} локоть={r['peak']['e']:.2f} поворот={r['peak']['y']:.3f} запястье={r['peak']['r']:.3f}; "
      f"стебельки={r['eye_peak']:.3f} Н·м; мин. запас устойчивости={r['margin']:.0f} мм; касаний предмет↔корпус/глаза={r['hits_body']}; клешня↔глаза={r['hits_arm_eyes']}; "
      f"лёг на спину={r['on_back']}; удержался при ходьбе={r['stays']}; положение={np.round(r['obj_rel']*1000)}; шаги с касанием={r['hit_where']}")
    pen = '<body name="obj" pos="0.180 0.0 0.0045"><freejoint/><geom name="obj_g" type="capsule" fromto="0 -0.06 0 0 0.06 0" size="0.0045" mass="0.015" friction="0.8 0.01 0.001"/></body>'
    wp_pen = [
        ({"L": [0.180, Y, 0.0]}, 0.8, ""),
        ({"L": [0.180, Y, G]}, 0.6, "grasp"),
        ({"L": [0.205, Y, 0.060]}, 0.8, ""),
        ({"L": [0.165, Y, 0.150]}, 0.8, ""),
        ({"L": [0.110, Y, 0.175]}, 0.8, ""),
        ({"L": [-0.008, Y, 0.168]}, 1.0, ""),
        ({"L": [-0.008, Y, 0.082]}, 0.8, "release"),
        ({"L": [0.025, Y, 0.145]}, 0.6, ""),
        ({"L": [0.165, Y, 0.150]}, 0.6, ""),
        ({"L": Sim2.tuck("L")}, 0.8, ""),
    ]
    r = run_carry(pen, wp_pen, two_hands=False, eye_fold=0.0)
    P(f"PEN 15 г одной клешнёй на спину: τ пик подъём={r['peak']['p']:.2f} локоть={r['peak']['e']:.2f}; мин. запас устойчивости={r['margin']:.0f} мм; "
      f"касаний={r['hits_body']}/{r['hits_arm_eyes']}; лёг на спину={r['on_back']}; удержался при ходьбе={r['stays']}; положение={np.round(r['obj_rel']*1000)}")
    for label, pl, th in (("WALK comfort", 0.5, 0.45), ("WALK fast", 0.5, 0.34)):
        rr = run_walk2(pl, th)
        P(f"{label} payload={pl}: v={rr['speed']:.1f} см/с; τ пик c/f/k={rr['peak']['c']:.2f}/{rr['peak']['f']:.2f}/{rr['peak']['k']:.2f}; "
          f"выше номинала f/k={rr['over']['f']:.1f}/{rr['over']['k']:.1f}%; запас={rr['margin']:.0f} мм; мощность={rr['power']:.0f} Вт")
    P(f"MASS: {sum(Sim2(0.0).m.body_mass):.3f} кг")
    open("sim_results.txt", "w", encoding="utf-8").write("\n".join(out))
