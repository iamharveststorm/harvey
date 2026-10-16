"""Режим «фото»: окно симуляции с фотореалистичным рендером Filament (PBR) вместо классического OpenGL MuJoCo.

Что даёт Filament (встроен в MuJoCo 3.15, тот же pip-пакет):
  * физически корректные материалы (PBR): цвет + карта нормалей + шероховатость/затенение (ORM) с Poly Haven,
    металл у винтов и стали, матовый пластик, мягкая резина стоп;
  * мягкие тени с размытием, освещение от окружения (IBL), тональная компрессия и сглаживание;
  * следы на песке: изменённый рельеф перезагружается в рендер раз в 1,5 с (≈ 0,15 с — короткая заминка картинки);
  * физика идёт в отдельном процессе (RemoteTeleop), окно и панель — в основном: оба ядра работают параллельно.
Управление то же, что в обычном окне (панель + клавиши). Камера — мышью в окне «фото»:
  левая кнопка — вращать, правая (или колёсико) — приблизить/отдалить.
Клавиши работают и в окне «фото»: ходьба, клешни, мир — как на панели.
Кадр рисуется вне экрана (Filament без окна) и показывается в окне tkinter — так работает на любой ОС.
Запуск:  python harvey_teleop.py --photo"""
import sys, time, threading
import multiprocessing as mp
import numpy as np
import mujoco
from mujoco.experimental.studio import renderer as studio_renderer


# ---------------- физика в отдельном процессе ----------------
# Рендер Filament и Python-поток физики в одном процессе иногда портят друг другу память (сбой примерно в половине
# запусков). Поэтому в режиме «фото» физика живёт в своём процессе: положение тел, рельеф песка и строка состояния
# передаются через общую память, команды клавиш — через очередь. Оба ядра работают параллельно.
def _child(qpos, seq, hf, hver, status, flags, cmd):
    import harvey_teleop as TP
    tp = TP.Teleop(); m, d = tp.sim.m, tp.sim.d
    qv = np.frombuffer(qpos, dtype=np.float64); hv = np.frombuffer(hf, dtype=np.float32)
    T = tp.terrain; DT = TP.DT; k = int(1 / 200 / DT)
    nxt = time.time(); last_hf = 0.0; last_st = 0.0
    while True:
        while not cmd.empty():
            c = cmd.get()
            if c[0] == "quit": return
            if c[0] == "key": tp.key(c[1], hold=c[2])
            elif c[0] == "rel": tp.release(c[1])
        for _ in range(k): tp.step()
        seq.value += 1; qv[:] = d.qpos; seq.value += 1               # нечётное — идёт запись
        t = time.time()
        if T is not None and T.ok and T.dirty and t - last_hf > 0.15:
            hv[:] = m.hfield_data[T.adr:T.adr + hv.size]; hver.value += 1; T.dirty = False; last_hf = t
        if t - last_st > 0.2:
            b = tp.status().encode("utf-8")[:2000]; status[:len(b) + 1] = b + b"\0"; last_st = t
        flags[0] = int(tp.show_phys); flags[1] = int(tp.world)
        nxt += k * DT; sl = nxt - time.time()
        if sl > 0: time.sleep(sl)
        elif sl < -0.25: nxt = time.time()                            # не успеваем — не копить отставание


class RemoteTeleop:
    """Заменяет Teleop в панели: команды уходят в процесс физики, состояние приходит из общей памяти.
    sim — копия модели только для рендера (её положение обновляет pull())."""
    def __init__(self):
        import harvey_teleop as TP
        self.TP = TP
        self.view = TP.Teleop(); self.sim = self.view.sim; self.MOVE, self.CLAW = TP.Teleop.MOVE, TP.Teleop.CLAW
        self.terrain = self.view.terrain
        m = self.sim.m; ctx = mp.get_context("spawn")
        T = self.terrain; self.nh = (T.H.size if (T is not None and T.ok) else 1)
        self.qpos = ctx.RawArray("d", m.nq); self.seq = ctx.RawValue("l", 0)
        self.hf = ctx.RawArray("f", self.nh); self.hver = ctx.RawValue("l", 0); self.hseen = 0
        self.st = ctx.RawArray("c", 2048); self.flags = ctx.RawArray("i", 4)
        self.cmd = ctx.Queue()
        self.p = ctx.Process(target=_child, args=(self.qpos, self.seq, self.hf, self.hver, self.st, self.flags, self.cmd), daemon=True)
        self.p.start()
        self.qv = np.frombuffer(self.qpos, dtype=np.float64); self.hv = np.frombuffer(self.hf, dtype=np.float32)
        self.world = self.view.world

    @property
    def show_phys(self):
        return bool(self.flags[0])

    def key(self, c, hold=False):
        self.cmd.put(("key", c, hold))

    def release(self, c):
        self.cmd.put(("rel", c))

    def status(self):
        raw = bytes(self.st[:]); return raw.split(b"\0")[0].decode("utf-8", "ignore") or "запуск физики…"

    def pull(self):
        """Забрать положение тел (и рельеф песка, если менялся). Возвращает True, если рельеф обновился."""
        m, d = self.sim.m, self.sim.d
        for _ in range(5):
            s0 = self.seq.value
            if s0 % 2: time.sleep(0.0002); continue
            q = self.qv.copy()
            if self.seq.value == s0: d.qpos[:] = q; break
        mujoco.mj_kinematics(m, d)
        if self.hver.value != self.hseen and self.terrain is not None and self.terrain.ok:
            self.hseen = self.hver.value; T = self.terrain
            m.hfield_data[T.adr:T.adr + self.nh] = self.hv
            return True
        return False

    def alive(self):
        return self.p.is_alive()

    def close(self):
        try: self.cmd.put(("quit",))
        except Exception: pass
        self.p.join(timeout=2)
        if self.p.is_alive(): self.p.terminate()


class PhotoView:
    """То же, что окно mujoco.viewer для run_gui: is_running, lock, opt, cam, sync, update_hfield, close.
    Рисует высокоуровневый рендерер MuJoCo Studio (Filament) без окна; кадр выводится в окно tkinter."""
    SAND_EVERY = 1.5          # с — как часто перезагружать рельеф песка в рендер (≈ 0,15 с на перезагрузку)

    def __init__(self, root, m, d, size=(1280, 720), title="Харви — фото (Filament, PBR)"):
        import tkinter as tk
        self.m, self.d = m, d
        self.d2 = mujoco.MjData(m)          # своя копия для рендера
        self.r = studio_renderer.Renderer("opengl_headless"); self.r.Init(m)
        self.opt = mujoco.MjvOption(); self.cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(m, self.cam)
        self.hid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_HFIELD, "h_sand")
        self.sand_dirty = False; self.sand_t = time.time()
        self._lock = threading.Lock(); self.running = True
        self.top = tk.Toplevel(root); self.top.title(title); self.top.configure(bg="black")
        self.top.geometry(f"{size[0]}x{size[1]}+400+30")          # справа от панели управления
        self.label = tk.Label(self.top, bg="black", bd=0, highlightthickness=0); self.label.pack(fill="both", expand=True)
        self.size = size; self.img = None; self.prev = None
        self.label.bind("<Configure>", lambda e: setattr(self, "size", (max(64, e.width), max(64, e.height))))
        self.label.bind("<ButtonPress-1>", self._down); self.label.bind("<ButtonPress-3>", self._down)
        self.label.bind("<B1-Motion>", lambda e: self._drag(e, 1)); self.label.bind("<B3-Motion>", lambda e: self._drag(e, 3))
        self.label.bind("<MouseWheel>", lambda e: self._zoom(-e.delta / 120 * 40))
        self.label.bind("<Button-4>", lambda e: self._zoom(-40)); self.label.bind("<Button-5>", lambda e: self._zoom(40))
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.fps = 0.0; self._t = time.time()

    def _down(self, e):
        self.prev = (e.x, e.y)

    def _drag(self, e, b):
        if self.prev is None: self.prev = (e.x, e.y); return
        dx, dy = e.x - self.prev[0], e.y - self.prev[1]; self.prev = (e.x, e.y)
        if b == 1:
            self.cam.azimuth -= dx * 0.3; self.cam.elevation = float(np.clip(self.cam.elevation - dy * 0.3, -89, 10))
        else:
            self._zoom(dy)

    def _zoom(self, dy):
        self.cam.distance = float(np.clip(self.cam.distance * np.exp(dy * 0.004), 0.15, 6.0))

    def bind_keys(self, on_press, on_release):
        self.top.bind("<KeyPress>", on_press); self.top.bind("<KeyRelease>", on_release)

    def is_running(self):
        return self.running

    def lock(self):
        return self._lock

    def update_hfield(self, hid):
        if hid == self.hid: self.sand_dirty = True

    def sync(self):
        if not self.running: return
        from PIL import Image, ImageTk
        w, h = self.size
        if self.sand_dirty and time.time() - self.sand_t > self.SAND_EVERY:     # следы на песке
            self.r.Init(self.m); self.sand_dirty = False; self.sand_t = time.time()
        with self._lock:
            self.d2.qpos[:] = self.d.qpos; self.d2.time = self.d.time
        mujoco.mj_kinematics(self.m, self.d2); mujoco.mj_camlight(self.m, self.d2)
        px = self.r.Render(self.m, self.d2, None, self.cam, self.opt, w, h)
        self.img = ImageTk.PhotoImage(Image.frombuffer("RGB", (w, h), px, "raw", "RGB", 0, 1))
        self.label.configure(image=self.img)
        t = time.time(); self.fps += (1.0 / max(1e-3, t - self._t) - self.fps) * 0.1; self._t = t

    def save(self, path):
        """Сохранить текущий кадр (для README и галереи)."""
        from PIL import ImageTk
        if self.img is not None: ImageTk.getimage(self.img).convert("RGB").save(path)

    def close(self):
        self.running = False
        try: self.top.destroy()
        except Exception: pass
