"""Харви: третья рука-«хвост» с присоской на спине.
Крепление сзади на панцире, поворот (STS3032) + плечо и локоть (STS3215) + наклон запястья (STS3032),
звенья 70 + 70 мм, присоска Ø22 мм на коротком сильфоне. Запястье держит присоску «лицом вниз» —
иначе телефон наклоняется вместе с рукой и соскальзывает при укладке. Тесты: телефон со стола позади — на спину;
ходьба с хвостом и телефоном; переворот со спины; передача телефона клешням в воздухе."""
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import math, json
import numpy as np
import mujoco
import harvey_sim as H
import harvey_scenarios as S
import harvey_grasp as GR

DT = S.DT
T_MOUNT = np.array([-0.080, 0.0, 0.072])   # в системе корпуса (на стойке над задним краем)
T1, T2 = 0.070, 0.070                      # плечо, предплечье (до оси запястья)
CUP = 0.026                                # от оси запястья до поверхности присоски
TAIL = '''
      <body name="T_base" pos="-0.080 0 0.072" euler="0 0 180">
        <joint name="T_y" type="hinge" axis="0 0 1" range="-120 120" armature="0.002" damping="0.02"/>
        <geom type="box" size="0.006 0.0116 0.014" pos="0 0 -0.006" mass="0.020" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
        <body name="T_up">
          <joint name="T_p" type="hinge" axis="0 -1 0" range="-40 135" armature="0.01" damping="0.05"/>
          <geom name="T_upg" type="capsule" fromto="0.020 0 0 0.070 0 0" size="0.008" mass="0.070" rgba=".85 .4 .25 1"/>
          <body name="T_fore" pos="0.070 0 0">
            <joint name="T_e" type="hinge" axis="0 -1 0" range="-130 155" armature="0.01" damping="0.05"/>
            <geom name="T_foreg" type="capsule" fromto="0.014 0 0 0.060 0 0" size="0.007" mass="0.070" rgba=".85 .4 .25 1"/>
            <body name="T_wr" pos="0.070 0 0">
              <joint name="T_w" type="hinge" axis="0 -1 0" range="-160 160" armature="0.002" damping="0.02"/>
              <geom type="box" size="0.006 0.0116 0.014" pos="0.004 0 0" mass="0.020" contype="0" conaffinity="0" rgba=".2 .2 .22 1"/>
              <body name="T_cup" pos="0.022 0 0">
                <joint name="T_ball" type="ball" range="0 15" limited="true" damping="0.002" stiffness="0.02"/>
                <geom name="T_cupg" type="cylinder" size="0.011 0.004" euler="0 90 0" mass="0.050" friction="1.0 0.01 0.001" rgba=".95 .95 1 1"/>
              </body>
            </body>
          </body>
        </body>
      </body>'''


def build_tail(obj="", extra="", suck=12.0):
    xml = GR.build(obj, extra=extra)
    xml = xml.replace('<geom name="tray"', TAIL + '<geom name="tray"', 1)
    xml = xml.replace('</worldbody>', '</worldbody><contact><exclude body1="T_fore" body2="T_cup"/><exclude body1="T_wr" body2="T_cup"/></contact>', 1)
    xml = xml.replace('<actuator>', '<actuator><motor name="m_T_y" joint="T_y" ctrlrange="-0.44 0.44"/>'
                      '<motor name="m_T_p" joint="T_p" ctrlrange="-2.94 2.94"/><motor name="m_T_e" joint="T_e" ctrlrange="-2.94 2.94"/><motor name="m_T_w" joint="T_w" ctrlrange="-0.44 0.44"/>'
                      f'<adhesion name="T_suck" body="T_cup" ctrlrange="0 1" gain="{suck}"/>', 1)
    return xml


def tail_ik(p, branch="down"):
    """p — рабочая точка присоски в системе корпуса; присоска смотрит вниз.
    Возвращает [поворот, плечо, локоть, запястье]."""
    d = np.asarray(p) - T_MOUNT + np.array([0, 0, CUP])   # ось запястья над присоской
    lx, ly, dz = -d[0], -d[1], d[2]                       # база хвоста развёрнута назад
    if lx >= 0: yaw = math.atan2(ly, lx); r = math.hypot(lx, ly)
    else: yaw = math.atan2(-ly, -lx); r = -math.hypot(lx, ly)
    dist = min(max(math.hypot(r, dz), abs(T2 - T1) + 1e-4), T1 + T2 - 1e-4)
    a = math.acos(max(-1, min(1, (T1**2 + dist**2 - T2**2) / (2 * T1 * dist))))
    g = math.acos(max(-1, min(1, (T1**2 + T2**2 - dist**2) / (2 * T1 * T2))))
    base = math.atan2(dz, r)
    p_, e_ = (base + a, -(math.pi - g)) if branch == "up" else (base - a, math.pi - g)
    w = -math.pi / 2 - (p_ + e_)
    w = (w + math.pi) % (2 * math.pi) - math.pi
    return np.array([yaw, p_, e_, w])


TAIL_REST = tail_ik([-0.040, 0.0, 0.095])   # присоска над задней частью спины; ниже — задевает поворотную стойку


class T(GR.G):
    def __init__(self, xml):
        super().__init__(xml)
        self.tq_t = TAIL_REST.copy()
        for j, v in zip("ypew", self.tq_t): self.d.qpos[self.m.joint(f"T_{j}").qposadr[0]] = v
        mujoco.mj_forward(self.m, self.d)
        self.suck = self.m.actuator("T_suck").id

    def step(self, q, arm=None, eye=0.0, armq=None):
        for j, v, stall, kp in (("y", self.tq_t[0], 0.44, 3.0), ("p", self.tq_t[1], 2.94, 40.0), ("e", self.tq_t[2], 2.94, 40.0),
                                ("w", self.tq_t[3], 0.44, 3.0)):
            jt = self.m.joint(f"T_{j}"); e = v - self.d.qpos[jt.qposadr[0]]; w = self.d.qvel[jt.dofadr[0]]
            self.d.ctrl[self.m.actuator(f"m_T_{j}").id] = min(stall, max(-stall, float(kp * e - 0.4 * w)))
        return super().step(q, arm, eye, armq)

    def tail_tip(self):
        b = self.d.body("T_cup"); R = b.xmat.reshape(3, 3)
        return b.xpos + R[:, 0] * 0.004


def tail_move(s, waypoints, legs=None, armq=None, eye=0.0):
    """waypoints: [(точка или углы, длительность, присоска 0/1 или None, ветвь)]"""
    q = legs or H.pose_targets(H.REACH_WORK, H.ZJ)
    for tgt, dur, suck, br in waypoints:
        st = s.tq_t.copy(); en = tail_ik(tgt, br) if br else np.array(tgt)
        if suck is not None: s.d.ctrl[s.suck] = suck
        steps = int(dur / DT)
        for i in range(steps):
            k = 0.5 - 0.5 * math.cos(math.pi * i / steps)
            s.tq_t = st + (en - st) * k
            s.step(q, None, eye, armq or getattr(s, "armq_cur", None))


def rel(s, body):
    return GR.rel(s, body)


PHONE_BEHIND = '<body name="phone" pos="-0.180 0 0.0045"><freejoint/><geom name="phone_g" type="box" size="0.0375 0.075 0.004" mass="0.2" friction="0.5 0.01 0.001" rgba=".1 .1 .12 1"/></body>'


# ---------- A. телефон со стола позади — на спину ----------
def test_pick_place(slow=1.0):
    s = T(build_tail(PHONE_BEHIND))
    zt = -(H.ZJ - 0.0085) - 0.0015         # чуть ниже верха телефона: присоска прижимается
    tail_move(s, [([-0.170, 0, zt + 0.04], 2.0 * slow, 0, "up"), ([-0.180, 0, zt + 0.002], 1.0 * slow, 0, "up")])   # «локоть вверх»: подъём не ниже −40°
    tail_move(s, [([-0.180, 0, zt + 0.002], 0.4, 1, "up"), ([-0.150, 0, 0.060], 1.5 * slow, None, "up")])
    lifted = rel(s, "phone")[2] > -0.02
    tail_move(s, [([-0.090, 0, 0.175], 2.5 * slow, None, "down"), ([-0.015, 0, 0.140], 2.5 * slow, None, "down"),
                  ([-0.015, 0, 0.088], 2.0 * slow, None, "down")])
    tail_move(s, [([-0.015, 0, 0.088], 0.5, 0, "down"), ([-0.050, 0, 0.140], 1.0, None, "down"), (list(TAIL_REST), 1.5, None, None)])
    r = rel(s, "phone")
    on_back = bool(r[2] > 0.055 and -0.075 < r[0] < 0.04)
    # прогулка с телефоном на спине и сложенным хвостом
    w = S.walk(s, seconds=6.0) if on_back else None
    r2 = rel(s, "phone")
    stays = bool(r2[2] > 0.055 and -0.08 < r2[0] < 0.045) if on_back else False
    return dict(поднял=bool(lifted), на_спине=on_back, положение_мм=np.round(r * 1000).tolist(),
                ходьба=w, не_съехал_при_ходьбе=stays)


# ---------- B. переворот со спины с помощью хвоста ----------
def up_z(s): return s.d.body("torso").xmat.reshape(3, 3)[2, 2]


def legs_push(side, k, push=0.15, pivot=-0.03):
    """Ноги стороны side давят в стол; ноги другой стороны (ось переката) убираются от стола, чтобы не подпирать."""
    q = {}
    for n in H.MOUNTS:
        sd = 1 if n[0] == "L" else -1
        p0 = H.neutral(n, 0.07)
        if sd == side: q[n] = H.ik(n, p0, -0.047 + push * k)
        else:
            x, y, yaw = H.MOUNTS[n]; a = math.radians(yaw)
            q[n] = H.ik(n, np.array([x + 0.045 * math.cos(a), y + 0.045 * math.sin(a)]), -0.047 + pivot * k)
    return q


def test_self_right(side=1, yaw_deg=90, label="", push_time=2.0, full_pitch=2.3, pivot=-0.03, claws=True):
    s = T(build_tail())
    q = np.zeros(4); mujoco.mju_axisAngle2Quat(q, np.array([1.0, 0, 0]), math.pi)
    s.d.qpos[3:7] = q; s.d.qpos[2] = 0.10; mujoco.mj_forward(s.m, s.d)
    q0 = H.pose_targets(H.REACH_WORK, H.ZJ)
    for i in range(int(1.2 / DT)): s.step(q0, None, -1.5)
    traj = []
    def run(dur, fn):
        for i in range(int(dur / DT)):
            k = i / int(dur / DT); legs, tail = fn(k)
            s.tq_t = tail; s.step(legs, None, -1.5, getattr(s, "armq_cur", None))
            if i % 400 == 0: traj.append(round(float(up_z(s)), 2))
    y = math.radians(yaw_deg) * side
    start = s.tq_t.copy()
    # 1) хвост поворачивается вбок и вытягивается к столу (для робота на спине стол — «над» спиной)
    out = np.array([y, 0.35, 0.0, 0.0])      # вбок — поднятым на 20° над горизонталью: не задевает задние ноги
    run(1.2, lambda k: (q0, start + (out - start) * k))
    # 2) хвост давит в стол (подъём плеча «вверх» по корпусу), ноги той же стороны толкают
    push = np.array([y, 1.6, -0.3, 0.0])
    run(push_time, lambda k: (legs_push(side, k, pivot=pivot), out + (push - out) * k))
    # 3) докручиваем: хвост до упора, ноги другой стороны готовятся принять вес
    full = np.array([y, full_pitch, -0.2, 0.0])
    if claws:   # клешня со стороны толчка тоже упирается в стол
        n = "L" if side > 0 else "R"; sg = 1 if side > 0 else -1
        s.armq_cur = {m: np.array(H.arm_ik(m, [0.06, sg * 0.13, 0.16] if m == n else s.tuck(m))) for m in "LR"}
    run(1.5, lambda k: (legs_push(side, 1.0, pivot=pivot), push + (full - push) * k))
    # 4) встаём
    run(2.0, lambda k: (H.pose_targets(H.REACH_WORK, H.ZJ), full + (TAIL_REST - full) * k))
    return dict(итог=("на ногах" if up_z(s) > 0.7 else ("на боку" if up_z(s) > -0.5 else "на спине")),
                наклон_по_ходу=traj[::2], label=label)


# ---------- C. передача телефона клешням в воздухе ----------
def test_handover():
    s = T(build_tail(PHONE_BEHIND))
    zt = -(H.ZJ - 0.0085) - 0.0015
    tail_move(s, [([-0.170, 0, zt + 0.04], 2.0, 0, "up"), ([-0.180, 0, zt + 0.002], 1.0, 0, "up"),
                  ([-0.180, 0, zt + 0.002], 0.4, 1, "up"), ([-0.150, 0, 0.060], 1.5, None, "up"),
                  ([-0.060, 0, 0.190], 2.5, None, "down"), ([0.030, 0, 0.190], 2.5, None, "down")])
    held_tail = rel(s, "phone")
    # клешни подходят к коротким торцам телефона с боков, кисти повёрнуты на 90° — пальцы смыкаются по толщине
    P = rel(s, "phone"); y_end = 0.075
    for n in "LR": s.grip[n] = -0.7
    tgtL = [P[0], y_end + 0.006, P[2]]; tgtR = [P[0], -(y_end + 0.006), P[2]]
    s.armq_cur = {n: np.array(H.arm_ik(n, s.tuck(n))) for n in "LR"}
    GR.path(s, [({"L": [P[0] - 0.01, 0.10, P[2] + 0.02], "R": [P[0] - 0.01, -0.10, P[2] + 0.02]}, 2.0, -0.7),
                ({"L": tgtL, "R": tgtR}, 1.5, None)])
    for n in "LR": s.grip[n] = 0.25
    s.glim = 0.12
    GR.path(s, [({"L": tgtL, "R": tgtR}, 1.0, None)])
    s.d.ctrl[s.suck] = 0
    tail_move(s, [([-0.040, 0, 0.140], 1.5, 0, "down")], armq=s.armq_cur)
    after = rel(s, "phone")
    fingers = [f"{n}_{g}" for n in "LR" for g in ("ffix", "fmovg", "handg")]
    f_claws = GR.obj_forces(s, "phone_g", fingers)
    others = set()
    for i in range(s.d.ncon):
        c = s.d.contact[i]; a = mujoco.mj_id2name(s.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom1); b = mujoco.mj_id2name(s.m, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
        if "phone_g" in (a, b): others.add(b if a == "phone_g" else a)
    held_claws = bool(after[2] > P[2] - 0.03 and f_claws > 0.5)
    return dict(хвост_держал_над_корпусом_мм=np.round(held_tail * 1000).tolist(), клешни_удержали=held_claws,
                сила_пальцев_Н=round(f_claws, 1), касаются_телефона=sorted(others), после_мм=np.round(after * 1000).tolist())


if __name__ == "__main__":
    which = _sys.argv[1:] or ["pick", "right", "handover"]
    res = {}
    if "pick" in which:
        r = test_pick_place(); res["телефон сзади на спину"] = r; print("A:", r, flush=True)
    if "right" in which:
        for side, yd in ((1, 90), (1, 60)):
            r = test_self_right(side, yd, f"хвост вбок {yd}°"); res[f"переворот, хвост {yd}°"] = r; print("B:", r, flush=True)
    if "handover" in which:
        r = test_handover(); res["передача клешням"] = r; print("C:", r, flush=True)
    json.dump(res, open("tail_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
