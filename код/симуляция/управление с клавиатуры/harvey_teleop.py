"""Управление Харви в симуляции MuJoCo.

Запуск (в одной папке с harvey_sim.py, harvey_scenarios.py, harvey_grasp.py и harvey_tail.py):
    pip install mujoco numpy
    python harvey_teleop.py            # окно симуляции + панель управления
    python harvey_teleop.py --photo    # фотореалистичное окно (Filament: PBR, мягкие тени), та же панель
    python harvey_teleop.py --console  # без панели, клавиши в консоли
    python harvey_teleop.py --test     # быстрая проверка без окон

Панель управления (отдельное маленькое окно поверх остальных):
  * кнопки работают всегда, даже если вы крутили камеру мышью в окне симуляции;
  * клавиши работают, когда активно окно панели (кликните по нему);
  * ходьба — пока клавиша или кнопка зажата: отпустили — Харви остановился.
    W / S   — вперёд / назад          A / D — повернуть влево / вправо
    Q / E   — шаг вбок влево / вправо  Пробел — стоп и отмена текущего действия
    F       — быстрый / обычный шаг    R — лечь / встать
    1 / 2 / 3 / 4 — клешни: сложить / к столу / на спину / вверх
    Клешня вручную: B — выбрать (левая / правая / обе); I / K — вперёд / назад, J / L — влево / вправо,
                    U / O — вверх / вниз (пока зажато); N — открыть пальцы, M — сжать.
                    Сжатые пальцы, коснувшиеся предмета обеими накладками, держат его (ручка, телефон, блокнот, кружка…).
    Мир: 5 — на стол, ] / [ — следующая / предыдущая зона полосы препятствий (трава, песок, гравий, галька,
         склоны 10–25°, косой склон, ступени, асфальт); G — защита края стола вкл/выкл (выключите, чтобы спуститься по доске);
         C — показать физические формы вместо деталей.
         V — адаптивная походка вкл/выкл (по умолчанию включена).
    T — хвост: взять телефон позади и положить на спину (развернитесь к нему задом)
    Y — попробовать встать со спины; удаётся не всегда — надёжно этому научит только обучение
    P — опрокинуть Харви на спину (для проверки)
    0 — начать заново        X / Esc — выход
Пока хвост выполняет действие (T, Y), ходьба не работает — панель пишет «занят»; пробел прерывает.
Старт — рабочий стол 150 × 90 см в комнате: датчики края не дают сойти с него (пока защита края включена).
Глаза при опрокидывании сами складываются наружу до упора (−105°): на спине Харви лежит на хвосте, а не на дисплеях.
"""
import math, sys, time, threading, queue, os
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import numpy as np
import mujoco
import harvey_sim as H
import harvey_scenarios as S
import harvey_tail as TT
import harvey_world as W
import harvey_gait as GA
import harvey_terrain as TR

DT = S.DT
PHONE = '<body name="phone" pos="-0.18 0.0 0.0045"><freejoint/><geom name="phone_g" type="box" size="0.0375 0.075 0.004" mass="0.2" friction="0.5 0.01 0.001" rgba=".1 .1 .12 1"/></body>'
WORLD = ('<body name="pen" pos="0.25 0.18 0.005"><freejoint/><geom type="capsule" fromto="-0.06 0 0 0.06 0 0" size="0.0045" mass="0.015" rgba=".1 .3 .8 1"/></body>'
         '<geom name="cable" type="capsule" fromto="0.35 -0.5 0.004 0.35 -0.15 0.004" size="0.004" rgba=".2 .2 .2 1"/>'
         '<geom name="note" type="box" size="0.08 0.11 0.005" pos="0.30 0.35 0.005" rgba=".9 .9 .7 1"/>'
         '<geom name="book" type="box" size="0.09 0.13 0.0125" pos="0.32 -0.38 0.0125" rgba=".5 .2 .2 1"/>')
ARM_POSES = {"tuck": (0.143, -0.024), "table": (0.185, -0.0386), "back": (-0.008, 0.088), "up": (0.110, 0.175)}   # компоновка v2


def edge_seen(sim, axis, sign, drop=0.03, max_range=0.3):
    """Лучи датчиков края смотрят наружу и вниз в сторону движения.
    По дальности и наклону корпуса (IMU) считается высота точки, куда попал луч; край — если луч
    ничего не нашёл в пределах 0,3 м (датчики VL53L4CD, луч 2,3 : 1; при наклоне корпуса дальний датчик видит стол дальше 0,2 м) или точка ниже опоры стоп больше чем на 3 см.
    Так наклон корпуса на книге не принимается за край."""
    tb = sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
    feet_z = min(sim.d.geom_xpos[sim.m.geom(f"{n}_foot").id][2] for n in H.MOUNTS) - H.FOOT_R
    world = np.array([1, 0, 0, 0, 0, 0], np.uint8); gid = np.zeros(1, np.int32)
    # 6 датчиков (компоновка v2): 2 вперёд (127; ±12), 2 назад (−104; ±14), по 1 в стороны (−28; ±52) — между средней и задней ногой
    for off in (((0.012, -0.012) if sign > 0 else (0.014, -0.014)) if axis == 0 else (-0.028,)):
        if axis == 0: o = np.array([0.127 if sign > 0 else -0.104, off, 0.004]); v = np.array([2.3 * sign, 0, -1.0])
        else: o = np.array([off, 0.052 * sign, 0.004]); v = np.array([0, 2.3 * sign, -1.0])
        p = tb.xpos + R @ o; d = R @ (v / np.linalg.norm(v))
        dist = mujoco.mj_ray(sim.m, sim.d, p, d, world, 1, tb.id, gid)
        if dist < 0 or dist > max_range: return True
        if (p + d * dist)[2] < feet_z - drop: return True
    return False


class Teleop:
    def __init__(self):
        self.reset()

    def reset(self):
        self.world = W.have_assets() and not os.environ.get("HARVEY_PLAIN")
        if self.world:            # комната, стол, реквизит, полоса препятствий, детали робота из CAD
            H.ASSETS = W.load_assets()
            xml = W.apply(TT.build_tail(PHONE, extra=W.props_xml()))
        else:                     # простой стол 120 × 120 см (если папки assets нет)
            xml = TT.build_tail(PHONE, extra=WORLD)
            xml = xml.replace('<geom name="floor" type="plane" size="3 3 0.1" friction="0.8 0.01 0.001"/>',
                              '<geom name="floor" type="box" size="0.6 0.6 0.02" pos="0 0 -0.02" friction="0.8 0.01 0.001"/>'
                              '<geom name="ground" type="plane" pos="0 0 -0.75" size="3 3 0.1"/>')
        self.sim = TT.T(xml)
        m = self.sim.m
        self.finger_ids = {n: {m.geom(f"{n}_{g}").id for g in ("ffix", "fmovg")} for n in "LR"}
        self.hand_ids = {n: m.geom(f"{n}_handg").id for n in "LR"}
        self.obj_bodies = {o: m.body(o).id for o in W.GRASPABLE if mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, o) >= 0}
        self.has_grab = self.world
        self.gait = GA.AdaptiveGait(self.sim)
        self.terrain = TR.Terrain(self.sim) if self.world else None     # песок, трава (камни — тела в модели)
        self.q0, self.v0 = self.sim.d.qpos.copy(), self.sim.d.qvel.copy()
        self._init_state()

    def soft_reset(self):
        """Вернуть всё на место, не пересоздавая модель (окно симуляции остаётся тем же)."""
        self.sim.d.ctrl[self.sim.suck] = 0; self.sim.tq_t = TT.TAIL_REST.copy()
        self.sim.d.qpos[:] = self.q0; self.sim.d.qvel[:] = self.v0; self.sim.d.ctrl[:] = 0
        self.sim.buf = []
        if self.terrain: self.terrain.reset_sand()                     # следы на песке — заново
        mujoco.mj_forward(self.sim.m, self.sim.d)
        self._init_state()

    def _init_state(self):
        self.cmd = np.zeros(3); self.vel = np.zeros(3)          # vx (м/с), vy (м/с), wz (рад/с)
        self.fast = False; self.rest = False; self.rest_k = 0.0
        self.phase = 0.0; self.t = 0.0
        self.arm_name = "tuck"
        self.armq = {n: np.array(H.arm_ik(n, self.target(n, "tuck"))) for n in "LR"}
        self.arm_from = {n: self.armq[n].copy() for n in "LR"}; self.arm_to = dict(self.arm_from); self.arm_k = 1.0
        self.holding = False; self.msg = "готов"; self.macro = None; self.mt = 0.0
        self.held = set()          # зажатые клавиши движения (режим панели)
        self.claw_sel = "LR"; self.claw_held = set(); self.claw_t = {n: self.target(n, "tuck") for n in "LR"}
        self.grip_closed = {n: False for n in "LR"}; self.grabbed = {n: None for n in "LR"}
        self.guard = True; self.zone_i = 0; self.show_phys = False
        if hasattr(self, "gait"):
            on = self.gait.on; self.gait = GA.AdaptiveGait(self.sim); self.gait.on = on   # рельеф под ногами — заново
        if hasattr(self, "sim"):
            for n in "LR": self.sim.grip[n] = -0.70
            if self.has_grab:
                for i in range(self.sim.m.neq): self.sim.d.eq_active[i] = 0

    @staticmethod
    def target(n, name):
        x, z = ARM_POSES[name]; y = H.ARM_S[n][1]
        return np.array([x, y, z])

    # ---------- команды ----------
    MOVE = {"W": (1, 0, 0), "S": (-0.7, 0, 0), "A": (0, 0, 1), "D": (0, 0, -1), "Q": (0, 0.6, 0), "E": (0, -0.6, 0)}

    def _cmd_from(self, keys):
        sp = 0.18 if self.fast else 0.12
        v = np.zeros(3)
        for c in keys:
            fx, fy, wz = self.MOVE[c]; v += [fx * sp, fy * sp, wz * 0.8]
        return v

    def key(self, k, hold=False):
        """Нажатие. hold=True — режим панели (идёт, пока зажато), иначе — до следующей команды."""
        c = (chr(k).upper() if 32 <= k < 127 else "") if isinstance(k, int) else str(k).upper()
        if c in self.MOVE:
            if self.macro:
                self.msg = "занят: хвост работает — пробел, чтобы прервать"; return
            if self.up_z() < 0.6:
                self.msg = "лежит на спине — сначала Y"; return
            if self.rest: self.rest = False
            if hold: self.held.add(c); self.cmd[:] = self._cmd_from(self.held)
            else: self.cmd[:] = self._cmd_from([c])
            self.msg = "иду"
        elif c == " ":
            self.cmd[:] = 0; self.held.clear()
            if self.macro:
                self.macro = [dict(dur=1.5, tail=TT.TAIL_REST.copy(), suck=0, legs=None)]; self._seg_start = None
                self.msg = "действие прервано"
            else:
                self.msg = "стоп"
        elif c == "F":
            self.fast = not self.fast; self.msg = "быстрый шаг" if self.fast else "обычный шаг"
            if self.held: self.cmd[:] = self._cmd_from(self.held)
        elif c == "R":
            if self.macro: self.msg = "занят — пробел, чтобы прервать"; return
            self.rest = not self.rest; self.cmd[:] = 0; self.held.clear(); self.msg = "ложится" if self.rest else "встаёт"
        elif c in ("1", "2", "3", "4"):
            name = ["tuck", "table", "back", "up"][int(c) - 1]
            self.arm_from = {n: self.armq[n].copy() for n in "LR"}
            self.arm_to = {n: np.array(H.arm_ik(n, self.target(n, name))) for n in "LR"}
            self.claw_t = {n: self.target(n, name) for n in "LR"}
            self.arm_k = 0.0; self.arm_name = name; self.msg = "клешни: " + {"tuck": "сложить", "table": "к столу", "back": "на спину", "up": "вверх"}[name]
        elif c == "T":
            if self.macro: self.msg = "уже занят"; return
            self.start_pick()
        elif c == "Y":
            if self.macro: self.msg = "уже занят"; return
            self.start_selfright()
        elif c == "P": self.flip()
        elif c == "0": self.soft_reset(); self.msg = "заново"
        elif c == "B":
            self.claw_sel = {"LR": "L", "L": "R", "R": "LR"}[self.claw_sel]
            self.msg = "клешня: " + {"L": "левая", "R": "правая", "LR": "обе"}[self.claw_sel]
        elif c in self.CLAW:
            if hold: self.claw_held.add(c)
            else: self._claw_move(self.CLAW[c], 0.01)            # консоль: 1 см за нажатие
        elif c in ("N", "M"):
            for n in self.claw_sel:
                self.grip_closed[n] = c == "M"; self.sim.grip[n] = 0.25 if c == "M" else -0.70
                if c == "N": self._release(n)
            self.msg = "пальцы сжаты" if c == "M" else "пальцы открыты"
        elif c == "G":
            self.guard = not self.guard; self.msg = "защита края " + ("включена" if self.guard else "ВЫКЛЮЧЕНА — можно сойти со стола")
        elif c == "V":
            self.gait.on = not self.gait.on; self.msg = "адаптивная походка " + ("включена" if self.gait.on else "выключена (как раньше)")
        elif c == "C":
            self.show_phys = not self.show_phys; self.msg = "показаны физические формы" if self.show_phys else "показаны детали"
        elif c in ("5", "]", "["):
            if not self.world: self.msg = "мира нет (папка assets)"; return
            self.zone_i = 0 if c == "5" else (self.zone_i + (1 if c == "]" else -1)) % len(W.ZONES)
            self.teleport(self.zone_i)

    CLAW = {"I": (1, 0, 0), "K": (-1, 0, 0), "J": (0, 1, 0), "L": (0, -1, 0), "U": (0, 0, 1), "O": (0, 0, -1)}

    def release(self, k):
        c = str(k).upper()
        if c in self.claw_held:
            self.claw_held.discard(c); return
        if c in self.held:
            self.held.discard(c); self.cmd[:] = self._cmd_from(self.held)
            if not self.held: self.msg = "стоп"

    # ---------- клешня вручную ----------
    LIM_P, LIM_E = (math.radians(-15), math.radians(175)), (math.radians(-105), math.radians(130))

    def _claw_ok(self, n, t):
        sx, sy, sz = H.ARM_S[n]
        if math.dist(t, (sx, sy, sz)) > H.A1 + H.A2 - 0.002: return None
        y, p, e = H.arm_ik(n, t)
        if not (self.LIM_P[0] <= p <= self.LIM_P[1] and self.LIM_E[0] <= e <= self.LIM_E[1]): return None
        if p < math.radians(80) and abs(y) > math.radians(15): return None     # правило: в низких позах поворот ±15°
        if abs(y) > math.radians(75): return None
        return np.array([y, p, e])

    def _claw_move(self, d, dist):
        moved = False
        for n in self.claw_sel:
            dd = np.array(d, float); dd[1] *= 1 if n == "L" else -1 if len(self.claw_sel) == 2 else 1   # обе: зеркально (влево = наружу)
            t = self.claw_t[n] + dd * dist; q = self._claw_ok(n, t)
            if q is not None:
                self.claw_t[n] = t; self.armq[n] = q; moved = True
        self.arm_k = 1.0; self.arm_name = "вручную"
        if not moved: self.msg = "дальше клешня не достаёт (пределы суставов и правила движения)"

    def _release(self, n):
        o = self.grabbed[n]
        if o is not None:
            self.sim.d.eq_active[self.sim.m.equality(f"grab_{n}_{o}").id] = 0; self.grabbed[n] = None

    def _grab_check(self):
        """Сжатые пальцы, коснувшиеся предмета обеими накладками (или накладкой и ладонью), удерживают его."""
        if not self.has_grab: return
        m, d = self.sim.m, self.sim.d
        for n in "LR":
            if not self.grip_closed[n] or self.grabbed[n] is not None: continue
            touch = {}
            for i in range(d.ncon):
                c = d.contact[i]
                for g, other in ((c.geom1, c.geom2), (c.geom2, c.geom1)):
                    if g in self.finger_ids[n] or g == self.hand_ids[n]:
                        b = m.geom_bodyid[other]
                        for o, ob in self.obj_bodies.items():
                            if b == ob: touch.setdefault(o, set()).add(g)
            for o, gs in touch.items():
                if len(gs) >= 2:
                    eq = m.equality(f"grab_{n}_{o}").id
                    b1 = d.body(f"{n}_hand"); b2 = d.body(o); R1 = b1.xmat.reshape(3, 3)
                    m.eq_data[eq][3:6] = R1.T @ (b2.xpos - b1.xpos)
                    q1i = np.zeros(4); mujoco.mju_negQuat(q1i, b1.xquat); qr = np.zeros(4); mujoco.mju_mulQuat(qr, q1i, b2.xquat)
                    m.eq_data[eq][6:10] = qr
                    d.eq_active[eq] = 1; self.grabbed[n] = o
                    self.msg = f"{'левая' if n == 'L' else 'правая'} клешня держит: {o}"
                    break

    def teleport(self, i):
        name, (x, y, zs) = W.ZONES[i]
        d = self.sim.d
        for n in "LR": self._release(n)
        zs = self.surface_z(x, y, zs)
        d.qpos[0:3] = [x, y, zs + H.ZJ + 0.006]; d.qpos[3:7] = [1, 0, 0, 0]; d.qvel[:6] = 0
        mujoco.mj_forward(self.sim.m, d)
        self.cmd[:] = 0; self.vel[:] = 0; self.held.clear(); self.macro = None
        on = self.gait.on; self.gait = GA.AdaptiveGait(self.sim); self.gait.on = on
        self.guard = name == "стол"
        self.msg = f"зона: {name}" + ("" if self.guard else " (защита края выключена)")

    def surface_z(self, x, y, default):
        """Высота поверхности под точкой (песок, камни, рельеф) — по стопам: самая высокая точка в круге 9 см."""
        m, d = self.sim.m, self.sim.d
        grp = np.array([1, 0, 0, 0, 0, 0], np.uint8); gid = np.zeros(1, np.int32); top = None
        tb = m.body("torso").id
        for dx, dy in ((0, 0), (0.09, 0.06), (0.09, -0.06), (-0.09, 0.06), (-0.09, -0.06), (0, 0.08), (0, -0.08)):
            z0 = W.G + 0.4
            for _ in range(20):                                  # стебли травы (без столкновений) — пропустить
                dist = mujoco.mj_ray(m, d, np.array([x + dx, y + dy, z0]), np.array([0, 0, -1.0]), grp, 1, tb, gid)
                if dist < 0 or m.geom_contype[gid[0]] or m.geom_conaffinity[gid[0]]: break
                z0 -= dist + 0.0005
            if dist >= 0:
                z = z0 - dist; top = z if top is None else max(top, z)
        return default if top is None or default > -0.3 else max(top, default)

    # ---------- хвост: готовые действия ----------
    def up_z(self):
        return self.sim.d.body("torso").xmat.reshape(3, 3)[2, 2]

    def start_pick(self):
        if self.up_z() < 0.7: self.msg = "сначала встать (Y)"; return
        tb = self.sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
        p = R.T @ (self.sim.d.body("phone").xpos - tb.xpos)          # «камера» нашла телефон
        p[2] = -(H.ZJ - 0.0085) - 0.0015
        d = p - TT.T_MOUNT + np.array([0, 0, TT.CUP])
        if np.linalg.norm(d) > TT.T1 + TT.T2 - 0.002 or p[0] > -0.08:
            self.msg = f"телефон вне досягаемости хвоста — развернитесь задом и подойдите (до него {np.linalg.norm(d)*100:.0f} см)"; return
        ik = TT.tail_ik
        segs = [(2.0, ik(p + [0.01, 0, 0.04], "up"), 0, None), (1.0, ik(p, "up"), 0, None), (0.4, ik(p, "up"), 1, None),
                (1.5, ik([-0.150, p[1] * 0.5, 0.06], "up"), None, None), (2.5, ik([-0.090, 0, 0.175]), None, None),
                (2.5, ik([-0.015, 0, 0.140]), None, None), (2.0, ik([-0.015, 0, 0.088]), None, None),
                (0.5, ik([-0.015, 0, 0.088]), 0, None), (1.0, ik([-0.050, 0, 0.140]), None, None), (1.5, TT.TAIL_REST.copy(), None, None)]
        self.cmd[:] = 0; self.vel[:] = 0
        self.macro = [dict(dur=d_, tail=t_, suck=s_, legs=l_) for d_, t_, s_, l_ in segs]; self.mt = 0.0; self._seg_start = None
        self.msg = "хвост берёт телефон"

    def start_selfright(self, side=1, yaw_deg=90):
        if self.up_z() > -0.3: self.msg = "Харви не на спине"; return
        y = math.radians(yaw_deg) * side; out = np.array([y, 0.35, 0.0, 0.0]); push = np.array([y, 1.6, -0.3, 0.0]); full = np.array([y, 2.3, -0.2, 0.0])   # вбок — поднятым на 20° (не задевает задние ноги), до 132°
        pn = "L" if side > 0 else "R"
        claw = {m: np.array(H.arm_ik(m, [0.06, side * 0.13, 0.16] if m == pn else self.target(m, "tuck"))) for m in "LR"}
        stand = H.pose_targets(H.REACH_WORK, H.ZJ)
        self.cmd[:] = 0; self.vel[:] = 0
        # рывок: хвост и ноги двигаются равномерно и резко (как в проверенном тесте harvey_tail.py)
        self.macro = [dict(dur=1.2, tail=out, suck=0, legs=lambda k: stand, eye=math.radians(-75), linear=True),
                      dict(dur=2.0, tail=push, suck=None, legs=lambda k: TT.legs_push(side, k, pivot=-0.03), eye=math.radians(-75), linear=True),   # как в проверенном тесте harvey_tail.py
                      dict(dur=1.5, tail=full, suck=None, legs=lambda k: TT.legs_push(side, 1.0, pivot=-0.03), eye=math.radians(-75), arm=claw, linear=True),
                      dict(dur=2.0, tail=TT.TAIL_REST.copy(), suck=None, legs=lambda k: stand, eye=0.0, linear=True),
                      dict(dur=1.5, tail=TT.TAIL_REST.copy(), suck=None, legs=lambda k: stand, eye=0.0,
                           arm={m: np.array(H.arm_ik(m, self.target(m, "tuck"))) for m in "LR"})]
        self.mt = 0.0; self._seg_start = None; self.msg = "пробую встать"

    def flip(self):
        d = self.sim.d
        q = np.zeros(4); mujoco.mju_axisAngle2Quat(q, np.array([1.0, 0, 0]), math.pi)
        d.qpos[3:7] = q; d.qpos[2] = 0.10; d.qvel[:] = 0
        if getattr(self, "prefold", True):
            for n in "LR":   # пока Харви опрокидывался, рефлекс уже сложил глаза
                d.qpos[self.sim.m.joint(f"{n}_s").qposadr[0]] = math.radians(-105)
        mujoco.mj_forward(self.sim.m, d)
        self.cmd[:] = 0; self.vel[:] = 0; self.macro = None; self.holding = False; self.msg = "перевернулся! (Y — попробовать встать)"

    def macro_step(self):
        """Возвращает цели ног/глаз/клешней на этот шаг или None, если действия нет."""
        if not self.macro: return None
        seg = self.macro[0]
        if self._seg_start is None:
            self._seg_start = self.sim.tq_t.copy(); self.mt = 0.0
            if seg.get("suck") is not None: self.sim.d.ctrl[self.sim.suck] = seg["suck"]
            if seg.get("arm") is not None:   # клешня упирается в стол сразу, резким движением
                self.armq = {n: seg["arm"][n].copy() for n in "LR"}; self.arm_from = dict(self.armq); self.arm_to = dict(self.armq); self.arm_k = 1.0
        k = min(1.0, self.mt / seg["dur"]); kk = k if seg.get("linear") else 0.5 - 0.5 * math.cos(math.pi * k)
        self.sim.tq_t = self._seg_start + (np.asarray(seg["tail"]) - self._seg_start) * kk
        legs = seg["legs"](k) if seg.get("legs") else None
        eye = seg.get("eye", 0.0)
        self.mt += DT
        if self.mt >= seg["dur"]:
            self.macro.pop(0); self._seg_start = None
            if not self.macro:
                self.macro = None
                if self.up_z() > 0.7 and "встать" in self.msg: self.msg = "встал!"
                elif "встать" in self.msg: self.msg = "не получилось — попробуйте Y ещё раз"
                elif "телефон" in self.msg:
                    tb = self.sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
                    r = R.T @ (self.sim.d.body("phone").xpos - tb.xpos)
                    self.holding = bool(r[2] > 0.055); self.msg = "телефон на спине" if self.holding else "телефон не удержался"
        return legs, eye

    # ---------- шаг управления ----------
    def gait_targets(self):
        t_half = 0.34 if self.fast else 0.45
        # плавный разгон и торможение
        self.vel += np.clip(self.cmd - self.vel, -0.0006, 0.0006)
        # край стола: как на Pico — запрет шага в сторону края (датчики спереди, сзади и по бокам)
        if self.guard and self.up_z() > 0.0:      # и на книге, и на уклоне — пока не на спине
            for axis, sign, name in ((0, 1, "впереди"), (0, -1, "сзади"), (1, 1, "слева"), (1, -1, "справа")):
                if self.vel[axis] * sign > 1e-4 and edge_seen(self.sim, axis, sign):
                    self.vel[axis] = 0; self.cmd[axis] = 0; self.held.clear(); self.msg = f"край стола {name} — стоп"
        self.rest_k = min(1, self.rest_k + DT / 1.5) if self.rest else max(0, self.rest_k - DT / 1.5)
        k = 0.5 - 0.5 * math.cos(math.pi * self.rest_k)
        reach = H.REACH_WORK + (H.REACH_REST - H.REACH_WORK) * k
        zj = H.ZJ + (H.ZJ_REST - H.ZJ) * k
        moving = np.linalg.norm(self.vel) > 1e-3 and self.rest_k == 0
        if moving:
            self.phase = (self.phase + DT * self.gait.speed_scale() / (2 * t_half)) % 1.0   # на крутом уклоне — медленнее
        q = {}; phases = {}; feet = {}; base = {}
        for n in H.MOUNTS:
            p0 = H.neutral(n, reach); h = -(zj - H.FOOT_R); s = None
            if moving:
                ph = self.phase if n in H.TRIPOD_A else (self.phase + 0.5) % 1.0
                if ph < 0.5: u = 0.5 - 2 * ph; z = 0.0
                else:
                    s = (ph - 0.5) * 2; u = -0.5 + (s - math.sin(2 * math.pi * s) / (2 * math.pi))
                    z = self.gait.swing_z(n, s) if self.gait.on else 0.025 * math.sin(math.pi * s)
                st = self.vel * t_half       # ход стопы за опорную фазу
                a = st[2] * u
                c, sn = math.cos(a), math.sin(a)
                p = np.array([c * p0[0] - sn * p0[1], sn * p0[0] + c * p0[1]]) + np.array([st[0] * u, st[1] * u])
                h += z
            else:
                p = p0
            phases[n] = s; feet[n] = p; base[n] = h
        adj = self.gait.update(DT, phases, feet) if self.up_z() > 0.5 else {n: 0.0 for n in H.MOUNTS}
        for n in H.MOUNTS:
            q[n] = H.ik(n, feet[n], base[n] + adj[n])   # адаптивная походка: опора под каждой стопой + ровный корпус
        return q

    def step(self):
        mac = self.macro_step()
        q = self.gait_targets()
        eye = 0.0
        if mac is not None:
            legs, eye = mac
            if legs is not None: q = legs
        if self.up_z() < 0.6 and mac is None:   # рефлекс Pico: при падении глаза складываются наружу-вниз до упора (−105°),
            eye = math.radians(-105)            # ниже арки хвоста — на спине Харви лежит на хвосте, а не на дисплеях
        if self.arm_k < 1:
            self.arm_k = min(1.0, self.arm_k + DT / 2.0)
            kk = 0.5 - 0.5 * math.cos(math.pi * self.arm_k)
            self.armq = {n: self.arm_from[n] + (self.arm_to[n] - self.arm_from[n]) * kk for n in "LR"}
        if self.claw_held:
            d = np.sum([self.CLAW[c] for c in self.claw_held], axis=0)
            self._claw_move(d, 0.06 * DT)                       # 6 см/с, пока зажато
        self.sim.step(q, None, eye, self.armq)
        if self.terrain: self.terrain.step()
        if int(self.t / DT) % 20 == 0: self._grab_check()
        self.t += DT

    def status(self):
        v = np.linalg.norm(self.vel[:2]) * 100
        tilt = self.sim.tilt()
        return (f"t={self.t:5.1f} с  скорость {v:4.1f} см/с  поворот {math.degrees(self.vel[2]):4.0f}°/с  "
                f"наклон {tilt:4.1f}°  клешни: {self.arm_name} [{ {'L': 'левая', 'R': 'правая', 'LR': 'обе'}[self.claw_sel] }]  "
                f"{'ТЕЛЕФОН НА СПИНЕ' if self.holding else ''}{self._where()}  — {self.msg}")

    def _where(self):
        if not self.world: return ""
        p = self.sim.d.body("torso").xpos
        held = ", ".join(f"{'Л' if n == 'L' else 'П'}: {o}" for n, o in self.grabbed.items() if o)
        return f"  место: {W.zone_at(*p)}{'  держит ' + held if held else ''}{'' if self.guard else '  [край не охраняется]'}"


class KeyReader(threading.Thread):
    """Читает нажатия в консоли без Enter (Windows — msvcrt, Linux/macOS — termios)."""
    def __init__(self):
        super().__init__(daemon=True); self.q = queue.Queue(); self.alive = True

    def run(self):
        if os.name == "nt":
            import msvcrt
            while self.alive:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\x00", "\xe0"): msvcrt.getwch(); continue
                    self.q.put(ch)
                else:
                    time.sleep(0.01)
        else:
            import termios, tty, select
            fd = sys.stdin.fileno(); old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while self.alive:
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r: self.q.put(sys.stdin.read(1))
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)


def sync_terrain(tp, v, state):
    """Следы на песке: передать изменённый рельеф в окно (не чаще 10 раз в секунду)."""
    T = tp.terrain
    if T is None or not T.dirty or time.time() - state.get("hf", 0) < 0.1: return
    try:
        v.update_hfield(T.hid)
    except Exception:
        pass
    T.dirty = False; state["hf"] = time.time()


def run_viewer():
    import mujoco.viewer
    if not sys.stdin.isatty():
        print("Запустите из консоли (терминала): клавиши читаются оттуда."); return
    tp = Teleop()
    print(__doc__)
    keys = KeyReader(); keys.start()
    try:
        with mujoco.viewer.launch_passive(tp.sim.m, tp.sim.d, show_left_ui=False, show_right_ui=False) as v:
            v.cam.distance = 0.9; v.cam.elevation = -25; v.cam.azimuth = 135
            last = time.time(); last_print = 0; st = {}
            while v.is_running():
                while not keys.q.empty():
                    ch = keys.q.get()
                    if ch.upper() in ("X", "Ч"):
                        v.close(); break
                    ru = {"Ц": "W", "Ы": "S", "Ф": "A", "В": "D", "Й": "Q", "У": "E", "А": "F", "К": "R", "П": "G", "Р": "H",
                          "И": "B", "Ш": "I", "Л": "K", "О": "J", "Д": "L", "Г": "U", "Щ": "O", "Т": "N", "Ь": "M", "С": "C",
                          "Х": "[", "Ъ": "]", "Е": "T", "Н": "Y", "З": "P"}
                    ch = ru.get(ch.upper(), ch)
                    if ch == "\x1b": v.close(); break
                    tp.key(ord(ch[0]) if ch else 0)
                with v.lock():
                    for _ in range(int(1 / 60 / DT)):
                        tp.step()
                    v.opt.geomgroup[1] = 1 if (tp.show_phys or not tp.world) else 0; v.opt.geomgroup[2] = 0 if tp.show_phys else 1
                sync_terrain(tp, v, st)
                v.cam.lookat[:] = tp.sim.d.body("torso").xpos
                v.sync()
                if time.time() - last_print > 0.5:
                    print("\r" + tp.status() + " " * 10, end="", flush=True); last_print = time.time()
                sleep = 1 / 60 - (time.time() - last)
                if sleep > 0: time.sleep(sleep)
                last = time.time()
    finally:
        keys.alive = False
        time.sleep(0.1)
        print("\nГотово.")


def run_gui(script=None, photo=False):
    """Окно симуляции + панель управления на tkinter (кнопки работают без фокуса клавиатуры).
    photo=True — окно с фотореалистичным рендером Filament (harvey_photo.py) вместо обычного.
    script — список (секунда, действие) для самопроверки (--gui-test)."""
    import tkinter as tk
    if photo:                                             # физика — в своём процессе, здесь только окно и панель
        import harvey_photo as PH
        tp = PH.RemoteTeleop()
        v = None                                          # окно «фото» — после панели (ему нужен tkinter)
    else:
        import mujoco.viewer
        tp = Teleop()
        v = mujoco.viewer.launch_passive(tp.sim.m, tp.sim.d, show_left_ui=False, show_right_ui=False)
        v.cam.distance = 0.9; v.cam.elevation = -25; v.cam.azimuth = 135
    root = tk.Tk(); root.title("Харви — управление"); root.attributes("-topmost", True); root.resizable(False, False)
    if photo:
        v = PH.PhotoView(root, tp.sim.m, tp.sim.d)
        v.cam.distance = 0.75; v.cam.elevation = -22; v.cam.azimuth = 140
    BG = "#F3EEE4"; root.configure(bg=BG)
    RU = {"Ц": "W", "Ы": "S", "Ф": "A", "В": "D", "Й": "Q", "У": "E", "А": "F", "К": "R", "Е": "T", "Н": "Y", "З": "P", "Ч": "X"}
    def norm(ch):
        ch = (ch or "").upper(); return RU.get(ch, ch)
    def mk(parent, text, cmd=None, hold=None, w=9):
        b = tk.Button(parent, text=text, width=w, height=2, relief="groove", bg="#FBF8F2", activebackground="#DDEBEC")
        if hold:
            b.bind("<ButtonPress-1>", lambda e: tp.key(hold, hold=True)); b.bind("<ButtonRelease-1>", lambda e: tp.release(hold))
        else:
            b.configure(command=cmd)
        return b
    tk.Label(root, text="Ходьба (зажмите)", bg=BG, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=3, pady=(8, 2))
    pad = tk.Frame(root, bg=BG); pad.grid(row=1, column=0, columnspan=3, padx=8)
    wbtn = mk(pad, "W ↑", hold="W")
    mk(pad, "Q ↖ вбок", hold="Q").grid(row=0, column=0); wbtn.grid(row=0, column=1); mk(pad, "E вбок ↗", hold="E").grid(row=0, column=2)
    mk(pad, "A ⟲", hold="A").grid(row=1, column=0); mk(pad, "Стоп", lambda: tp.key(" ")).grid(row=1, column=1); mk(pad, "D ⟳", hold="D").grid(row=1, column=2)
    mk(pad, "F быстро", lambda: tp.key("F")).grid(row=2, column=0); mk(pad, "S ↓", hold="S").grid(row=2, column=1); mk(pad, "R лечь", lambda: tp.key("R")).grid(row=2, column=2)
    tk.Label(root, text="Клешни", bg=BG, font=("Segoe UI", 10, "bold")).grid(row=2, column=0, columnspan=3, pady=(8, 2))
    cl = tk.Frame(root, bg=BG); cl.grid(row=3, column=0, columnspan=3, padx=8)
    for i, t in enumerate(("1 сложить", "2 к столу", "3 на спину", "4 вверх")):
        mk(cl, t, (lambda c=str(i + 1): tp.key(c)), w=9).grid(row=0, column=i)
    tk.Label(root, text="Хвост и проверки", bg=BG, font=("Segoe UI", 10, "bold")).grid(row=4, column=0, columnspan=3, pady=(8, 2))
    tl = tk.Frame(root, bg=BG); tl.grid(row=5, column=0, columnspan=3, padx=8)
    mk(tl, "T телефон\nна спину", lambda: tp.key("T"), w=11).grid(row=0, column=0)
    mk(tl, "P опрокинуть", lambda: tp.key("P"), w=11).grid(row=0, column=1)
    mk(tl, "Y встать", lambda: tp.key("Y"), w=11).grid(row=0, column=2)
    mk(tl, "0 заново", lambda: tp.key("0"), w=11).grid(row=1, column=1)
    tk.Label(root, text="Клешня вручную (зажмите)", bg=BG, font=("Segoe UI", 10, "bold")).grid(row=6, column=0, columnspan=3, pady=(8, 2))
    cw = tk.Frame(root, bg=BG); cw.grid(row=7, column=0, columnspan=3, padx=8)
    mk(cw, "B выбрать", lambda: tp.key("B")).grid(row=0, column=0); mk(cw, "I вперёд", hold="I").grid(row=0, column=1); mk(cw, "U вверх", hold="U").grid(row=0, column=2)
    mk(cw, "J влево", hold="J").grid(row=1, column=0); mk(cw, "K назад", hold="K").grid(row=1, column=1); mk(cw, "L вправо", hold="L").grid(row=1, column=2)
    mk(cw, "N открыть", lambda: tp.key("N")).grid(row=2, column=0); mk(cw, "M сжать", lambda: tp.key("M")).grid(row=2, column=1); mk(cw, "O вниз", hold="O").grid(row=2, column=2)
    tk.Label(root, text="Мир", bg=BG, font=("Segoe UI", 10, "bold")).grid(row=8, column=0, columnspan=3, pady=(8, 2))
    wf = tk.Frame(root, bg=BG); wf.grid(row=9, column=0, columnspan=3, padx=8)
    mk(wf, "[ назад", lambda: tp.key("[")).grid(row=0, column=0); mk(wf, "5 на стол", lambda: tp.key("5")).grid(row=0, column=1); mk(wf, "] дальше", lambda: tp.key("]")).grid(row=0, column=2)
    mk(wf, "G край вкл/выкл", lambda: tp.key("G"), w=13).grid(row=1, column=0, columnspan=2); mk(wf, "C формы", lambda: tp.key("C")).grid(row=1, column=2)
    status = tk.Label(root, text="", bg=BG, justify="left", wraplength=330, font=("Segoe UI", 9))
    status.grid(row=10, column=0, columnspan=3, padx=8, pady=8, sticky="w")
    # Клавиша определяется по физической кнопке, а не по букве: работает в любой раскладке.
    CYR = {"cyrillic_tse": "W", "cyrillic_yeru": "S", "cyrillic_ef": "A", "cyrillic_ve": "D", "cyrillic_shorti": "Q",
           "cyrillic_u": "E", "cyrillic_a": "F", "cyrillic_ka": "R", "cyrillic_ie": "T", "cyrillic_en": "Y",
           "cyrillic_ze": "P", "cyrillic_che": "X", "cyrillic_i": "B", "cyrillic_sha": "I", "cyrillic_el": "K", "cyrillic_o": "J",
           "cyrillic_de": "L", "cyrillic_ghe": "U", "cyrillic_shcha": "O", "cyrillic_te": "N", "cyrillic_softsign": "M",
           "cyrillic_pe": "G", "cyrillic_es": "C", "cyrillic_ha": "[", "cyrillic_hardsign": "]", "bracketleft": "[", "bracketright": "]"}
    def keyname(e):
        if sys.platform == "win32" and e.keycode:            # виртуальные коды Windows не зависят от раскладки
            k = e.keycode
            if 65 <= k <= 90 or 48 <= k <= 57: return chr(k)
            if k == 32: return " "
            if k == 27: return "ESC"
            if k == 219: return "["
            if k == 221: return "]"
        ks = (e.keysym or "").lower()
        if ks == "space": return " "
        if ks == "escape": return "ESC"
        if ks in CYR: return CYR[ks]
        if ks in ("bracketleft", "bracketright"): return "[" if ks == "bracketleft" else "]"
        if len(ks) == 1: return ks.upper()
        return norm(e.char) if e.char else ""
    pressed_at = {}
    def press(c):
        if c in ("ESC", "X"): close(); return
        if c in tp.MOVE or c in tp.CLAW:
            pressed_at[c] = time.time(); tp.key(c, hold=True)
        elif c: tp.key(c)
    def on_press_track(e):
        press(keyname(e))
    def on_release_track(e):
        c = keyname(e)
        if c in tp.MOVE or c in tp.CLAW:
            t0 = time.time()
            def maybe():                                      # автоповтор присылает пары «отпустил — нажал»
                if pressed_at.get(c, 0) <= t0: tp.release(c)
            root.after(40, maybe)
    root.bind("<KeyPress>", on_press_track); root.bind("<KeyRelease>", on_release_track)
    if photo: v.bind_keys(on_press_track, on_release_track)   # клавиши работают и в окне «фото»
    state = {"run": True, "last_print": 0}
    def close():
        state["run"] = False
        root.quit()
    root.protocol("WM_DELETE_WINDOW", close)
    def tick():
        if not state["run"]: return
        if not v.is_running(): close(); return
        t0 = time.time()
        if photo:
            if not tp.alive(): close(); return
            if tp.pull(): v.update_hfield(tp.terrain.hid)            # следы на песке пришли из процесса физики
            v.opt.geomgroup[1] = 1 if (tp.show_phys or not tp.world) else 0; v.opt.geomgroup[2] = 0 if tp.show_phys else 1
        else:
          with v.lock():
            for _ in range(int(1 / 60 / DT)): tp.step()
            v.opt.geomgroup[1] = 1 if (tp.show_phys or not tp.world) else 0; v.opt.geomgroup[2] = 0 if tp.show_phys else 1
        sync_terrain(tp, v, state)
        v.cam.lookat[:] = tp.sim.d.body("torso").xpos
        v.sync()
        if not v.is_running(): close(); return
        status.configure(text=tp.status() + (f"  [фото: {v.fps:.0f} к/с]" if photo else ""))
        root.after(max(1, int((1 / 60 - (time.time() - t0)) * 1000)), tick)
    print(__doc__)
    if script:
        log = []
        def act(a):
            kind, arg = a
            if kind == "key":   root.event_generate("<KeyPress>", keysym=arg if arg != " " else "space", when="tail")
            elif kind == "keyup": root.event_generate("<KeyRelease>", keysym=arg, when="tail")
            elif kind == "hold_btn": wbtn.event_generate("<ButtonPress-1>", when="tail")
            elif kind == "release_btn": wbtn.event_generate("<ButtonRelease-1>", when="tail")
            elif kind == "log":
                log.append(f"{arg}: {tp.status()} | корпус {np.round(tp.sim.d.body('torso').xpos[:2] * 1000).tolist()}"); print(log[-1], flush=True)
            elif kind == "quit": close()
        for t_, a in script: root.after(int(t_ * 1000), lambda a=a: act(a))
    root.after(50, tick)
    root.focus_force()
    root.mainloop()
    try: root.destroy()
    except Exception: pass
    try: v.close()
    except Exception: pass
    if photo:
        tp.close()                                         # остановить процесс физики


def run_test():
    """Сценарий без окон: проверяет ходьбу с удержанием, «занят», отмену пробелом, края стола, хвост."""
    tp = Teleop()
    def go(sec):
        for _ in range(int(sec / DT)): tp.step()
    def pos(): return np.round(tp.sim.d.body("torso").xpos[:2] * 1000).tolist()
    log = []
    def note(label): log.append(f"{label}: {tp.status()}  | корпус {pos()} мм"); print(log[-1], flush=True)
    tp.key("W", hold=True); go(2.0); note("зажал W 2 с")
    tp.release("W"); go(1.0); note("отпустил W")
    tp.key("A", hold=True); go(1.5); tp.release("A"); go(0.5); note("поворот A")
    tp.key("0"); go(0.5)
    tp.key("T"); go(3.0); tp.key("W", hold=True); go(0.5); note("W во время хвоста")
    tp.key(" "); go(2.0); note("пробел — прервать")
    tp.key("0"); go(0.5)
    tp.key("T"); go(18.5); note("T — телефон на спину")
    tp.key("S", hold=True); go(12.0); note("зажал S — к заднему краю")
    tp.release("S"); tp.key("Q", hold=True); go(12.0); note("зажал Q — к левому краю")
    tp.release("Q"); tp.key("P"); go(1.2); note("P — опрокинуть"); tp.key("W", hold=True); go(0.5); note("W на спине")
    tp.key(" "); tp.key("Y"); go(10.0); note("Y — попытка встать")
    rel = tp.sim.d.body("phone").xpos - tp.sim.d.body("torso").xpos
    print("телефон относительно корпуса, мм:", np.round(rel * 1000))


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_test()
    elif "--gui-test" in sys.argv:
        run_gui(script=[(1.0, ("key", "w")), (3.0, ("keyup", "w")), (4.5, ("log", "клавиша W зажата 2 с и отпущена")),
                        (4.6, ("key", "Cyrillic_ef")), (5.0, ("keyup", "Cyrillic_ef")), (5.1, ("log", "русская раскладка: Ф = A (поворот)")),
                        (5.0, ("hold_btn", None)), (7.0, ("release_btn", None)), (8.5, ("log", "кнопка W зажата 2 с и отпущена")),
                        (9.0, ("key", "0")), (9.5, ("key", "t")), (11.0, ("key", "w")), (11.2, ("log", "W во время хвоста")),
                        (11.5, ("key", " ")), (13.5, ("log", "пробел — прервать")), (14.0, ("quit", None))])
    elif "--photo" in sys.argv:
        run_gui(photo=True)
    elif "--console" in sys.argv or sys.platform == "darwin":   # на macOS окно MuJoCo живёт в главном потоке (mjpython)
        run_viewer()
    else:
        try:
            import tkinter  # noqa: F401
        except ImportError:
            print("tkinter не найден — включаю управление из консоли"); run_viewer()
        else:
            run_gui()
