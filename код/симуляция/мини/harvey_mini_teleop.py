"""Харви «Компакт мини» — управление с клавиатуры на рабочем столе, фотореалистичная картинка.

Физика — MuJoCo (приводы STS3032 с ограничением момента, трение, контакты — как в проверках harvey_mini.py).
Картинка — рендер Filament (PBR: цвет, нормали, шероховатость с Poly Haven, мягкие тени), как режим «фото» «Компакта».
Физика идёт в отдельном процессе, окно и панель — в основном.
Стол, комната и предметы — в реальном масштабе (лист, ручки, карандаш, кружка, наушники, зажигалка, книга, ноутбук),
салфетка перед левой клешнёй, станция зарядки на столе слева сзади.

    python harvey_mini_teleop.py            # фото-окно (Filament) + панель управления
    python harvey_mini_teleop.py --classic  # обычное окно MuJoCo (быстрее, проще картинка)
    python harvey_mini_teleop.py --test     # самопроверка без окон

Клавиши (в любой раскладке; ходьба и клешни — пока зажато):
    W / S — вперёд / назад      A / D — повернуть      Q / E — шаг вбок      F — быстрый / обычный шаг
    R — присесть / встать (для работы клешнями на столе)        Z — лечь на брюхо / встать
    Клешни: B — какая (левая / правая / обе); I / K — вперёд / назад, J / L — влево / вправо, U / O — вверх / вниз
            N — раскрыть губки, M — сжать; 1 — поджать, 2 — к столу, 3 — помахать, 4 — подать вперёд-вверх
    T — взять ручку или карандаш перед клешнёй (подойдите так, чтобы предмет лежал вдоль клешни)
    H — домой: дойти до станции и лечь на контакты (на роботе — по метке AprilTag; здесь — по положению)
    7 / 8 / 9 — глаза: грусть / интерес / радость        G — защита края стола вкл/выкл
    C — показать физические формы        0 — начать заново        X / Esc — выход
Мышь в фото-окне: левая кнопка — вращать камеру, правая или колесо — приблизить."""
import math, sys, os, time, threading
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
WORLD_DIR = os.path.join(HERE, "..", "управление с клавиатуры")
for p_ in (HERE, WORLD_DIR):
    if p_ not in sys.path: sys.path.insert(0, p_)
import harvey_mini as H
import harvey_world as W
import harvey_terrain as TR

DT = H.DT
DOCK = (-0.25, -0.15)                      # центр площадки станции на столе; Харви заходит на неё по +x
GRASPABLE = ("pen", "pen2", "pencil")
CAP_J = 22.0 * 3600                        # батарея 2S 18650 ≈ 22 Вт·ч
KT = H.STALL / 1.2                         # Н·м/А на выходе STS3032-C036 (упор 0,44 Н·м при 1,2 А)


def world_model():
    """Стол «Компакта» (реальный масштаб, PBR), предметы, салфетка, станция; детали робота из CAD."""
    geoms = "\n    ".join(W.world_geoms())
    props = W.props_xml().replace(TR.stones_xml(), "")
    xml = H.build_xml(napkin=True, world_xml=geoms + W.LIGHTS + props, visual=True, dock=True, dock_pos=DOCK)
    xml = xml.replace('<visual><global offwidth="1920" offheight="1080"/><quality shadowsize="4096"/></visual>',
                      W.VISUAL + W.asset_xml(robot=False))
    xml = xml.replace('<light pos="0.2 -0.3 1" dir="-0.2 0.3 -1" castshadow="true"/>', "")
    assets = {k: v for k, v in W.load_assets().items() if k.startswith("world/")}
    assets.update(H.load_assets())
    return xml, assets


def yaw_of(q):
    return math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))


class MiniTeleop:
    MOVE = {"W": (1, 0, 0), "S": (-0.7, 0, 0), "A": (0, 0, 1), "D": (0, 0, -1), "Q": (0, 0.7, 0), "E": (0, -0.7, 0)}
    CLAW = {"I": (1, 0, 0), "K": (-1, 0, 0), "J": (0, 1, 0), "L": (0, -1, 0), "U": (0, 0, 1), "O": (0, 0, -1)}

    def __init__(self):
        xml, assets = world_model()
        self.sim = H.Mini(xml=xml, assets=assets)
        m, d = self.sim.m, self.sim.d
        self.world = True; self.show_phys = False
        self.tq_adr = m.jnt_qposadr[m.body("torso").jntadr[0]]; self.tv_adr = m.jnt_dofadr[m.body("torso").jntadr[0]]
        self.feet = [m.geom(f"{n}_foot").id for n in H.MOUNTS]
        self.pogo = [m.geom("pogo0").id, m.geom("pogo1").id]; self.belly = m.geom("body").id
        self.energy = 0.85 * CAP_J
        self.q0, self.v0 = d.qpos.copy(), d.qvel.copy(); self.sq0 = dict(self.sim.q)
        self._init_state()

    # ---------- состояние ----------
    def _init_state(self):
        self.cmd = np.zeros(3); self.vel = np.zeros(3); self.held = set(); self.claw_held = set()
        self.fast = False; self.phase = 0.0; self.t = 0.0
        self.dz = 0.0; self.dz_t = 0.0; self.pose = "стоит"
        self.claw_sel = "LR"; self.guard = True; self.macro = None; self.msg = "готов"
        tuck = tuple(math.radians(a) for a in H.TUCK_Q)
        self.claw_p = {s: H.arm_fk(s, tuck) for s in "LR"}
        self.arm_go = {}                                        # плавный переход в готовую позу: s → (q_from, q_to, k)
        self.eyes = {"L": 0.0, "R": 0.0}
        self.charging = False

    def soft_reset(self):
        d = self.sim.d
        d.qpos[:] = self.q0; d.qvel[:] = 0; d.ctrl[:] = 0
        self.sim.q.update(self.sq0); mujoco.mj_forward(self.sim.m, d)
        self._init_state()

    # ---------- клавиши ----------
    def _cmd_from(self):
        sp = 0.08 if self.fast else 0.06; v = np.zeros(3)
        for c in self.held:
            fx, fy, wz = self.MOVE[c]; v += [fx * sp, fy * sp, wz * 0.8]
        return v

    def key(self, k, hold=False):
        k = k.upper() if isinstance(k, str) else k
        if k in self.MOVE:
            if self.macro: self.macro = None; self.msg = "действие прервано"
            if self.pose == "лежит": self.dz_t = 0.0; self.pose = "стоит"
            self.held.add(k); self.cmd = self._cmd_from(); self.msg = "иду"; return
        if k in self.CLAW:
            self.claw_held.add(k); return
        if k == " ": self.held.clear(); self.cmd[:] = 0; self.macro = None; self.msg = "стоп"
        elif k == "F": self.fast = not self.fast; self.cmd = self._cmd_from(); self.msg = "быстрый шаг" if self.fast else "обычный шаг"
        elif k == "R":
            self.dz_t = 0.016 if self.dz_t < 0.010 else 0.0; self.pose = "присел" if self.dz_t else "стоит"; self.msg = self.pose
        elif k == "Z":
            self.dz_t = 0.013 if self.pose != "лежит" else 0.0; self.pose = "лежит" if self.dz_t else "стоит"; self.msg = self.pose
        elif k == "B":
            self.claw_sel = {"LR": "L", "L": "R", "R": "LR"}[self.claw_sel]
            self.msg = "клешня: " + {"L": "левая", "R": "правая", "LR": "обе"}[self.claw_sel]
        elif k == "N":
            for s in self.claw_sel: self.sim.q[f"{s}_g"] = math.radians(-45)
            self.msg = "губки раскрыты"
        elif k == "M":
            for s in self.claw_sel: self.sim.q[f"{s}_g"] = 0.25
            self.msg = "губки сжаты"
        elif k in "1234":
            self.preset(int(k))
        elif k == "T": self.macro = self._macro_pick(); self.msg = "беру…"
        elif k == "H": self.macro = self._macro_dock(); self.msg = "иду на станцию"
        elif k in "789":
            self.eyes = {"7": {"L": -35.0, "R": -35.0}, "8": {"L": 18.0, "R": -12.0}, "9": {"L": 12.0, "R": 12.0}}[k]
            self.msg = {"7": "грустит", "8": "интересно", "9": "радуется"}[k]
        elif k == "G": self.guard = not self.guard; self.msg = "защита края " + ("вкл" if self.guard else "выкл")
        elif k == "C": self.show_phys = not self.show_phys
        elif k == "0": self.soft_reset(); self.msg = "заново"

    def release(self, k):
        k = k.upper()
        if k in self.MOVE: self.held.discard(k); self.cmd = self._cmd_from()
        if not self.held and self.msg == "иду": self.msg = "стоп"
        if k in self.CLAW: self.claw_held.discard(k)

    # ---------- клешни ----------
    def table_z(self):
        return -(H.ZJ - self.dz)              # стол в системе корпуса

    def preset(self, i):
        sel = self.claw_sel
        for s in sel:
            y = H.ARM_S[s][1]
            if i == 1: q = tuple(math.radians(a) for a in H.TUCK_Q)
            elif i == 2:
                self.dz_t = 0.016; self.pose = "присел"
                q = H.arm_ik(s, np.array([0.112, y, self.table_z() + 0.016 + 0.012]))
            elif i == 3: q = (math.radians(20), math.radians(80), math.radians(-40))
            else: q = H.arm_ik(s, np.array([0.120, y, 0.075]))
            q_from = tuple(self.sim.q[f"{s}_{j}"] for j in "ype")
            self.arm_go[s] = (np.array(q_from), np.array(q), 0.0)
        self.msg = {1: "клешни поджаты", 2: "клешни к столу", 3: "машет", 4: "подаёт"}[i]

    def _arm_step(self):
        for s, (qa, qb, k) in list(self.arm_go.items()):
            k = min(1.0, k + DT / 1.0)
            kk = 0.5 - 0.5 * math.cos(math.pi * k)
            q = qa + (qb - qa) * kk
            q[0] = qa[0] + (qb[0] - qa[0]) * max(0.0, (kk - 0.5) * 2)        # поворот — во второй половине (правило 1)
            for j, v in zip("ype", q): self.sim.q[f"{s}_{j}"] = float(v)
            self.claw_p[s] = H.arm_fk(s, tuple(q))
            if k >= 1.0: del self.arm_go[s]
            else: self.arm_go[s] = (qa, qb, k)
        if self.claw_held:
            dv = np.sum([self.CLAW[c] for c in self.claw_held], axis=0) * 0.06 * DT
            for s in self.claw_sel:
                if s in self.arm_go: continue
                v = dv.copy()
                if s == "R" and self.claw_sel == "LR": v[1] = -v[1]               # обе — зеркально
                p = self.claw_p[s] + v; q = H.arm_ik(s, p)
                if H.claw_ok(s, q) and abs(np.linalg.norm(H.arm_fk(s, q) - p)) < 0.002:
                    self.claw_p[s] = p
                    for j, val in zip("ype", q): self.sim.q[f"{s}_{j}"] = val
                else:
                    self.msg = "предел клешни (правила движения)"

    # ---------- готовые действия ----------
    def _wait(self, sec):
        n = int(sec / DT)
        for _ in range(n): yield

    def _macro_pick(self):
        """Взять предмет перед выбранной клешнёй: присесть, губки сверху, сжать, встать, поднять на 6 см."""
        s = "L" if self.claw_sel in ("L", "LR") else "R"
        tb = self.sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
        best = None
        for o in GRASPABLE:
            b = self.sim.d.body(o); p = R.T @ (b.xpos - tb.xpos)
            ax = R.T @ b.xmat.reshape(3, 3)[:, 0]; ang = abs(math.degrees(math.atan2(ax[1], ax[0])))
            ang = min(ang, 180 - ang)
            if 0.085 < p[0] < 0.150 and abs(p[1] - H.ARM_S[s][1]) < 0.022 and ang < 25:
                best = (o, p)
        if best is None:
            self.msg = "нет ручки перед клешнёй: подойдите, чтобы она лежала вдоль клешни"; return
        o, p = best
        self.sim.q[f"{s}_g"] = math.radians(-45); self.dz_t = 0.016; self.pose = "присел"
        yield from self._wait(0.8)
        def move(a, b, sec):
            n = int(sec / DT)
            for i in range(n):
                k = 0.5 - 0.5 * math.cos(math.pi * (i + 1) / n)
                q = H.arm_ik(s, a + (b - a) * k, H.JAW_END)
                for j, v in zip("ype", q): self.sim.q[f"{s}_{j}"] = v
                yield
        def body_pt(pw):
            tb_ = self.sim.d.body("torso"); return tb_.xmat.reshape(3, 3).T @ (np.array(pw) - tb_.xpos)
        pw = self.sim.d.body(o).xpos.copy()
        a = H.arm_fk(s, tuple(self.sim.q[f"{s}_{j}"] for j in "ype"), H.JAW_END)
        over = body_pt(pw + [0, 0, 0.030]); at = body_pt([pw[0], pw[1], 0.0016])
        yield from move(a, over, 1.0); yield from move(over, at, 0.8)
        self.sim.q[f"{s}_g"] = 0.25; yield from self._wait(0.6)
        self.dz_t = 0.0; self.pose = "стоит"; yield from self._wait(0.6)
        cur = H.arm_fk(s, tuple(self.sim.q[f"{s}_{j}"] for j in "ype"), H.JAW_END)
        up = body_pt(pw + [0, 0, 0.060]); yield from move(cur, up, 1.0)
        self.claw_p[s] = H.arm_fk(s, tuple(self.sim.q[f"{s}_{j}"] for j in "ype"))
        lifted = self.sim.d.body(o).xpos[2] > 0.03
        self.msg = f"{'держит' if lifted else 'не удержал'}: {o}"

    def _macro_dock(self):
        """Домой: к точке в 16 см перед станцией, развернуться по оси, зайти, лечь на контакты."""
        if self.pose == "лежит": self.dz_t = 0.0; self.pose = "стоит"; yield from self._wait(0.8)
        tb = self.sim.d.body("torso"); x0, y0 = tb.xpos[:2]
        side = 1.0 if y0 >= DOCK[1] else -1.0; way = []
        if abs(y0 - DOCK[1]) < 0.16 and x0 > DOCK[0] - 0.16:          # башенка станции на пути — сначала в сторону
            way.append(((x0, DOCK[1] + 0.17 * side), 0.015, False)); y0 = DOCK[1] + 0.17 * side
        way += [((DOCK[0] - 0.16, y0), 0.015, False), ((DOCK[0] - 0.16, DOCK[1]), 0.008, False), ((DOCK[0], DOCK[1]), 0.004, True)]
        for target, tol, slow in way:
            for _ in range(int(25 / DT)):
                tb = self.sim.d.body("torso"); pos = tb.xpos[:2]; psi = yaw_of(tb.xquat)
                e = np.array(target) - pos; c, sn = math.cos(psi), math.sin(psi)
                ex, ey = c * e[0] + sn * e[1], -sn * e[0] + c * e[1]
                vmax = 0.035 if slow else 0.06
                self.cmd = np.array([float(np.clip(2.5 * ex, -vmax, vmax)), float(np.clip(2.5 * ey, -vmax, vmax)),
                                     float(np.clip(-2.5 * psi, -0.6, 0.6))])
                if math.hypot(ex, ey) < tol and abs(psi) < math.radians(3):
                    break
                yield
        self.cmd[:] = 0
        yield from self._wait(0.6)
        self.dz_t = 0.013; self.pose = "лежит"
        yield from self._wait(1.2)
        self.msg = "на станции — " + ("заряжается" if self.charging else "контакты не замкнулись")

    # ---------- датчики ----------
    def edge_seen(self, axis, sign, max_range=0.3, drop=0.03):
        m, d = self.sim.m, self.sim.d
        tb = d.body("torso"); R = tb.xmat.reshape(3, 3)
        feet_z = min(d.geom_xpos[g][2] for g in self.feet) - H.FOOT_R
        grp = np.array([1, 0, 0, 0, 0, 0], np.uint8); gid = np.zeros(1, np.int32); zs = H.BZ0 + 0.0065
        if axis == 0:
            pts = [((H.BX1 + 0.002) if sign > 0 else (H.BX0 - 0.002), y) for y in (0.009, -0.009)]; v = np.array([2.3 * sign, 0, -1.0])
        else:
            pts = [(-0.020, (H.BY1 + 0.002) * sign)]; v = np.array([0, 3.5 * sign, -1.0])   # бок — луч положе: стопы шире корпуса
        for x, y in pts:
            o = tb.xpos + R @ np.array([x, y, zs]); dr = R @ (v / np.linalg.norm(v))
            dist = mujoco.mj_ray(m, d, o, dr, grp, 1, tb.id, gid)
            if dist < 0 or dist > max_range or (o + dr * dist)[2] < feet_z - drop:
                return True
        return False

    def _contacts_charging(self):
        d = self.sim.d; f6 = np.zeros(6); F = [0.0, 0.0]
        if d.ncon == 0: return False
        g = d.contact.geom[:d.ncon]
        for k, pg in enumerate(self.pogo):
            for i in np.nonzero(((g[:, 0] == pg) & (g[:, 1] == self.belly)) | ((g[:, 1] == pg) & (g[:, 0] == self.belly)))[0]:
                mujoco.mj_contactForce(self.sim.m, d, int(i), f6); F[k] += abs(f6[0])
        return min(F) > 0.3

    # ---------- шаг ----------
    def step(self):
        if self.macro is not None:
            try: next(self.macro)
            except StopIteration: self.macro = None
        t_half = 0.24 if self.fast else 0.30
        self.vel += np.clip(self.cmd - self.vel, -0.0004, 0.0004)
        if self.guard:
            for axis, sign, name in ((0, 1, "впереди"), (0, -1, "сзади"), (1, 1, "слева"), (1, -1, "справа")):
                if self.vel[axis] * sign > 1e-4 and int(self.t / DT) % 20 == 0 and self.edge_seen(axis, sign):
                    self.vel[axis] = 0; self.cmd[axis] = 0; self.held.clear(); self.msg = f"край стола {name} — стоп"
        self.dz += float(np.clip(self.dz_t - self.dz, -0.02 * DT, 0.02 * DT))
        moving = np.linalg.norm(self.vel) > 1e-3
        if moving: self.phase = (self.phase + DT / (2 * t_half)) % 1.0
        h0 = -(H.ZJ - H.FOOT_R) + self.dz
        for n in H.MOUNTS:
            p0 = H.neutral(n); z = 0.0; u = 0.0
            if moving:
                pp = self.phase if n in H.TRIPOD_A else (self.phase + 0.5) % 1.0
                if pp < 0.5: u = 0.5 - 2 * pp
                else:
                    s_ = (pp - 0.5) * 2; u = -0.5 + (s_ - math.sin(2 * math.pi * s_) / (2 * math.pi)); z = 0.015 * math.sin(math.pi * s_)
            a = self.vel[2] * t_half * u; c, sn = math.cos(a), math.sin(a)
            p = np.array([c * p0[0] - sn * p0[1], sn * p0[0] + c * p0[1]]) + self.vel[:2] * t_half * u
            for j, v in zip("cfk", H.leg_ik(n, p, h0 + z)): self.sim.q[f"{n}_{j}"] = v
        self._arm_step()
        for s in "LR": self.sim.q[f"{s}_s"] = math.radians(self.eyes[s])
        self.sim.step(record=False)
        # батарея: 28 приводов (ток по моменту) + Pi Zero, дисплеи, датчики; заряд на станции 12 Вт
        I = float(np.sum(np.abs(self.sim.d.ctrl))) / KT + 28 * 0.015
        self.energy -= (6.0 * I / 0.9 + 1.8) * DT
        if int(self.t / DT) % 50 == 0: self.charging = self._contacts_charging()
        if self.charging: self.energy = min(CAP_J, self.energy + 12.0 * DT)
        self.t += DT

    def status(self):
        tb = self.sim.d.body("torso"); v = np.linalg.norm(self.vel[:2]) * 100
        tilt = self.sim.tilt(); soc = 100 * self.energy / CAP_J
        sel = {"L": "левая", "R": "правая", "LR": "обе"}[self.claw_sel]
        return (f"t={self.t:5.1f} с  скорость {v:3.1f} см/с  наклон {tilt:3.1f}°  {self.pose}  клешня: {sel}  "
                f"заряд {soc:3.0f} %{' (заряжается)' if self.charging else ''}{'  НИЗКИЙ ЗАРЯД — H' if soc < 15 else ''}"
                f"{'' if self.guard else '  [край не охраняется]'}  — {self.msg}")


# ---------------- физика в отдельном процессе (для фото-окна) ----------------
def _child(qpos, seq, status, flags, cmd):
    tp = MiniTeleop(); d = tp.sim.d
    qv = np.frombuffer(qpos, dtype=np.float64); k = int(1 / 200 / DT)
    nxt = time.time(); last_st = 0.0
    while True:
        while not cmd.empty():
            c = cmd.get()
            if c[0] == "quit": return
            if c[0] == "key": tp.key(c[1], hold=c[2])
            elif c[0] == "rel": tp.release(c[1])
        for _ in range(k): tp.step()
        seq.value += 1; qv[:] = d.qpos; seq.value += 1
        t = time.time()
        if t - last_st > 0.2:
            b = tp.status().encode("utf-8")[:2000]; status[:len(b) + 1] = b + b"\0"; last_st = t
        flags[0] = int(tp.show_phys)
        nxt += k * DT; sl = nxt - time.time()
        if sl > 0: time.sleep(sl)
        elif sl < -0.25: nxt = time.time()


class RemoteMini:
    """Для панели вместо MiniTeleop: команды — в процесс физики, положение тел и строка состояния — из общей памяти."""
    MOVE, CLAW = MiniTeleop.MOVE, MiniTeleop.CLAW

    def __init__(self):
        import multiprocessing as mp
        xml, assets = world_model()
        self.sim = H.Mini(xml=xml, assets=assets); self.world = True
        ctx = mp.get_context("spawn")
        self.qpos = ctx.RawArray("d", self.sim.m.nq); self.seq = ctx.RawValue("l", 0)
        self.st = ctx.RawArray("c", 2048); self.flags = ctx.RawArray("i", 4); self.cmd = ctx.Queue()
        self.p = ctx.Process(target=_child, args=(self.qpos, self.seq, self.st, self.flags, self.cmd), daemon=True); self.p.start()
        self.qv = np.frombuffer(self.qpos, dtype=np.float64)

    @property
    def show_phys(self): return bool(self.flags[0])
    def key(self, c, hold=False): self.cmd.put(("key", c, hold))
    def release(self, c): self.cmd.put(("rel", c))
    def status(self):
        return bytes(self.st[:]).split(b"\0")[0].decode("utf-8", "ignore") or "запуск физики…"
    def alive(self): return self.p.is_alive()

    def pull(self):
        m, d = self.sim.m, self.sim.d
        for _ in range(5):
            s0 = self.seq.value
            if s0 % 2: time.sleep(0.0002); continue
            q = self.qv.copy()
            if self.seq.value == s0 and np.any(q): d.qpos[:] = q; break
        mujoco.mj_kinematics(m, d)

    def close(self):
        try: self.cmd.put(("quit",))
        except Exception: pass
        self.p.join(timeout=2)
        if self.p.is_alive(): self.p.terminate()


# ---------------- панель и окно ----------------
def keyname(e):
    if sys.platform == "win32" and e.keycode:              # коды Windows не зависят от раскладки
        k = e.keycode
        if 65 <= k <= 90 or 48 <= k <= 57: return chr(k)
        return {32: " ", 27: "ESC"}.get(k, "")
    ks = (e.keysym or "").lower()
    if ks == "space": return " "
    if ks == "escape": return "ESC"
    return ks.upper() if len(ks) == 1 else ""


def run_gui(photo=True, script=None):
    import tkinter as tk
    root = tk.Tk(); root.title("Харви мини — управление"); root.attributes("-topmost", True); root.resizable(False, False)
    BG = "#F3EEE4"; root.configure(bg=BG)
    if photo:
        sys.path.insert(0, WORLD_DIR)
        import harvey_photo as PH
        tp = RemoteMini(); v = PH.PhotoView(root, tp.sim.m, tp.sim.d, title="Харви мини — фото (Filament, PBR)")
        v.cam.distance = 0.42; v.cam.elevation = -20; v.cam.azimuth = 200
    else:
        import mujoco.viewer
        tp = MiniTeleop(); v = mujoco.viewer.launch_passive(tp.sim.m, tp.sim.d, show_left_ui=False, show_right_ui=False)
        v.cam.distance = 0.42; v.cam.elevation = -20; v.cam.azimuth = 200
    state = {"run": True}
    def close():
        state["run"] = False; root.quit()
    root.protocol("WM_DELETE_WINDOW", close)
    def mk(parent, text, cmd=None, hold=None, w=10):
        b = tk.Button(parent, text=text, width=w, height=2, relief="groove", bg="#FBF8F2", activebackground="#DDEBEC")
        if hold:
            b.bind("<ButtonPress-1>", lambda e: tp.key(hold, hold=True)); b.bind("<ButtonRelease-1>", lambda e: tp.release(hold))
        else: b.configure(command=cmd)
        return b
    rows = [("Ходьба (зажмите)", [("Q ↖ вбок", None, "Q"), ("W ↑", None, "W"), ("E вбок ↗", None, "E"),
                                  ("A ⟲", None, "A"), ("Стоп", " ", None), ("D ⟳", None, "D"),
                                  ("F быстро", "F", None), ("S ↓", None, "S"), ("R присесть", "R", None)]),
            ("Клешни", [("1 поджать", "1", None), ("2 к столу", "2", None), ("3 помахать", "3", None),
                        ("4 подать", "4", None), ("T взять ручку", "T", None), ("B выбрать", "B", None),
                        ("N раскрыть", "N", None), ("M сжать", "M", None), ("Z лечь", "Z", None)]),
            ("Клешня вручную (зажмите)", [("I вперёд", None, "I"), ("U вверх", None, "U"), ("J влево", None, "J"),
                                          ("K назад", None, "K"), ("O вниз", None, "O"), ("L вправо", None, "L")]),
            ("Харви", [("H домой", "H", None), ("7 грусть", "7", None), ("8 интерес", "8", None),
                       ("9 радость", "9", None), ("G край", "G", None), ("0 заново", "0", None)])]
    r = 0
    for title, btns in rows:
        tk.Label(root, text=title, bg=BG, font=("Segoe UI", 10, "bold")).grid(row=r, column=0, pady=(8, 2)); r += 1
        f = tk.Frame(root, bg=BG); f.grid(row=r, column=0, padx=8); r += 1
        for i, (t, k, hold) in enumerate(btns):
            mk(f, t, (lambda k=k: tp.key(k)) if k else None, hold).grid(row=i // 3, column=i % 3)
    status = tk.Label(root, text="", bg=BG, justify="left", wraplength=340, font=("Segoe UI", 9)); status.grid(row=r, column=0, padx=8, pady=8, sticky="w")
    pressed_at = {}
    def press(e):
        c = keyname(e)
        if c in ("ESC", "X"): close(); return
        if c in tp.MOVE or c in tp.CLAW: pressed_at[c] = time.time(); tp.key(c, hold=True)
        elif c: tp.key(c)
    def release(e):
        c = keyname(e)
        if c in tp.MOVE or c in tp.CLAW:
            t0 = time.time()
            root.after(40, lambda: tp.release(c) if pressed_at.get(c, 0) <= t0 else None)   # автоповтор шлёт «отпустил-нажал»
    root.bind("<KeyPress>", press); root.bind("<KeyRelease>", release)
    if photo: v.bind_keys(press, release)
    def tick():
        if not state["run"]: return
        if not v.is_running(): close(); return
        t0 = time.time()
        if photo:
            if not tp.alive(): close(); return
            tp.pull()
        else:
            with v.lock():
                for _ in range(int(1 / 60 / DT)): tp.step()
        v.opt.geomgroup[1] = 1 if tp.show_phys else 0; v.opt.geomgroup[2] = 0 if tp.show_phys else 1
        v.cam.lookat[:] = tp.sim.d.body("torso").xpos
        v.sync()
        status.configure(text=tp.status() + (f"  [{v.fps:.0f} к/с]" if photo else ""))
        root.after(max(1, int((1 / 60 - (time.time() - t0)) * 1000)), tick)
    if script:
        for t_, k in script:
            root.after(int(t_ * 1000), (lambda k=k: close() if k == "quit" else tp.key(k)))
    print(__doc__)
    root.after(50, tick); root.focus_force(); root.mainloop()
    try: root.destroy()
    except Exception: pass
    try: v.close()
    except Exception: pass
    if photo: tp.close()


def run_test():
    tp = MiniTeleop(); d = tp.sim.d
    def go(sec):
        for _ in range(int(sec / DT)): tp.step()
    def pos(): return np.round(d.body("torso").xpos[:2] * 1000).astype(int).tolist()
    log = []
    def note(s): log.append(s); print(s, "|", tp.status(), "| корпус", pos(), "мм", flush=True)
    go(0.5)
    tp.key("W", hold=True); go(2.0); tp.release("W"); go(0.5); note("W 2 с")
    tp.key("A", hold=True); go(1.5); tp.release("A"); go(0.5); note("поворот A 1,5 с")
    tp.key("Q", hold=True); go(1.5); tp.release("Q"); go(0.5); note("вбок Q 1,5 с")
    tp.key("3"); go(1.5); note("3 — помахать")
    tp.key("1"); go(1.5); note("1 — поджать")
    # к ручке: поставить Харви так, чтобы ручка лежала перед левой клешнёй
    tp.soft_reset(); qa, va = tp.tq_adr, tp.tv_adr
    pen = d.body("pen").xpos.copy()
    d.qpos[qa:qa + 3] = [pen[0] - 0.120, pen[1] - H.ARM_S["L"][1], H.ZJ + 0.003]; d.qpos[qa + 3:qa + 7] = [1, 0, 0, 0]; d.qvel[va:va + 6] = 0
    mujoco.mj_forward(tp.sim.m, d); go(0.8)
    tp.key("B"); tp.key("T"); go(5.5); note("T — взять ручку")
    pen_up = float(d.body("pen").xpos[2])
    tp.key("4"); go(1.5); note("4 — подать"); pen_give = float(d.body("pen").xpos[2])
    tp.soft_reset(); go(0.5)
    tp.key("H"); go(30.0); note("H — домой на станцию")
    tp.energy = 0.10 * CAP_J; e0 = tp.energy; go(3.0); note("заряд на станции")
    res = {"ручка_поднята_мм": round(pen_up * 1000), "ручка_подана_мм": round(pen_give * 1000), "заряжается": tp.charging,
           "заряд_растёт": bool(tp.energy > e0)}
    tp.soft_reset(); go(0.3)
    tp.key("Q", hold=True); go(12.0); tp.release("Q"); go(0.5); note("Q к левому краю стола")
    res["стоп_у_края_y_мм"] = pos()[1]; res["край_стола_y_мм"] = 450; res["на_столе"] = bool(d.body("torso").xpos[2] > 0.0)
    print("итог:", res, flush=True)
    return res


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    elif "--gui-test" in sys.argv:
        run_gui(photo="--classic" not in sys.argv, script=[(2.0, "3"), (4.0, "1"), (6.0, "quit")])
    else:
        run_gui(photo="--classic" not in sys.argv)
