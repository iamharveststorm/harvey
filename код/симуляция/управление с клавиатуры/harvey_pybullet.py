"""Перекрёстная проверка Харви во втором движке (PyBullet / Bullet).
Та же геометрия, массы, походка и тот же регулятор с ограничением «момент — скорость»."""
import math, os, json, tempfile
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import pybullet as p
import harvey_sim as H

DT = 0.0005
ARM = 0.01   # инерция редуктора, добавляется к инерции звена


def inertial(m, x=0.0, extra=ARM):
    i = 1e-5 + extra
    return f'<inertial><origin xyz="{x} 0 0"/><mass value="{m}"/><inertia ixx="{i}" iyy="{i}" izz="{i}" ixy="0" ixz="0" iyz="0"/></inertial>'


def urdf(payload=0.0):
    links, joints = [], []
    body_mass = 1.18 + 0.42 + 0.05 + 0.04 + 0.04 + payload
    links.append(f'''<link name="torso"><inertial><origin xyz="0.012 0 {0.0254 + payload * 0.04}"/><mass value="{body_mass}"/>
      <inertia ixx="0.004" iyy="0.004" izz="0.006" ixy="0" ixz="0" iyz="0"/></inertial>
      <collision><origin xyz="0 0 0.0254"/><geometry><box size="0.15 0.14 0.07"/></geometry></collision></link>''')
    for n, (x, y, yaw) in H.MOUNTS.items():
        links.append(f'<link name="{n}_coxa">{inertial(0.065, 0.03)}</link>')
        links.append(f'<link name="{n}_femur">{inertial(0.063, 0.0225)}</link>')
        links.append(f'''<link name="{n}_tibia">{inertial(0.015, 0.05)}
          <collision><origin xyz="{H.TIB - H.FOOT_R} 0 0"/><geometry><sphere radius="{H.FOOT_R}"/></geometry></collision></link>''')
        joints.append(f'''<joint name="{n}_c" type="revolute"><parent link="torso"/><child link="{n}_coxa"/>
          <origin xyz="{x} {y} 0" rpy="0 0 {math.radians(yaw)}"/><axis xyz="0 0 1"/><limit lower="-1.05" upper="1.05" effort="3" velocity="5"/></joint>''')
        joints.append(f'''<joint name="{n}_f" type="revolute"><parent link="{n}_coxa"/><child link="{n}_femur"/>
          <origin xyz="{H.COX} 0 0"/><axis xyz="0 -1 0"/><limit lower="-1.05" upper="1.75" effort="3" velocity="5"/></joint>''')
        joints.append(f'''<joint name="{n}_k" type="revolute"><parent link="{n}_femur"/><child link="{n}_tibia"/>
          <origin xyz="{H.FEM} 0 0"/><axis xyz="0 -1 0"/><limit lower="-2.8" upper="0.52" effort="3" velocity="5"/></joint>''')
    return '<?xml version="1.0"?><robot name="harvey">' + "".join(links) + "".join(joints) + "</robot>"


class PB:
    def __init__(self, payload=0.0, friction=0.8):
        self.c = p.connect(p.DIRECT)
        p.setGravity(0, 0, -9.81); p.setTimeStep(DT); p.setPhysicsEngineParameter(numSolverIterations=100)
        fn = os.path.join(tempfile.gettempdir(), "harvey.urdf"); open(fn, "w").write(urdf(payload))
        plane = p.createCollisionShape(p.GEOM_PLANE)
        self.plane = p.createMultiBody(0, plane)
        self.r = p.loadURDF(fn, [0, 0, H.ZJ + 0.003], useFixedBase=False, flags=p.URDF_USE_INERTIA_FROM_FILE)
        self.j = {p.getJointInfo(self.r, i)[1].decode(): i for i in range(p.getNumJoints(self.r))}
        p.changeDynamics(self.plane, -1, lateralFriction=friction)
        for n in H.MOUNTS:
            p.changeDynamics(self.r, self.j[f"{n}_k"], lateralFriction=friction)
        q = H.pose_targets(H.REACH_WORK, H.ZJ)
        for n, vals in q.items():
            for jn, v in zip("cfk", vals): p.resetJointState(self.r, self.j[f"{n}_{jn}"], v)
        ids = list(self.j.values())
        p.setJointMotorControlArray(self.r, ids, p.VELOCITY_CONTROL, forces=[0] * len(ids))
        for i in ids: p.changeDynamics(self.r, i, jointDamping=0.05)
        self.kp, self.kd = 25.0, 0.3

    def step(self, q):
        tq = {}
        for n, vals in q.items():
            for jn, qd in zip("cfk", vals):
                i = self.j[f"{n}_{jn}"]; pos, vel = p.getJointState(self.r, i)[:2]
                tau = self.kp * (qd - pos) - self.kd * vel
                lim = H.TAU_STALL * max(0.0, 1 - abs(vel) / H.W0) if np.sign(tau) == np.sign(vel) else H.TAU_STALL
                tau = float(np.clip(tau, -lim, lim))
                p.setJointMotorControl2(self.r, i, p.TORQUE_CONTROL, force=tau)
                tq[f"{n}_{jn}"] = tau
        p.stepSimulation()
        return tq

    def pose(self):
        pos, orn = p.getBasePositionAndOrientation(self.r)
        r, pt, _ = p.getEulerFromQuaternion(orn)
        return np.array(pos), math.degrees(r), math.degrees(pt)

    def close(self):
        p.disconnect(self.c)


def stand(payload):
    s = PB(payload); q = H.pose_targets(H.REACH_WORK, H.ZJ); mx = 0
    for i in range(int(3 / DT)):
        tq = s.step(q)
        if i * DT > 2: mx = max(mx, max(abs(tq[f"{n}_f"]) for n in H.MOUNTS))
    pos, r, pt = s.pose(); s.close()
    return dict(femur_max=round(mx, 2), height_mm=round(pos[2] * 1000, 1))


def walk(payload, t_half, seconds=8.0, friction=0.8):
    s = PB(payload, friction); period = 2 * t_half; x0 = None; pk = 0; tilt = 0; over = []
    for i in range(int(seconds / DT)):
        t = i * DT
        q = H.pose_targets(H.REACH_WORK, H.ZJ, phase=(t / period) % 1.0, stroke=0.056 * min(1, t))
        tq = s.step(q)
        if t > 2:
            pos, r, pt = s.pose()
            if x0 is None: x0, t0 = pos, t
            tilt = max(tilt, abs(r), abs(pt))
            for k in ("RF_f", "RM_f", "LM_k", "RB_k"):
                pk = max(pk, abs(tq[k])); over.append(abs(tq[k]) > H.TAU_RATED)
    pos, r, pt = s.pose(); s.close()
    return dict(v=round((pos[0] - x0[0]) / (seconds - t0) * 100, 1), peak=round(pk, 2), over=round(100 * float(np.mean(over)), 1),
                tilt=round(tilt, 1), fell=bool(tilt > 35))


if __name__ == "__main__":
    res = {}
    for pl in (0.0, 0.5):
        res[f"стоит, груз {pl} кг"] = stand(pl); print(res, flush=True)
    for pl, th in ((0.5, 0.45), (0.5, 0.34), (0.5, 0.6)):
        res[f"идёт T/2={th}, груз {pl}"] = walk(pl, th); print(res, flush=True)
    res["идёт комфорт, μ=0.3"] = walk(0.5, 0.45, friction=0.3)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open("pybullet_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
