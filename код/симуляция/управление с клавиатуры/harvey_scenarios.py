"""Сценарии проверки Харви «Компакт» v2 в MuJoCo: поверхности, препятствия, край стола,
уклоны, толчки, отказ ноги, разряженная батарея, протирка стола, разброс параметров.
Запуск: python harvey_scenarios.py <имя_сценария|all>"""
import math, sys, json
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco
import harvey_sim as H

DT = 0.0005


class Sim3(H.Sim2):
    def __init__(self, payload=0.0, obj=None, friction=0.8, mass_scale=1.0, tscale=1.0, latency=0.0,
                 noise_deg=0.0, world_extra="", table_edge=None, gravity_tilt=0.0, dead=(), seed=0, tip_pad=False):
        xml = H.build_xml(payload, body_mass=1.18 * mass_scale, obj=obj)
        xml = xml.replace('friction="0.8 0.01 0.001"/>\n    <body name="torso"', f'friction="{friction} 0.01 0.001"/>\n    <body name="torso"')
        xml = xml.replace('<geom name="floor" type="plane" size="3 3 0.1" friction="0.8 0.01 0.001"/>',
                          f'<geom name="floor" type="plane" size="3 3 0.1" friction="{friction} 0.01 0.001"/>')
        if table_edge is not None:   # стол заканчивается на x = table_edge, ниже — пол в 75 см
            xml = xml.replace(f'<geom name="floor" type="plane" size="3 3 0.1" friction="{friction} 0.01 0.001"/>',
                              f'<geom name="floor" type="box" size="0.6 0.6 0.02" pos="{table_edge - 0.6} 0 -0.02" friction="{friction} 0.01 0.001"/>'
                              f'<geom name="ground" type="plane" pos="0 0 -0.75" size="3 3 0.1"/>')
        if tip_pad:
            tp = f"{H.TIP[0]} 0 {H.TIP[1]}"
            xml = xml.replace(f'<body name="L_tip" pos="{tp}"><geom type="sphere" size="0.003" mass="0.001" contype="0" conaffinity="0"/></body>',
                              f'<body name="L_tip" pos="{tp}"><geom name="pad" type="sphere" size="0.008" mass="0.003" friction="0.4 0.01 0.001" rgba="1 1 1 1"/></body>')
        xml = xml.replace('friction="1.0 0.01 0.001"', f'friction="{friction} 0.01 0.001"')   # стопы: в MuJoCo берётся максимум из пары
        xml = xml.replace("</worldbody>", world_extra + "</worldbody>")
        self.m = mujoco.MjModel.from_xml_string(xml)
        if gravity_tilt:
            a = math.radians(gravity_tilt)
            self.m.opt.gravity[:] = [-9.81 * math.sin(a), 0, -9.81 * math.cos(a)]   # +x — вверх по уклону
        for g in range(self.m.ngeom):          # группа 0 — стол и предметы мира, 1 — робот
            if self.m.geom_group[g] < 2:    # группа 2 — видимые детали из CAD (мир harvey_world), их не трогаем
                b = self.m.geom_bodyid[g]          # 1 — робот (всё, что растёт из корпуса), 0 — мир и предметы
                self.m.geom_group[g] = 1 if (b != 0 and self.m.body_rootid[b] == self.m.body('torso').id) else 0
        self.d = mujoco.MjData(self.m)
        names = [f"{n}_{j}" for n in H.MOUNTS for j in "cfk"] + H.ARM_JOINTS
        self.jid = {k: self.m.joint(k).qposadr[0] for k in names}
        self.vid = {k: self.m.joint(k).dofadr[0] for k in names}
        self.aid = {k: self.m.actuator(f"m_{k}").id for k in names}
        q = H.pose_targets(H.REACH_WORK, H.ZJ)
        for n, (qc, qf, qk) in q.items():
            for j, v in zip("cfk", (qc, qf, qk)):
                self.d.qpos[self.jid[f"{n}_{j}"]] = v
        self.arm_t = {n: self.tuck(n) for n in "LR"}
        for n in "LR":
            for j, v in zip("ype", H.arm_ik(n, self.arm_t[n])):
                self.d.qpos[self.jid[f"{n}_{j}"]] = v
        mujoco.mj_forward(self.m, self.d)
        self.kp, self.kd, self.kpa, self.kda, self.kp32, self.kd32 = 25.0, 0.3, 80.0, 0.6, 3.0, 0.05
        self.tscale, self.dead = tscale, set(dead)
        self.lag = max(0, int(latency / DT)); self.buf = []
        self.rng = np.random.default_rng(seed); self.noise = math.radians(noise_deg)
        self.tq = {}

    def step(self, q, arm=None, eye=0.0, armq=None):
        d = self.d
        tgt = {}
        for n, vals in q.items():
            for j, v in zip("cfk", vals): tgt[f"{n}_{j}"] = v
        for n in "LR":
            y, p, e = armq[n] if armq else H.arm_ik(n, (arm or self.arm_t)[n])
            tgt[f"{n}_y"], tgt[f"{n}_p"], tgt[f"{n}_e"], tgt[f"{n}_r"] = y, p, e, 0.0
        if isinstance(eye, dict): tgt["L_s"], tgt["R_s"] = eye["L"], eye["R"]     # у каждого глаза своя цель
        else: tgt["L_s"] = tgt["R_s"] = eye
        for n in "LR":     # правило компоновки v2: пока своя клешня поднята (≥ 60°), глаз отклонён наружу ≥ 20°
            if tgt[f"{n}_p"] >= math.radians(60):
                tgt[f"{n}_s"] = min(tgt[f"{n}_s"], math.radians(-20))
        self.buf.append(tgt)
        cmd = self.buf.pop(0) if len(self.buf) > self.lag else self.buf[0]
        out = {}
        for k, qd in cmd.items():
            meas = d.qpos[self.jid[k]] + (self.rng.normal(0, self.noise) if self.noise else 0.0)
            e = qd - meas; w = d.qvel[self.vid[k]]
            stall, w0 = H.LIMITS.get(k, (H.TAU_STALL, H.W0))
            stall *= self.tscale; w0 *= self.tscale
            if k[1] == "_" and k[2] in "yrs":   # STS3032: поворот плеча, запястье, стебельки
                kp, kd = self.kp32, self.kd32
            elif k[1] == "_":                   # STS3215 клешни
                kp, kd = self.kpa, self.kda
            else:                               # ноги
                kp, kd = self.kp, self.kd
            tau = kp * e - kd * w
            lim = stall * max(0.0, 1 - abs(w) / w0) if (tau > 0) == (w > 0) and tau != 0 and w != 0 else stall
            tau = min(lim, max(-lim, float(tau)))         # (без np.clip — быстрее в 5 раз, результат тот же)
            if k[:2] in self.dead: tau = 0.0
            d.ctrl[self.aid[k]] = tau
            out[k] = (tau, w)
        mujoco.mj_step(self.m, d)
        self.tq = out
        return out

    def tilt(self):
        r, p = H.rpy(self.d.body("torso").xquat)
        return max(abs(r), abs(p))

    def fallen(self):
        return self.tilt() > 35 or self.d.body("torso").xpos[2] < 0.015


def walk(sim, seconds=8.0, t_half=0.45, stroke=0.056, lift=0.025, stop_fn=None, push=None, payload_check=False):
    period = 2 * t_half
    x0 = None; maxtilt = 0; stopped_at = None; margins = []; peak = 0; over = []
    for i in range(int(seconds / DT)):
        t = i * DT
        st = stroke * min(1.0, t)
        if stop_fn and stopped_at is None and stop_fn(sim):
            stopped_at = t
        if stopped_at is not None:
            q = H.pose_targets(H.REACH_WORK, H.ZJ)
        else:
            q = H.pose_targets(H.REACH_WORK, H.ZJ, phase=(t / period) % 1.0, stroke=st, lift=lift)
        if push and push[0] <= t < push[0] + push[1]:
            sim.d.xfrc_applied[sim.m.body("torso").id][:3] = push[2]
        else:
            sim.d.xfrc_applied[sim.m.body("torso").id][:3] = 0
        tq = sim.step(q)
        if t > 2.0:
            if x0 is None: x0, t0 = sim.d.body("torso").xpos.copy(), t
            maxtilt = max(maxtilt, sim.tilt())
            for k in ("RF_f", "RM_f", "LM_k", "RB_k"):
                peak = max(peak, abs(tq[k][0])); over.append(abs(tq[k][0]) > H.TAU_RATED * sim.tscale)
            if i % 40 == 0: margins.append(sim.com_margin())
        if sim.fallen():
            return dict(fell=True, t=round(t, 2), tilt=round(sim.tilt(), 1))
    x1 = sim.d.body("torso").xpos
    v = (x1[0] - x0[0]) / (seconds - t0) * 100 if x0 is not None else 0
    return dict(fell=False, v=round(v, 1), tilt=round(maxtilt, 1), margin=round(min(margins) * 1000) if margins else None,
                peak=round(peak, 2), over=round(100 * float(np.mean(over)), 1) if over else 0, stopped_at=stopped_at,
                x_end=round(float(x1[0]) * 1000))


EDGE_Y = 0.012          # датчики края вперёд — на передней стенке под клешнями (компоновка v2)
BLOCKED = {"n": 0, "total": 0}


def edge_sensor(sim, thresh=0.15):   # VL53L4CD: над столом луч ~112 мм, порог 150 мм с запасом
    tb = sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
    hit = False
    for y in (EDGE_Y, -EDGE_Y):
        p = tb.xpos + R @ np.array([0.127, y, 0.004])
        v = R @ np.array([2.3, 0, -1.0]); v /= np.linalg.norm(v)   # луч 2,3 : 1 (~23,5° вниз), было 1,9 : 1 под VL6180X
        gid = np.zeros(1, np.int32)
        world = np.array([1, 0, 0, 0, 0, 0], np.uint8); robot = np.array([0, 1, 0, 0, 0, 0], np.uint8)
        dist = mujoco.mj_ray(sim.m, sim.d, p, v, world, 1, tb.id, gid)
        dr = mujoco.mj_ray(sim.m, sim.d, p, v, robot, 0, tb.id, gid)   # не загораживает ли луч сам робот
        BLOCKED["total"] += 1
        if 0 <= dr < (dist if dist >= 0 else 1.0): BLOCKED["n"] += 1
        if dist < 0 or dist > thresh: hit = True
    return hit


def feet_x(sim):
    return [float(sim.d.geom_xpos[sim.m.geom(f"{n}_foot").id][0]) for n in H.MOUNTS]


# ---------------- сценарии ----------------
def sc_surfaces():
    out = {}
    for name, mu in (("дерево μ=0.8", 0.8), ("чистое стекло μ=0.6", 0.6), ("глянцевая бумага, пыль μ=0.3", 0.3), ("очень скользко μ=0.15", 0.15)):
        out[name] = walk(Sim3(0.5, friction=mu))
    return out


def sc_obstacles():
    out = {}
    cable = '<geom name="cable" type="capsule" fromto="0.25 -0.4 0.004 0.25 0.4 0.004" size="0.004" friction="0.6 0.01 0.001"/>'
    note = '<geom name="note" type="box" size="0.15 0.4 0.005" pos="0.40 0 0.005" friction="0.8 0.01 0.001"/>'
    book = '<geom name="book" type="box" size="0.15 0.4 0.0125" pos="0.40 0 0.0125" friction="0.8 0.01 0.001"/>'
    for name, xml, lift in (("кабель Ø8 мм, подъём стопы 25", cable, 0.025), ("тетрадь 10 мм, подъём 25", note, 0.025),
                            ("книга 25 мм, подъём 25", book, 0.025), ("книга 25 мм, подъём 40", book, 0.040)):
        r = walk(Sim3(0.0, world_extra=xml), seconds=10.0, lift=lift)
        r["перебрался"] = (not r["fell"]) and r.get("x_end", 0) > 330
        out[name] = r
    return out


def sc_edge():
    out = {}
    for name, th, lat in (("комфортно, задержка 0", 0.45, 0.0), ("комфортно, задержка 50 мс", 0.45, 0.05),
                          ("быстро, задержка 50 мс", 0.34, 0.05), ("быстро, задержка 150 мс", 0.34, 0.15)):
        s = Sim3(0.0, table_edge=0.40, latency=lat)
        r = walk(s, seconds=7.0, t_half=th, stop_fn=edge_sensor)
        fx = feet_x(s)
        r["стопы до края, мм"] = round((0.40 - max(fx)) * 1000)
        r["упал со стола"] = bool(s.d.body("torso").xpos[2] < -0.1 or r["fell"])
        r["луч загорожен роботом, %"] = round(100 * BLOCKED["n"] / max(1, BLOCKED["total"]), 1)
        BLOCKED["n"] = BLOCKED["total"] = 0
        out[name] = r
    return out


def sc_slopes():
    out = {}
    for deg in (10, 15, 20, 25):
        out[f"вверх по уклону {deg}°"] = walk(Sim3(0.5, gravity_tilt=deg))
        out[f"поперёк уклона {deg}° стоя"] = stand_tilt(deg)
    return out


def stand_tilt(deg):
    s = Sim3(0.5)
    a = math.radians(deg); s.m.opt.gravity[:] = [0, -9.81 * math.sin(a), -9.81 * math.cos(a)]
    q = H.pose_targets(H.REACH_WORK, H.ZJ)
    y0 = s.d.body("torso").xpos[1]
    for i in range(int(4 / DT)):
        s.step(q)
        if s.fallen(): return dict(fell=True)
    return dict(fell=False, сполз_мм=round(abs(s.d.body("torso").xpos[1] - y0) * 1000, 1), margin=round(s.com_margin() * 1000))


def sc_push():
    out = {}
    for name, f in (("тычок пальцем сбоку 5 Н·0,1 с", [0, 5, 0]), ("толчок 15 Н·0,1 с", [0, 15, 0]), ("удар 30 Н·0,1 с", [0, 30, 0]),
                    ("толчок спереди 15 Н", [-15, 0, 0])):
        out[name + " (стоит)"] = walk(Sim3(0.5), seconds=5.0, stroke=0.0, push=(3.0, 0.1, f))
        out[name + " (идёт)"] = walk(Sim3(0.5), seconds=5.0, push=(3.0, 0.1, f))
    return out


def sc_failure():
    out = {}
    out["нога RM отключилась, стоит"] = walk(Sim3(0.0, dead=("RM",)), seconds=5.0, stroke=0.0)
    out["нога RM отключилась, идёт триподом"] = walk(Sim3(0.0, dead=("RM",)), seconds=6.0)
    out["нога RF отключилась, стоит"] = walk(Sim3(0.5, dead=("RF",)), seconds=5.0, stroke=0.0)
    return out


def sc_battery():
    out = {}
    for name, ts in (("полный заряд 12,6 В", 1.0), ("половина 11,1 В", 0.88), ("почти разряжен 10,2 В", 0.81)):
        out[name + ", груз 0,5 кг, комфорт"] = walk(Sim3(0.5, tscale=ts))
        out[name + ", груз 0,5 кг, быстро"] = walk(Sim3(0.5, tscale=ts), t_half=0.34)
    return out


def sc_random(n=6):
    rows = []
    for k in range(n):
        rng = np.random.default_rng(100 + k)
        p = dict(friction=float(rng.uniform(0.5, 1.0)), mass_scale=float(rng.uniform(0.9, 1.15)),
                 tscale=float(rng.uniform(0.8, 1.0)), latency=float(rng.uniform(0.0, 0.03)), noise_deg=0.2, seed=k)
        r = walk(Sim3(float(rng.uniform(0, 0.8)), **p), seconds=6.0)
        r.update({kk: round(v, 2) for kk, v in p.items() if kk != "seed"})
        rows.append(r)
    return rows


PRESS = 0.006


def sc_wipe():
    """Левая клешня с салфеткой (мягкая подушечка) трёт стол зигзагом, прижимая её вниз."""
    s = Sim3(0.0, tip_pad=True)
    table_z = -H.ZJ
    press = PRESS
    path = []
    for i in range(7):
        x = 0.145 + 0.007 * i                     # от плеча (105; 30): 40…82 мм вперёд, ±15 мм вбок
        path += [(x, 0.015), (x, 0.045)] if i % 2 == 0 else [(x, 0.045), (x, 0.015)]
    q = H.pose_targets(H.REACH_WORK, H.ZJ)
    arm = {n: s.tuck(n) for n in "LR"}
    pad = s.m.geom("pad").id; floor = s.m.geom("floor").id
    forces, peak, margins = [], 0, []
    start = s.tuck("L")
    first = np.array([path[0][0], path[0][1], table_z + 0.008 - press])
    for i in range(int(1.0 / DT)):
        arm["L"] = H.smooth(start, first, i * DT); s.step(q, arm)
    for a, b in zip(path[:-1], path[1:]):
        steps = int(0.6 / DT)
        for i in range(steps):
            k = i / steps
            p = np.array([a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, table_z + 0.008 - press])
            arm["L"] = p; tq = s.step(q, arm)
            peak = max(peak, abs(tq["L_p"][0]), abs(tq["L_e"][0]))
            if i % 20 == 0:
                fz = 0.0
                for c in s.d.contact[: s.d.ncon]:
                    if {c.geom1, c.geom2} == {pad, floor}:
                        f6 = np.zeros(6); mujoco.mj_contactForce(s.m, s.d, list(s.d.contact[: s.d.ncon]).index(c), f6); fz += f6[0]
                forces.append(fz); margins.append(s.com_margin())
    forces = np.array(forces)
    return dict(сила_прижима_Н=round(float(forces.mean()), 2), мин=round(float(forces.min()), 2), макс=round(float(forces.max()), 2),
                касание_процент=round(100 * float(np.mean(forces > 0.2)), 1), пик_момента=round(peak, 2),
                запас_устойчивости_мм=round(min(margins) * 1000), упал=s.fallen())


SCEN = dict(surfaces=sc_surfaces, obstacles=sc_obstacles, edge=sc_edge, slopes=sc_slopes, push=sc_push,
            failure=sc_failure, battery=sc_battery, random=sc_random, wipe=sc_wipe)

if __name__ == "__main__":
    names = sys.argv[1:] or ["all"]
    if names == ["all"]: names = list(SCEN)
    for n in names:
        res = SCEN[n]()
        print(f"== {n}", flush=True)
        print(json.dumps(res, ensure_ascii=False, indent=1, default=str), flush=True)
        with open(f"scen_{n}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1, default=str)
