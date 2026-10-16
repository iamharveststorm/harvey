"""Харви «Компакт мини» в MuJoCo: размеры, массы и видимые детали — из CAD (модели/мини/harvey_mini_parts.py).

Все 28 приводов — STS3032 (пик 0,44 Н·м, номинал 0,147 Н·м, 0,09 с/60°): 6 ног × 3 сустава, 2 клешни × 4 сустава
(поворот плеча, подъём, локоть, захват — губки смыкаются вбок), 2 стебелька глаз. Хвоста нет.
Физика — на простых формах (группа 1), детали из CAD только рисуются (группа 2).
Правила движения — модели/мини/harvey_mini_parts.py (RULES): прошивка и эта симуляция их соблюдают.

    python harvey_mini.py               # все проверки, итог в mini_results.json
    python harvey_mini.py walk pen      # выборочно: stand, walk, turn, pen, wipe, tip, edge, dock
    python harvey_mini.py --view        # окно MuJoCo: Харви идёт
После правок CAD: (окружение CAD) python модели/мини/harvey_mini_parts.py — обновит assets/."""
import math, sys, json, os
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
ADIR = os.path.join(HERE, "assets")
CAD = json.load(open(os.path.join(ADIR, "mini_visual.json"), encoding="utf-8"))
G, MS = CAD["G"], CAD["masses"]
mm = 0.001

# ---------------- приводы STS3032 ----------------
STALL, RATED = 0.44, 0.147                 # Н·м
W0 = math.radians(60) / 0.09               # рад/с без нагрузки
DT = 0.0005

# ---------------- геометрия из CAD (м) ----------------
COX, FEM, TIB, FOOT_R = G["cox"] * mm, G["fem"] * mm, G["tib"] * mm, G["foot_r"] * mm
ZJ = TIB - FEM * math.sin(math.radians(20))           # оси бедра над столом в стойке
REACH = COX + FEM * math.cos(math.radians(20))
MOUNTS = {n: (v[0] * mm, v[1] * mm, v[2]) for n, v in G["mounts"].items()}
TRIPOD_A = ("RF", "LM", "RB")
BX0, BX1, BY0, BY1, BZ0, BZ1 = [v * mm for v in G["body"]]
ARM_S = {s: tuple(v * mm for v in G["arm_s"][s]) for s in "LR"}
A1, FORE = G["a1"] * mm, G["fore"] * mm
GX, GY = CAD["GX"] * mm, CAD["GY"] * mm
JAW_MID, JAW_END = GX + 0.015, GX + 0.026            # середина и конец губок вдоль кисти
EYE = {s: tuple(v * mm for v in G["eye"][s]) for s in "LR"}
TUCK_Q = (0.0, 15.0, -115.0)                           # «поджато» (градусы) — как CLAW_TUCK в CAD


def torso_mass():
    limbs = 6 * (MS["coxa"] + MS["femur"] + MS["tibia"]) + 2 * (MS["ay"] + MS["up"] + MS["fore"] + MS["hand"] + MS["jaw"]) + 2 * MS["eye"]
    return MS["total"] - limbs


def _vis(body, key=None):
    """Видимые детали из CAD на тело (группа 2)."""
    out = ""
    for f, mat in CAD["bodies"].get(key or body, []):
        out += f'<geom type="mesh" mesh="{f[:-4]}" material="v_{mat}" group="2" contype="0" conaffinity="0" mass="0"/>'
    return out


DOCK_X = 0.20                                          # станция в 20 см перед стартом


def dock_xml(visual):
    """Станция: площадка 64 × 56 × 4 мм, 2 подпружиненных контакта (мягкий контакт = пружина), башенка с меткой."""
    h, top = CAD["dock_h"] * mm, CAD["pogo_top"] * mm
    g = [f'<geom name="dock_pad" type="box" size="0.030 0.026 {h / 2}" pos="{DOCK_X} 0 {h / 2}" rgba=".3 .3 .32 1" group="1"/>',
         f'<geom name="dock_tower" type="box" size="0.004 0.030 0.026" pos="{DOCK_X + 0.144} 0 0.026" rgba=".3 .3 .32 1" group="1"/>']
    for i, y in enumerate(CAD["belly_y"]):
        g.append(f'<geom name="pogo{i}" type="cylinder" size="0.0025 {(top - h) / 2}" pos="{DOCK_X} {y * mm} {h + (top - h) / 2}" '
                 f'solref="0.02 0.7" solimp="0.5 0.9 0.0015" rgba=".85 .7 .3 1" group="1"/>')
    if visual:
        g += [f'<geom type="mesh" mesh="{f[:-4]}" pos="{DOCK_X} 0 0" material="v_grey" group="2" contype="0" conaffinity="0"/>' for f, _ in CAD["bodies"]["dock"]]
    return "".join(g)


def build_xml(pen=False, napkin=False, world_xml=None, visual=True, dock=False):
    vis = _vis if visual else (lambda *a, **k: "")
    legs = ""
    for n, (x, y, yaw) in MOUNTS.items():
        legs += f"""
      <body name="{n}_coxa" pos="{x} {y} 0" euler="0 0 {yaw}">
        <joint name="{n}_c" axis="0 0 1" range="-30 30" armature="0.0015" damping="0.01"/>
        <geom type="box" size="0.0115 0.0138 0.006" pos="{COX - 0.0058} 0 0" mass="{MS['coxa']:.4f}" group="1" contype="2" conaffinity="0" rgba=".2 .2 .22 1"/>
        {vis(f"{n}_coxa", "leg_coxa")}
        <body name="{n}_femur" pos="{COX} 0 0">
          <joint name="{n}_f" axis="0 -1 0" range="-45 85" armature="0.0015" damping="0.01"/>
          <geom type="box" size="{FEM / 2} 0.009 0.006" pos="{FEM / 2} 0.004 0" mass="{MS['femur']:.4f}" group="1" contype="2" conaffinity="0" rgba=".9 .4 .2 1"/>
          {vis(f"{n}_femur", "leg_femur")}
          <body name="{n}_tibia" pos="{FEM} 0 0">
            <joint name="{n}_k" axis="0 -1 0" range="-130 -60" armature="0.0015" damping="0.01"/>
            <geom type="capsule" fromto="0.012 0 0 {TIB - FOOT_R - 0.002} 0 0" size="0.0036" mass="{MS['tibia']:.4f}" group="1" contype="2" conaffinity="0" rgba=".9 .4 .2 1"/>
            <geom name="{n}_foot" type="sphere" pos="{TIB - FOOT_R} 0 0" size="{FOOT_R}" mass="0.0005" friction="1.0 0.01 0.001" group="1" rgba=".1 .1 .1 1"/>
            {vis(f"{n}_tibia", "leg_tibia")}
          </body>
        </body>
      </body>"""
    arms = ""
    for s, (x, y, z) in ARM_S.items():
        sg = 1 if s == "L" else -1
        arms += f"""
      <body name="{s}_ay" pos="{x} {y} {z}">
        <joint name="{s}_y" axis="0 0 {sg}" range="-10 70" armature="0.0015" damping="0.01"/>
        <geom type="cylinder" size="0.008 0.002" pos="0 0 -0.009" mass="{max(0.001, MS['ay'] - 0.02):.4f}" group="1" contype="0" conaffinity="0"/>
        {vis(f"{s}_ay")}
        <body name="{s}_up">
          <joint name="{s}_p" axis="0 -1 0" range="-20 90" armature="0.0015" damping="0.01"/>
          <geom type="box" size="0.0115 0.0138 0.006" pos="-0.0058 0 0" mass="0.020" group="1" contype="0" conaffinity="0"/>
          <geom name="{s}_upg" type="capsule" fromto="0.008 {sg * 0.020} 0 {A1} {sg * 0.020} 0" size="0.005" mass="{max(0.001, MS['up'] - 0.02):.4f}" group="1" rgba=".9 .4 .2 1"/>
          <geom type="box" size="0.0115 0.0138 0.006" pos="{A1 - 0.0058} 0 0" mass="0.0001" group="1" rgba=".1 .1 .1 1"/>
          {vis(f"{s}_up")}
          <body name="{s}_fore" pos="{A1} 0 0">
            <joint name="{s}_e" axis="0 -1 0" range="-140 60" armature="0.0015" damping="0.01"/>
            <geom name="{s}_foreg" type="capsule" fromto="0.006 {-sg * 0.020} 0 {FORE} {-sg * 0.006} 0.010" size="0.004" mass="{MS['fore']:.4f}" group="1" rgba=".9 .4 .2 1"/>
            {vis(f"{s}_fore")}
            <body name="{s}_hand" pos="{FORE} 0 0">
              <geom type="box" size="0.0115 0.006 0.0138" pos="{GX - 0.0058} {sg * GY} {0.009 + 0.0138}" mass="{MS['hand'] - 0.0015:.4f}" group="1" rgba=".1 .1 .1 1"/>
              <geom name="{s}_jawfix" type="box" size="0.015 0.0015 0.004" pos="{GX + 0.011} {sg * 0.006} 0" mass="0.0015" friction="1.2 0.02 0.002" group="1" rgba=".1 .1 .1 1"/>
              {vis(f"{s}_hand")}
              <site name="{s}_mid" pos="{JAW_MID} 0 0" size="0.002"/>
              <body name="{s}_jaw" pos="{GX} {sg * GY} 0">
                <joint name="{s}_g" axis="0 0 {sg}" range="-50 12" armature="0.0005" damping="0.005"/>
                <geom name="{s}_jawmov" type="box" size="0.015 0.0015 0.004" pos="0.012 {-sg * 0.0025} 0" mass="{MS['jaw']:.4f}" friction="1.2 0.02 0.002" group="1" rgba=".1 .1 .1 1"/>
                {vis(f"{s}_jaw")}
              </body>
            </body>
          </body>
        </body>
      </body>"""
    eyes = "".join(f"""
      <body name="{s}_eye" pos="{x} {y} {z}">
        <joint name="{s}_s" axis="{1 if s == 'L' else -1} 0 0" range="-90 20" armature="0.001" damping="0.005"/>
        <geom type="capsule" fromto="-0.0025 0 0 -0.0025 0 {G['stalk'] * mm}" size="0.003" mass="{MS['eye'] * 0.4:.4f}" group="1" contype="0" conaffinity="0"/>
        <geom type="cylinder" pos="0 0 {(G['stalk'] + G['disp_d'] / 2) * mm}" euler="0 90 0" size="{G['disp_d'] / 2 * mm} 0.003" mass="{MS['eye'] * 0.6:.4f}" group="1" contype="0" conaffinity="0"/>
        {vis(f"{s}_eye")}
      </body>""" for s, (x, y, z) in EYE.items())
    pen_xml = f"""
    <body name="pen" pos="0.120 {ARM_S['L'][1]} 0.0045"><freejoint/>
      <geom name="pen_g" type="capsule" fromto="-0.062 0 0 0.062 0 0" size="0.0045" mass="0.010" friction="0.8 0.01 0.002" condim="4" rgba=".1 .3 .8 1"/>
    </body>""" if pen else ""
    nap_xml = f"""
    <body name="napkin" pos="0.118 {ARM_S['L'][1]} 0.00075"><freejoint/>
      <geom name="napkin_g" type="box" size="0.035 0.035 0.00075" mass="0.003" friction="0.45 0.01 0.001" rgba=".97 .97 .95 1"/>
    </body>""" if napkin else ""
    acts = "".join(f'<motor name="m_{j}" joint="{j}" ctrlrange="-{STALL} {STALL}"/>' for j in joint_names())
    meshes = "".join(f'<mesh name="{f[:-4]}" file="{f}"/>' for k, items in CAD["bodies"].items() for f, _ in items if k != "dock" or dock) if visual else ""
    floor = (world_xml or '<geom name="floor" type="plane" size="1 1 0.1" friction="0.8 0.01 0.001" rgba=".78 .64 .46 1"/>') + (dock_xml(visual) if dock else "")
    return f"""<mujoco model="harvey_mini">
  <option timestep="{DT}" integrator="implicitfast"/>
  <visual><global offwidth="1920" offheight="1080"/><quality shadowsize="4096"/></visual>
  <default><joint type="hinge"/><geom contype="1" conaffinity="3"/></default>
  <asset>{meshes}
    <material name="v_orange" rgba="0.92 0.38 0.12 1" specular="0.35" shininess="0.45"/>
    <material name="v_grey" rgba="0.20 0.22 0.25 1" specular="0.25" shininess="0.35"/>
    <material name="v_servo" rgba="0.07 0.07 0.08 1" specular="0.3" shininess="0.5"/>
    <material name="v_tpu" rgba="0.05 0.05 0.05 1" specular="0.05"/>
    <material name="v_pcb" rgba="0.10 0.36 0.21 1" specular="0.3"/>
    <material name="v_battery" rgba="0.11 0.42 0.53 1" specular="0.6" shininess="0.6"/>
    <material name="v_screen" rgba="0.36 0.90 1.0 1" emission="0.9"/>
  </asset>
  <worldbody>
    <light pos="0.2 -0.3 1" dir="-0.2 0.3 -1" castshadow="true"/>
    {floor}
    <body name="torso" pos="0 0 {ZJ + 0.003}">
      <freejoint/>
      <geom name="body" type="box" size="{(BX1 - BX0) / 2} {(BY1 - BY0) / 2} {(BZ1 - BZ0) / 2}" pos="{(BX0 + BX1) / 2} 0 {(BZ0 + BZ1) / 2}" mass="{torso_mass():.4f}" group="1" rgba=".25 .26 .28 1" conaffinity="1"/>
      {vis("torso")}
      {arms}{eyes}{legs}
    </body>{pen_xml}{nap_xml}
  </worldbody>
  <actuator>{acts}</actuator>
</mujoco>"""


def joint_names():
    return [f"{n}_{j}" for n in MOUNTS for j in "cfk"] + [f"{s}_{j}" for s in "LR" for j in "ypeg"] + ["L_s", "R_s"]


def load_assets():
    return {f: open(os.path.join(ADIR, f), "rb").read() for f in os.listdir(ADIR) if f.endswith(".stl")}


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


def arm_ik(s, p, tipx=JAW_MID):
    """p — точка на губках (на расстоянии tipx от конца предплечья) в системе корпуса. Решение «локоть вверх»."""
    x, y, z = ARM_S[s]; sg = 1 if s == "L" else -1
    dx, dy, dz = p[0] - x, p[1] - y, p[2] - z
    qy = sg * math.atan2(dy, dx); r = math.hypot(dx, dy); A2 = FORE + tipx
    d = min(math.hypot(r, dz), A1 + A2 - 1e-4)
    qe = math.acos(max(-1, min(1, (A1 ** 2 + A2 ** 2 - d ** 2) / (2 * A1 * A2)))) - math.pi
    qp = math.atan2(dz, r) + math.acos(max(-1, min(1, (A1 ** 2 + d ** 2 - A2 ** 2) / (2 * A1 * d))))
    return qy, qp, qe


def arm_fk(s, q, tipx=JAW_MID):
    x, y, z = ARM_S[s]; sg = 1 if s == "L" else -1
    qy, qp, qe = q
    r = A1 * math.cos(qp) + (FORE + tipx) * math.cos(qp + qe); h = A1 * math.sin(qp) + (FORE + tipx) * math.sin(qp + qe)
    return np.array([x + r * math.cos(qy), y + sg * r * math.sin(qy), z + h])


def claw_ok(s, q):
    """Правила 1 и 4 из CAD (углы в радианах)."""
    qy, qp, qe = (math.degrees(v) for v in q)
    if not (-10.5 <= qy <= 70 and -20.5 <= qp <= 90 and -140 <= qe <= 60): return False
    x, y, z = ARM_S[s]; pts = []
    a, b = math.radians(qp), math.radians(qp + qe)
    e = (A1 * math.cos(a), A1 * math.sin(a)); w = (e[0] + FORE * math.cos(b), e[1] + FORE * math.sin(b))
    t = (w[0] + JAW_END * math.cos(b), w[1] + JAW_END * math.sin(b))
    for r, h in (e, w, t): pts.append((x + r * math.cos(math.radians(qy)), z + h))
    low = any(pz <= BZ1 + 0.003 for _, pz in pts)
    if low and qy > 8.5: return False
    if qp >= 60 and qy < 0: return False
    return all(px > BX1 + 0.003 or pz > BZ1 + 0.003 for px, pz in pts)


# ---------------- симуляция ----------------
class Mini:
    def __init__(self, pen=False, napkin=False, world_xml=None, visual=False, assets=None, dock=False):
        self.m = mujoco.MjModel.from_xml_string(build_xml(pen, napkin, world_xml, visual, dock), assets or (load_assets() if visual else {}))
        self.d = mujoco.MjData(self.m)
        self.j = {k: (self.m.joint(k).qposadr[0], self.m.joint(k).dofadr[0], self.m.actuator(f"m_{k}").id) for k in joint_names()}
        self.kp = {"c": 3.0, "f": 4.0, "k": 4.0, "y": 2.0, "p": 3.0, "e": 3.0, "g": 1.0, "s": 1.0}
        self.kd = 0.03
        self.grip_lim = 0.12                      # ограничение момента захвата (ток в STS3032), Н·м
        self.q = {k: 0.0 for k in self.j}; self.tq = {k: [] for k in self.j}; self.viol = 0
        st = self.stand_q(); self.q.update(st)
        for k, v in st.items(): self.d.qpos[self.j[k][0]] = v
        for s in "LR":
            for jj, v in zip("ype", (math.radians(a) for a in TUCK_Q)): self.q[f"{s}_{jj}"] = v; self.d.qpos[self.j[f"{s}_{jj}"][0]] = v
        mujoco.mj_forward(self.m, self.d)

    def stand_q(self, dz=0.0):
        h = -(ZJ - FOOT_R) + dz; out = {}
        for n in MOUNTS:
            for jj, v in zip("cfk", leg_ik(n, neutral(n), h)): out[f"{n}_{jj}"] = v
        return out

    def step(self, record=True):
        d = self.d
        for s in "LR":                                         # правило 2: клешня выше 60° — глаз наружу на 45°
            if self.q[f"{s}_p"] >= math.radians(60): self.q[f"{s}_s"] = min(self.q[f"{s}_s"], math.radians(-45))
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
        v = np.concatenate([np.array(self.tq[k]) for k in keys if self.tq[k]])
        return {"средняя_%ном": round(float(v.mean() / RATED * 100)), "пик_%ном": round(float(np.percentile(v, 99) / RATED * 100)),
                "пик_%предела": round(float(np.percentile(v, 99) / STALL * 100))}

    def reset_load(self):
        self.tq = {k: [] for k in self.j}

    def set_arm(self, s, q):
        if not claw_ok(s, q): self.viol += 1
        for jj, v in zip("ype", q): self.q[f"{s}_{jj}"] = v

    def to_body(self, pw):
        tb = self.d.body("torso"); R = tb.xmat.reshape(3, 3); return R.T @ (np.array(pw) - tb.xpos)

    def gait(self, vx=0.06, wz=0.0, t_half=0.30, lift=0.015, dz=0.0):
        h0 = -(ZJ - FOOT_R) + dz
        def fn(t):
            ph = (t / (2 * t_half)) % 1.0
            for n in MOUNTS:
                p0 = neutral(n); pp = ph if n in TRIPOD_A else (ph + 0.5) % 1.0
                if pp < 0.5: u = 0.5 - 2 * pp; z = 0.0
                else:
                    s_ = (pp - 0.5) * 2; u = -0.5 + (s_ - math.sin(2 * math.pi * s_) / (2 * math.pi)); z = lift * math.sin(math.pi * s_)
                a = wz * t_half * u; c, sn = math.cos(a), math.sin(a)
                p = np.array([c * p0[0] - sn * p0[1], sn * p0[0] + c * p0[1]]) + np.array([vx * t_half * u, 0])
                for jj, v in zip("cfk", leg_ik(n, p, h0 + z)): self.q[f"{n}_{jj}"] = v
        return fn

    def crouch(self, dz, sec=0.6):
        tgt = self.stand_q(dz); st = {k: self.q[k] for k in tgt}
        self.run(sec, lambda t: self.q.update({k: st[k] + (tgt[k] - st[k]) * min(1, t / sec) for k in tgt}))

    def move_arm(self, s, p_to, sec, tipx=JAW_MID, p_from=None):
        """Точка губок по прямой из текущей в p_to (система корпуса)."""
        q0 = tuple(self.q[f"{s}_{j}"] for j in "ype")
        a = arm_fk(s, q0, tipx) if p_from is None else np.array(p_from); b = np.array(p_to)
        def fn(t):
            k = min(1.0, t / sec); k = 0.5 - 0.5 * math.cos(math.pi * k)
            self.set_arm(s, arm_ik(s, a + (b - a) * k, tipx))
        self.run(sec, fn)


LEGS_F = [f"{n}_f" for n in MOUNTS]; LEGS_K = [f"{n}_k" for n in MOUNTS]; LEGS_C = [f"{n}_c" for n in MOUNTS]


def test_stand():
    s = Mini(); s.run(1.0, record=False); s.reset_load(); s.run(2.0)
    return {"бедро": s.load(LEGS_F), "колено": s.load(LEGS_K), "наклон": round(s.tilt(), 1),
            "просвет_под_корпусом_мм": round(float(s.d.body("torso").xpos[2] + BZ0) * 1000)}


def test_walk(vx=0.06, sec=8.0):
    s = Mini(); s.run(0.8, record=False)
    x0 = s.d.body("torso").xpos.copy(); s.reset_load(); mx = 0; fn = s.gait(vx)
    for i in range(int(sec / DT)):
        fn(i * DT); s.step()
        if i % 100 == 0: mx = max(mx, s.tilt())
    x1 = s.d.body("torso").xpos
    return {"скорость_см_с": round(float(x1[0] - x0[0]) / sec * 100, 1), "увод_мм": round(float(x1[1] - x0[1]) * 1000),
            "наклон_макс": round(mx, 1), "на_ногах": bool(s.tilt() < 30), "бедро": s.load(LEGS_F), "колено": s.load(LEGS_K),
            "поворот_ноги": s.load(LEGS_C)}


def test_turn():
    s = Mini(); s.run(0.5, record=False)
    yaw = lambda q: math.degrees(math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2)))
    y0 = yaw(s.d.body("torso").xquat); s.run(4.0, s.gait(0.0, wz=0.8))
    return {"градусов_в_с": round((yaw(s.d.body("torso").xquat) - y0) / 4, 1), "на_ногах": bool(s.tilt() < 30)}


def test_pen():
    """Левая клешня: присесть, губки к ручке сверху, сжать, поднять на 60 мм, пронести шагом, подать вперёд-вверх."""
    s = Mini(pen=True); s.run(0.8, record=False)
    s.q["L_g"] = math.radians(-45); s.run(0.3)
    s.crouch(0.016)
    pen = s.d.body("pen").xpos.copy(); s.reset_load()
    over = s.to_body(pen + [0, 0, 0.030]); at = s.to_body([pen[0], pen[1], 0.0016])     # конец губок — над столом
    s.move_arm("L", over, 1.0, JAW_END); s.move_arm("L", at, 0.8, JAW_END)
    s.q["L_g"] = 0.25; s.run(0.6)                                   # сжать: момент ограничен grip_lim
    s.crouch(0.0)
    up = s.to_body(pen + [0, 0, 0.060]); s.move_arm("L", up, 1.0, JAW_END)
    lift = float(s.d.body("pen").xpos[2] - pen[2])
    s.run(2.0, s.gait(0.05))
    give = np.array([0.120, ARM_S["L"][1], 0.075]); s.move_arm("L", give, 1.0, JAW_END); s.run(1.0)
    pz = float(s.d.body("pen").xpos[2]); dist = float(np.linalg.norm(s.d.body("pen").xpos - s.d.site("L_mid").xpos))
    return {"поднята_на_мм": round(lift * 1000), "подана_на_высоте_над_столом_мм": round(pz * 1000),
            "в_пальцах": bool(dist < 0.035 and pz > 0.03), "наклон_корпуса": round(s.tilt(), 1), "на_ногах": bool(s.tilt() < 30),
            "нарушений_правил": s.viol, "нагрузка": {"поворот": s.load(["L_y"]), "подъём": s.load(["L_p"]), "локоть": s.load(["L_e"]), "захват": s.load(["L_g"])}}


def test_wipe():
    """Салфетка 70 × 70 мм: сжатые губки прижимают её к столу; рука ходит вперёд-назад (28 мм: дальше вперёд
    подъём плеча вышел бы за −20°),
    вбок — поворот корпуса на месте (клешня низко наружу не поворачивается — правило 1). 3 полосы."""
    s = Mini(napkin=True); s.run(0.8, record=False)
    s.q["L_g"] = 0.15; s.crouch(0.016)
    nap = s.d.body("napkin").xpos.copy(); s.reset_load()
    over = s.to_body(nap + [0, 0, 0.030]); press = s.to_body([nap[0], nap[1], -0.0005])   # прижим: губки давят в салфетку
    s.move_arm("L", over, 0.8, JAW_END); s.move_arm("L", press, 0.6, JAW_END)
    start = s.d.body("napkin").xpos.copy(); xs = []; ys = []
    for k in range(3):
        for dx in (0.008, -0.020):
            s.move_arm("L", press + np.array([dx, 0, 0]), 0.6, JAW_END)
            xs.append(float(s.d.body("napkin").xpos[0] - start[0]))
        if k < 2:                                       # следующая полоса: развернуть корпус на ~10°, губки не отпускать
            fn = s.gait(0.0, wz=0.6, dz=0.016, lift=0.010); s.run(0.6, fn)
            s.crouch(0.016, 0.3)
            ys.append(float(s.d.body("napkin").xpos[1] - start[1]))
    s.move_arm("L", press + [0, 0, 0.03], 0.5, JAW_END)
    span = max(xs) - min(xs)
    return {"салфетка_ходит_мм": round(span * 1000), "рука_ходит_мм": 28, "следует_за_рукой": bool(span > 0.020),
            "сдвиг_полос_вбок_мм": round((max(ys + [0]) - min(ys + [0])) * 1000), "наклон": round(s.tilt(), 1),
            "нарушений_правил": s.viol, "нагрузка": {"поворот": s.load(["L_y"]), "подъём": s.load(["L_p"]), "локоть": s.load(["L_e"])}}


def test_tip():
    """Обе клешни вытянуты вперёд горизонтально — не клюёт ли носом."""
    s = Mini(); s.run(0.5, record=False)
    for sd in "LR":
        s.set_arm(sd, (0.0, 0.0, 0.0))
    s.reset_load(); s.run(1.5)
    return {"наклон": round(s.tilt(), 1), "подъём_плеча": s.load(["L_p", "R_p"]), "передние_колени": s.load(["LF_k", "RF_k"])}


def test_edge():
    """Край стола: передний датчик VL53L4CD у дна смотрит вперёд-вниз с наклоном 2,3 : 1 (как у «Компакта»):
    край виден за 2,3·h до датчика. Какой запас у стоп и поджатых клешней, если остановиться сразу."""
    x1 = BX1 + 0.002; zs = ZJ + BZ0 + 0.0065; ahead = 2.3 * zs
    foot_x = max(neutral(n)[0] for n in ("LF", "RF")) + FOOT_R
    claw_x = arm_fk("L", tuple(math.radians(a) for a in TUCK_Q), JAW_END)[0]
    stop = x1 + ahead - 0.010                           # 10 мм — тормозной путь на 6 см/с
    return {"край_виден_за_мм_до_корпуса": round(ahead * 1000), "запас_стопы_мм": round((stop - foot_x) * 1000),
            "запас_клешни_мм": round((stop - claw_x) * 1000)}


def test_dock():
    """Заход на станцию: 20 см шагом прямо (на роботе — по метке AprilTag), остановка над контактами,
    корпус ниже на 13 мм — пластины брюха ложатся на подпружиненные контакты."""
    s = Mini(dock=True); s.run(0.6, record=False)
    fn = s.gait(0.06); x0 = float(s.d.body("torso").xpos[0]); t = 0.0
    while float(s.d.body("torso").xpos[0]) < DOCK_X - 0.003 and t < 8.0:
        fn(t); s.step(False); t += DT
    s.q.update(s.stand_q()); s.run(0.5, record=False)
    s.crouch(CAD["rest_drop"] * mm, 1.0); s.run(0.5, record=False)
    m, d = s.m, s.d; bid = m.geom("body").id; f6 = np.zeros(6); F = {}
    for i in range(d.ncon):
        c = d.contact[i]
        for k in range(2):
            gid = m.geom(f"pogo{k}").id
            if {c.geom1, c.geom2} == {bid, gid}:
                mujoco.mj_contactForce(m, d, i, f6); F[k] = F.get(k, 0) + abs(f6[0])
    err = s.d.body("torso").xpos[:2] - [DOCK_X, 0]
    feet_on_pad = sum(1 for n in MOUNTS for i in range(d.ncon) if m.geom(f"{n}_foot").id in (d.contact[i].geom1, d.contact[i].geom2)
                      and m.geom("dock_pad").id in (d.contact[i].geom1, d.contact[i].geom2))
    return {"дошёл_за_с": round(t, 1), "промах_мм": [round(float(v) * 1000) for v in err],
            "сила_на_контактах_Н": [round(float(F.get(k, 0.0)), 2) for k in range(2)], "заряжается": bool(min(F.get(0, 0), F.get(1, 0)) > 0.3),
            "стоп_на_площадке": feet_on_pad, "наклон": round(s.tilt(), 1)}


TESTS = {"stand": test_stand, "walk": test_walk, "turn": test_turn, "pen": test_pen, "wipe": test_wipe, "tip": test_tip, "edge": test_edge, "dock": test_dock}


def view():
    import mujoco.viewer
    s = Mini(pen=True, visual=True)
    with mujoco.viewer.launch_passive(s.m, s.d) as v:
        v.opt.geomgroup[1] = 0; v.cam.distance = 0.45; v.cam.azimuth = 150; v.cam.elevation = -20
        fn = s.gait(0.05); t = 0.0
        while v.is_running() and t < 6.0:
            for _ in range(33): fn(t); s.step(False); t += DT
            v.cam.lookat[:] = s.d.body("torso").xpos; v.sync()


if __name__ == "__main__":
    if "--view" in sys.argv:
        view(); sys.exit()
    which = [a for a in sys.argv[1:] if a in TESTS] or list(TESTS)
    res = {}
    for k in which:
        res[k] = TESTS[k](); print(f"{k}: {res[k]}", flush=True)
    res["масса_кг"] = MS["total"]
    res["размеры_мм"] = {"оси бедра над столом": round(ZJ * 1000, 1),
                         "размах стоп в стойке": round(2 * max(abs(neutral(n)[1]) for n in MOUNTS) * 1000)}
    json.dump(res, open(os.path.join(HERE, "mini_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
