"""Адаптивная походка Харви для неровных поверхностей (тот же алгоритм пойдёт в прошивку Pico 2).

Три механизма поверх обычной трипод-походки:
1. Выравнивание корпуса по IMU: каждая нога получает поправку высоты стопы c_i ~ ∫(наклон · положение стопы):
   на склоне ноги снизу вытягиваются, сверху поджимаются, корпус остаётся горизонтальным.
2. Поиск опоры: g_i — где под этой ногой земля. Опорная нога без контакта опускается, пока не нащупает
   опору (до −45 мм); нога в переносе, коснувшаяся раньше времени (ступенька, камень), останавливается там.
   На настоящем роботе касание определяется по нагрузке привода колена (регистр Present Load STS3215),
   в симуляции — по силе контакта стопы.
3. Шаг выше (35 мм вместо 25) и медленнее на крутом уклоне.
Средние значения c и g всё время подтягиваются к нулю — высота корпуса над средней опорой сохраняется."""
import math
import numpy as np
import mujoco
import harvey_sim as H

LIFT_FLAT, LIFT_ROUGH = 0.025, 0.035
C_MAX, G_MIN, G_MAX = 0.035, -0.045, 0.040
K_LEVEL = 2.5          # 1/с — скорость выравнивания корпуса
SEARCH = 0.08          # м/с — скорость поиска опоры
TOUCH_N = 1.2          # Н — касание
MEAN_PULL = 1.5        # 1/с — возврат средних к нулю


class AdaptiveGait:
    def __init__(self, sim):
        self.sim = sim; m = sim.m
        self.foot = {n: m.geom(f"{n}_foot").id for n in H.MOUNTS}
        self.c = {n: 0.0 for n in H.MOUNTS}; self.g = {n: 0.0 for n in H.MOUNTS}
        self.lock = {n: None for n in H.MOUNTS}
        self.on = True
        self.rough = 0.0       # 0…1 — насколько неровно (по разбросу g), поднимает шаг
        self._f = {}; self._f6 = np.zeros(6)

    def force(self, n):
        return self._f.get(n, 0.0)

    def _forces(self):
        """Сила контакта каждой стопы (один проход по списку контактов — быстро)."""
        d, m = self.sim.d, self.sim.m; self._f = {}
        if d.ncon == 0: return
        g = d.contact.geom[:d.ncon]
        for n, gid in self.foot.items():
            f = 0.0
            for i in np.nonzero((g[:, 0] == gid) | (g[:, 1] == gid))[0]:
                mujoco.mj_contactForce(m, d, int(i), self._f6); f += abs(self._f6[0])
            self._f[n] = f

    def foot_h(self, n):
        tb = self.sim.d.body("torso"); R = tb.xmat.reshape(3, 3)
        return float((R.T @ (self.sim.d.geom_xpos[self.foot[n]] - tb.xpos))[2])

    def tilt_slope(self):
        """Наклон по IMU: z мира в системе корпуса (R[2,0] — тангаж, R[2,1] — крен)."""
        R = self.sim.d.body("torso").xmat.reshape(3, 3)
        return R[2, 0], R[2, 1]

    def speed_scale(self):
        R = self.sim.d.body("torso").xmat.reshape(3, 3)
        tilt = math.degrees(math.acos(max(-1, min(1, R[2, 2]))))
        return 1.0 if tilt < 8 else max(0.5, 1.0 - (tilt - 8) / 30)

    def lift(self):
        return LIFT_FLAT + (LIFT_ROUGH - LIFT_FLAT) * self.rough

    def update(self, dt, phases, p_feet):
        """phases: {нога: None (опора) или s ∈ [0;1) (перенос)}; p_feet: {нога: (x, y) стопы в системе корпуса}.
        Возвращает {нога: поправка высоты стопы, м} (прибавить к номинальной высоте)."""
        out = {}
        if not self.on:
            return {n: 0.0 for n in H.MOUNTS}
        sx, sy = self.tilt_slope()
        self._forces()
        for n in H.MOUNTS:
            x, y = p_feet[n]
            self.c[n] = min(C_MAX, max(-C_MAX, self.c[n] + K_LEVEL * dt * (sx * x + sy * y) * 8.0))
        mc = np.mean(list(self.c.values()))
        for n in H.MOUNTS: self.c[n] -= mc * min(1.0, MEAN_PULL * dt * 4)
        for n in H.MOUNTS:
            s = phases[n]; f = self.force(n)
            if s is None:                                   # опора: нет контакта — искать ниже
                self.lock[n] = None
                if f < TOUCH_N * 0.5:
                    self.g[n] = max(G_MIN, self.g[n] - SEARCH * dt)
            else:                                           # перенос: во второй половине — остановиться на касании
                if s > 0.55 and f > TOUCH_N and self.lock[n] is None:
                    self.lock[n] = s
                    lift_now = self.lift() * math.sin(math.pi * s)
                    self.g[n] = min(G_MAX, max(G_MIN, self.g[n] + lift_now))
        mg = np.mean(list(self.g.values()))
        for n in H.MOUNTS: self.g[n] -= mg * MEAN_PULL * dt
        spread = np.ptp(list(self.g.values()))
        self.rough += dt * (min(1.0, spread / 0.015) - self.rough) * 2.0
        for n in H.MOUNTS:
            out[n] = self.c[n] + self.g[n]
        return out

    def swing_z(self, n, s):
        if self.lock.get(n) is not None:
            return 0.0                                      # уже стоит на опоре — подъём учтён в g
        return self.lift() * math.sin(math.pi * s)
