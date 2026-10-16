"""Физика веществ полосы препятствий: песок, гравий, галька, трава.

Песок — деформируемый грунт. Поверхность — карта высот 220 × 180 ячеек по 5 мм, которую программа меняет во время
симуляции, а MuJoCo сразу считает по ней контакты:
  * несущая способность растёт с глубиной (модель Терцаги–Беккера упрощённо): q(z) = Q0 + K·z, площадь опоры
    сферической стопы — π(2rz − z²). Пока сила на стопу больше q·A, песок под стопой продавливается — стопа тонет;
  * вытесненный объём не исчезает: он ложится валиком вокруг следа (объём сохраняется);
  * склоны круче угла естественного откоса (33°) осыпаются — стенки следа и гребни дюн оплывают;
  * стопа, идущая в песке вбок, пашет борозду: стенку следа тоже продавливает, если давит сильнее, чем она держит.
  Отсюда следы, борозды, проседание и сцепление: ноге есть во что упереться — стенка своего следа.
Гравий и галька — настоящие отдельные камни (эллипсоиды, плотность гранита 2600 кг/м³). Пока их никто не трогает,
они «спят» (режим сна MuJoCo) и почти ничего не стоят; стопа их будит — камни раскатываются и проворачиваются.
Трава — стебли (видимые пучки) и сопротивление: стопа, идущая сквозь слой стеблей, тормозится пропорционально скорости
и глубине; дёрн под ними мягкий (податливый контакт).

Пересчитать положения камней после изменения полосы (камни падают и улежатся, ~1 мин):
    python harvey_terrain.py --settle
"""
import os, sys, json, math
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
STONES = os.path.join(HERE, "assets", "world", "stones.json")
G = -0.75

# ---------- песок ----------
SAND_POS = (4.95, 0.0)
SAND_SIZE = (0.55, 0.45, 0.06, 0.01)        # полуразмеры x, y; диапазон высот 60 мм; основание
SAND_NC, SAND_NR = 221, 181                 # ячейка 5 мм
Q0, K_Q = 4.0e3, 4.0e6                      # Па, Па/м — несущая способность сухого песка (стопа Ø15 мм: 5 Н → ~7 мм)
SINK_V = 0.12                               # м/с — наибольшая скорость продавливания
REPOSE = math.radians(33)                   # угол естественного откоса
RIM = (1.2, 2.6)                            # валик вокруг следа — от 1,2 до 2,6 радиуса стопы

# ---------- трава ----------
GRASS_POS, GRASS_HALF = (3.85, 0.0), (0.50, 0.45)
BLADE_H = 0.035                             # высота слоя стеблей
GRASS_C = 0.8                               # Н·с/м — сопротивление стеблей на полностью погружённую стопу

# ---------- камни: зона, число, полуоси (мин, макс), цвета ----------
STONE_ZONES = {
    "gravel": dict(x=(5.62, 6.38), y=(-0.32, 0.32), n=240, a=(0.006, 0.011), seed=3,
                   colors=[(0.56, 0.54, 0.50), (0.46, 0.44, 0.41), (0.62, 0.58, 0.52), (0.38, 0.37, 0.36)]),
    "pebbles": dict(x=(6.57, 7.33), y=(-0.32, 0.32), n=150, a=(0.012, 0.020), seed=5,
                    colors=[(0.70, 0.67, 0.62), (0.52, 0.50, 0.47), (0.78, 0.74, 0.66), (0.42, 0.40, 0.38), (0.60, 0.52, 0.44)]),
}


def sand_heights():
    """Начальный рельеф песчаной площадки, м (строки — y, столбцы — x): основание 20 мм, дюны до 47 мм, рябь от ветра,
    по краям — откос не круче 25° (как у насыпанного песка)."""
    yy, xx = np.mgrid[0:SAND_NR, 0:SAND_NC].astype(np.float64)
    xx /= SAND_NC - 1; yy /= SAND_NR - 1
    dunes = 0.6 * (np.sin(xx * 7.5 + 0.8 * np.sin(yy * 4)) * 0.5 + 0.5) + 0.25 * (np.sin(yy * 5 + 2) * 0.5 + 0.5)
    ripple = 0.5 + 0.5 * np.sin(xx * 95 + 3 * np.sin(yy * 7) + 0.6 * np.sin(yy * 23))
    rng = np.random.default_rng(11); noise = rng.normal(0, 1, (SAND_NR, SAND_NC))
    for _ in range(3):
        noise = (noise + np.roll(noise, 1, 0) + np.roll(noise, -1, 0) + np.roll(noise, 1, 1) + np.roll(noise, -1, 1)) / 5
    h = 0.020 + 0.027 * dunes / 0.85 + 0.0025 * ripple + 0.004 * noise
    t = np.minimum(np.minimum(xx, 1 - xx) / 0.17, np.minimum(yy, 1 - yy) / 0.2).clip(0, 1)
    return h * (t * t * (3 - 2 * t))


def sand_asset():
    return f'<hfield name="h_sand" nrow="{SAND_NR}" ncol="{SAND_NC}" size="{" ".join(map(str, SAND_SIZE))}"/>'


def sand_geom():
    return (f'<geom name="sand" type="hfield" hfield="h_sand" pos="{SAND_POS[0]} {SAND_POS[1]} {G - 0.0005}" material="m_sand" '
            f'friction="0.65 0.005 0.0002" solref="0.008 1" solimp="0.9 0.97 0.002"/>')


# ---------- трава: пучки стеблей (только видны) ----------
def _tuft_mesh(name, seed, blades=24):
    rng = np.random.default_rng(seed); v, f = [], []
    for b in range(blades):
        a = rng.uniform(0, 2 * math.pi); r0 = rng.uniform(0, 0.011); h = rng.uniform(0.022, BLADE_H + 0.012)
        w = rng.uniform(0.0016, 0.0026); lean = rng.uniform(0.15, 0.5); tw = a + rng.uniform(-0.6, 0.6)
        bx, by = r0 * math.cos(a), r0 * math.sin(a); dx, dy = math.cos(a), math.sin(a); px, py = -math.sin(tw), math.cos(tw)
        segs = 4; i0 = len(v)
        for s in range(segs + 1):
            u = s / segs; z = h * u; off = lean * h * u * u; ww = w * (1 - u) + 0.0002
            cx, cy = bx + dx * off, by + dy * off
            v += [(cx - px * ww, cy - py * ww, z), (cx + px * ww, cy + py * ww, z)]
        for s in range(segs):
            k = i0 + 2 * s
            f += [(k, k + 1, k + 3), (k, k + 3, k + 2), (k, k + 3, k + 1), (k, k + 2, k + 3)]   # обе стороны
    vs = " ".join(f"{x:.5f} {y:.5f} {z:.5f}" for x, y, z in v); fs = " ".join(f"{a} {b} {c}" for a, b, c in f)
    return f'<mesh name="{name}" vertex="{vs}" face="{fs}"/>'


GRASS_MATS = [("m_blade1", "0.30 0.47 0.16"), ("m_blade2", "0.38 0.52 0.19"), ("m_blade3", "0.26 0.40 0.14"), ("m_blade4", "0.47 0.53 0.24")]


def stone_assets():
    """Материалы камней: свой цвет у каждого оттенка, матовая поверхность (у гальки — чуть глаже)."""
    return [f'<material name="m_{zone}_{i}" rgba="{c[0]} {c[1]} {c[2]} 1" specular="0.2" shininess="0.3" '
            f'roughness="{0.75 if zone == "gravel" else 0.55}" metallic="0"/>'
            for zone, z in STONE_ZONES.items() for i, c in enumerate(z["colors"])]


def grass_assets():
    a = [_tuft_mesh(f"tuft{i}", 20 + i) for i in range(4)] + stone_assets()
    a += [f'<material name="{n}" rgba="{c} 1" specular="0.15" shininess="0.3"/>' for n, c in GRASS_MATS]
    return a


def grass_geoms(n=950, seed=4):
    """Пучки стеблей по площадке травы. Высоту каждого Terrain ставит по рельефу после сборки модели."""
    rng = np.random.default_rng(seed); g = []
    for i in range(n):
        x = GRASS_POS[0] + rng.uniform(-0.94, 0.94) * GRASS_HALF[0]; y = GRASS_POS[1] + rng.uniform(-0.94, 0.94) * GRASS_HALF[1]
        g.append(f'<geom name="tuft_{i}" type="mesh" mesh="tuft{rng.integers(4)}" pos="{x:.4f} {y:.4f} {G}" euler="0 0 {rng.uniform(0, 360):.0f}" '
                 f'material="{GRASS_MATS[rng.integers(4)][0]}" contype="0" conaffinity="0" group="0"/>')
    return g


# ---------- камни ----------
def _stone_list():
    out = []
    for zone, z in STONE_ZONES.items():
        rng = np.random.default_rng(z["seed"])
        for i in range(z["n"]):
            a = rng.uniform(*z["a"]); b = a * rng.uniform(0.62, 0.9); c = a * rng.uniform(0.38, 0.62)
            ci = int(rng.integers(len(z["colors"]))); rng.uniform(0.9, 1.08)
            out.append(dict(name=f"{zone}_s{i}", size=(a, b, c), mat=f"m_{zone}_{ci}",
                            pos=(rng.uniform(*z["x"]), rng.uniform(*z["y"]), G + 0.03 + rng.uniform(0, 0.03)),
                            quat=(1.0, float(rng.normal(0, 0.15)), float(rng.normal(0, 0.15)), float(rng.normal(0, 1)))))
    return out


def stones_xml(settled=True):
    st = _stone_list()
    saved = {}
    if settled and os.path.isfile(STONES):
        saved = json.load(open(STONES, encoding="utf-8"))
    b = []
    for s in st:
        p, q = s["pos"], s["quat"]; sleep = ""
        if s["name"] in saved:
            p, q = saved[s["name"]][:3], saved[s["name"]][3:]; sleep = ' sleep="init"'
        q = np.array(q, float); q /= np.linalg.norm(q)
        b.append(f'<body name="{s["name"]}" pos="{p[0]:.5f} {p[1]:.5f} {p[2]:.5f}" quat="{q[0]:.5f} {q[1]:.5f} {q[2]:.5f} {q[3]:.5f}"{sleep}>'
                 f'<freejoint/><geom type="ellipsoid" size="{s["size"][0]:.4f} {s["size"][1]:.4f} {s["size"][2]:.4f}" density="2600" '
                 f'friction="0.75 0.01 0.001" condim="4" solref="0.004 1" material="{s["mat"]}"/></body>')
    return "".join(b)


# ---------- во время симуляции ----------
class Terrain:
    def __init__(self, sim, every=10):
        self.sim = sim; m, d = sim.m, sim.d
        self.every = every; self.k = 0; self.on = True
        self.hid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_HFIELD, "h_sand")
        self.ok = self.hid >= 0 and m.hfield_nrow[self.hid] == SAND_NR
        self.feet = {n: m.geom(f"{n}_foot").id for n in ("LF", "LM", "LB", "RF", "RM", "RB")}
        self.foot_body = {n: m.geom_bodyid[g] for n, g in self.feet.items()}
        self.r = float(m.geom_size[self.feet["LF"]][0])
        self.dirty = False; self.f6 = np.zeros(6)
        self.sink = 0.0                                     # средняя глубина следов под стопами, м (для панели)
        if self.ok:
            self.sand_g = m.geom("sand").id
            self.adr = m.hfield_adr[self.hid]; self.zr = m.hfield_size[self.hid][2]
            self.H0 = sand_heights(); self.reset_sand()
            self.cell = 2 * SAND_SIZE[0] / (SAND_NC - 1)
        gh = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_HFIELD, "h_grass")
        self.grass_g = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, "grass")
        if gh >= 0:
            nr, nc = m.hfield_nrow[gh], m.hfield_ncol[gh]
            self.GH = m.hfield_data[m.hfield_adr[gh]:m.hfield_adr[gh] + nr * nc].reshape(nr, nc) * m.hfield_size[gh][2]
            self.gsize = m.hfield_size[gh]; self.gpos = m.geom_pos[self.grass_g].copy()
            for i in range(m.ngeom):                        # пучки — на поверхность дёрна
                nm = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i)
                if nm and nm.startswith("tuft_"):
                    m.geom_pos[i][2] = self.gpos[2] + self.grass_h(*m.geom_pos[i][:2]) - 0.001
        else:
            self.GH = None
        mujoco.mj_forward(m, d)

    # --- рельеф ---
    def reset_sand(self):
        if not self.ok: return
        self.H = self.H0.copy()
        self.sim.m.hfield_data[self.adr:self.adr + SAND_NR * SAND_NC] = (self.H / self.zr).ravel()
        self.dirty = True

    def sand_h(self, x, y):
        if not self.ok: return None
        c = (x - SAND_POS[0] + SAND_SIZE[0]) / self.cell; r = (y - SAND_POS[1] + SAND_SIZE[1]) / self.cell
        if not (0 <= c < SAND_NC - 1 and 0 <= r < SAND_NR - 1): return None
        c0, r0 = int(c), int(r); fc, fr = c - c0, r - r0; H = self.H
        return float((H[r0, c0] * (1 - fc) + H[r0, c0 + 1] * fc) * (1 - fr) + (H[r0 + 1, c0] * (1 - fc) + H[r0 + 1, c0 + 1] * fc) * fr)

    def grass_h(self, x, y):
        nr, nc = self.GH.shape
        c = (x - self.gpos[0] + self.gsize[0]) / (2 * self.gsize[0]) * (nc - 1)
        r = (y - self.gpos[1] + self.gsize[1]) / (2 * self.gsize[1]) * (nr - 1)
        if not (0 <= c <= nc - 1 and 0 <= r <= nr - 1): return None
        return float(self.GH[int(round(r)), int(round(c))])

    def foot_forces(self, geom):
        """Сила (модуль: нормаль + трение) каждой стопы о данную поверхность."""
        d, m = self.sim.d, self.sim.m; out = {}
        if d.ncon == 0: return out
        g = d.contact.geom[:d.ncon]
        for n, fid in self.feet.items():
            idx = np.nonzero(((g[:, 0] == fid) & (g[:, 1] == geom)) | ((g[:, 1] == fid) & (g[:, 0] == geom)))[0]
            f = 0.0
            for i in idx:
                mujoco.mj_contactForce(m, d, int(i), self.f6); f += float(np.linalg.norm(self.f6[:3]))
            if idx.size: out[n] = f
        return out

    # --- шаг ---
    def step(self):
        """Вызывать на каждом шаге физики; работает раз в every шагов (200 Гц)."""
        self.k += 1
        if self.k % self.every or not self.on: return
        dt = self.every * self.sim.m.opt.timestep
        if self.ok: self._sand(dt)
        if self.GH is not None: self._grass()

    def _sand(self, dt):
        d = self.sim.d; r = self.r; cell = self.cell
        forces = self.foot_forces(self.sand_g)
        sinks = []
        for n, F in forces.items():
            c = d.geom_xpos[self.feet[n]]
            lx, ly = c[0] - SAND_POS[0] + SAND_SIZE[0], c[1] - SAND_POS[1] + SAND_SIZE[1]
            ci, ri = int(round(lx / cell)), int(round(ly / cell))
            R = int(math.ceil(RIM[1] * r / cell)) + 4
            c0, c1, r0, r1 = max(0, ci - R), min(SAND_NC, ci + R + 1), max(0, ri - R), min(SAND_NR, ri + R + 1)
            if c1 - c0 < 3 or r1 - r0 < 3: continue
            W = self.H[r0:r1, c0:c1]; W0 = W.copy()
            gx = (np.arange(c0, c1) * cell - lx)[None, :]; gy = (np.arange(r0, r1) * cell - ly)[:, None]
            rho2 = gx * gx + gy * gy
            zc = c[2] - (G - 0.0005)                          # центр стопы над основанием площадки
            under = rho2 < r * r
            ring = (rho2 > (1.3 * r) ** 2) & (rho2 < (2.3 * r) ** 2)
            surf = float(np.mean(W[ring])) if ring.any() else float(W.max())
            z = max(0.0, surf - (zc - r))                     # глубина следа
            ze = min(max(z, 0.0008), r)
            A = math.pi * (2 * r * ze - ze * ze) + (2 * math.pi * r * (z - r) * 0.5 if z > r else 0.0)
            cap = (Q0 + K_Q * z) * A
            sinks.append(z)
            if F <= cap: continue
            over = min(1.0, F / cap - 1.0)
            bottom = zc - np.sqrt(np.maximum(r * r - rho2, 0.0))                      # нижняя поверхность стопы
            # сетка 5 мм грубее стопы Ø15 мм: стопа касается граней между узлами, поэтому перегруженный след
            # углубляется на шаг δ (больше в центре) и не выше нижней поверхности стопы
            wgt = np.clip(1.0 - rho2 / (r * r), 0.0, 1.0)
            target = np.where(under, np.minimum(W, bottom) - over * SINK_V * dt * wgt, W)
            target = np.maximum(target, W - SINK_V * dt * 2)                            # не быстрее 2·SINK_V
            target = np.maximum(target, 0.0)
            removed = float(np.sum(W - target))
            if removed <= 0: continue
            W[:] = target
            rim = (rho2 > (RIM[0] * r) ** 2) & (rho2 < (RIM[1] * r) ** 2)
            if rim.any(): W[rim] += removed / rim.sum()                                  # объём — в валик
            self._slump(W, ~under, 3)
            self.H[r0:r1, c0:c1] = W
            rows = slice(r0, r1)
            hd = self.sim.m.hfield_data[self.adr:self.adr + SAND_NR * SAND_NC].reshape(SAND_NR, SAND_NC)
            hd[rows, c0:c1] = W / self.zr
            self.dirty = True
        if sinks: self.sink += (float(np.mean(sinks)) - self.sink) * 0.2

    def _slump(self, W, can, iters):
        """Осыпание: перепад между соседними ячейками больше tg(33°)·ячейка — избыток пересыпается вниз."""
        lim = math.tan(REPOSE) * self.cell
        for _ in range(iters):
            for axis in (0, 1):
                a = W[1:, :] if axis == 0 else W[:, 1:]; b = W[:-1, :] if axis == 0 else W[:, :-1]
                ca = can[1:, :] if axis == 0 else can[:, 1:]; cb = can[:-1, :] if axis == 0 else can[:, :-1]
                diff = a - b
                mv = np.where(diff > lim, (diff - lim) * 0.25, np.where(diff < -lim, (diff + lim) * 0.25, 0.0))
                mv = np.where(ca & cb, mv, 0.0)
                if axis == 0: W[1:, :] -= mv; W[:-1, :] += mv
                else: W[:, 1:] -= mv; W[:, :-1] += mv

    def _grass(self):
        d, m = self.sim.d, self.sim.m
        d.qfrc_applied[:] = 0
        v6 = np.zeros(6)
        for n, g in self.feet.items():
            p = d.geom_xpos[g]
            if not (abs(p[0] - GRASS_POS[0]) < GRASS_HALF[0] and abs(p[1] - GRASS_POS[1]) < GRASS_HALF[1]): continue
            h = self.grass_h(p[0], p[1])
            if h is None: continue
            soil = self.gpos[2] + h
            k = (soil + BLADE_H - (p[2] - self.r)) / BLADE_H
            if k <= 0: continue
            k = min(1.0, k)
            mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_GEOM, g, v6, 0)
            F = np.array([-GRASS_C * k * v6[3], -GRASS_C * k * v6[4], 0.0])
            mujoco.mj_applyFT(m, d, F, np.zeros(3), p, self.foot_body[n], d.qfrc_applied)


def settle(seconds=3.0):
    """Уронить камни на гравий и гальку и сохранить, как они улеглись."""
    sys.path.insert(0, HERE)
    if os.path.isfile(STONES): os.remove(STONES)
    import harvey_teleop as TP
    tp = TP.Teleop(); m, d = tp.sim.m, tp.sim.d
    names = [s["name"] for s in _stone_list()]
    for i in range(int(seconds / m.opt.timestep)):
        mujoco.mj_step(m, d)
    out = {}
    for nm in names:
        b = d.body(nm); p = b.xpos
        if p[2] < G - 0.01 or p[2] > G + 0.08: continue          # укатился/провалился — не сохраняем
        out[nm] = [round(float(v), 6) for v in list(p) + list(b.xquat)]
    json.dump(out, open(STONES, "w", encoding="utf-8"))
    print(f"камней улеглось: {len(out)} из {len(names)} → {STONES}")


if __name__ == "__main__":
    if "--settle" in sys.argv:
        settle()
