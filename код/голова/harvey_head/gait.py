"""Походка Харви «Компакт мини» на голове: команда корпусу → углы всех 28 суставов. Трипод, как в симуляции.

Команда — та же, что даёт поведение (behavior.py): {"v": (вперёд мм/с, влево мм/с, поворот °/с), "pose": "stand" | "lie"}.
Размеры ног — из CAD (mini_geometry.json, выгружает модели/мини/harvey_mini_parts.py export_head); симуляция берёт эту же
походку (код/симуляция/мини/harvey_mini.py), поэтому её проверки — проверки этого кода.
Скорость меняется плавно (разгон 0,8 м/с² и 0,8 рад/с²), шаг — две тройки ног по очереди, подъём стопы 15 мм.
Нули и направления приводов — как суставы в симуляции (предварительно: задаются при сборке).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

TRIPOD_A = ("RF", "LM", "RB")
GEOMETRY = Path(__file__).absolute().parent / "mini_geometry.json"


@dataclass(frozen=True)
class Geometry:
    cox: float
    fem: float
    tib: float
    foot_r: float
    mounts: dict                      # нога → (x, y мм, поворот гнезда °) в системе корпуса
    stance_deg: float                 # бедро в стойке
    tuck_deg: tuple                   # клешни «поджато»: поворот плеча, подъём, локоть
    rest_drop: float                  # лечь на станцию: корпус ниже на столько мм

    @property
    def stance_h(self) -> float:
        """Стопа ниже оси бедра в стойке, мм (отрицательное)."""
        return -(self.tib - self.fem * math.sin(math.radians(self.stance_deg)) - self.foot_r)

    @property
    def reach(self) -> float:
        return self.cox + self.fem * math.cos(math.radians(self.stance_deg))


def load(path: Path = GEOMETRY) -> Geometry:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return Geometry(d["cox"], d["fem"], d["tib"], d["foot_r"], {k: tuple(v) for k, v in d["mounts"].items()},
                    d["stance_deg"], tuple(d["tuck_deg"]), d["rest_drop"])


def neutral(geo: Geometry, n: str) -> tuple:
    x, y, yaw = geo.mounts[n]
    a = math.radians(yaw)
    return x + geo.reach * math.cos(a), y + geo.reach * math.sin(a)


def leg_ik(geo: Geometry, n: str, p: tuple, h: float) -> tuple:
    """Суставы (поворот, бедро, колено), рад, чтобы стопа встала в p (x, y мм) на h мм от плоскости осей бедра."""
    x, y, yaw = geo.mounts[n]
    a = math.radians(yaw)
    dx, dy = p[0] - x, p[1] - y
    lx, ly = math.cos(a) * dx + math.sin(a) * dy, -math.sin(a) * dx + math.cos(a) * dy
    qc = math.atan2(ly, lx)
    rr, l2 = math.hypot(lx, ly) - geo.cox, geo.tib - geo.foot_r
    d = min(max(math.hypot(rr, h), abs(l2 - geo.fem) + 1e-4), geo.fem + l2 - 1e-4)
    qf = math.atan2(h, rr) + math.acos(max(-1.0, min(1.0, (geo.fem ** 2 + d ** 2 - l2 ** 2) / (2 * geo.fem * d))))
    qk = -(math.pi - math.acos(max(-1.0, min(1.0, (geo.fem ** 2 + l2 ** 2 - d ** 2) / (2 * geo.fem * l2)))))
    return qc, qf, qk


def foot_targets(geo: Geometry, phase: float, vel, t_half: float, lift: float, dz: float = 0.0, pitch: float = 0.0,
                 moving: bool = True) -> dict:
    """Где каждая стопа (x, y, h мм) в фазе шага phase ∈ [0, 1) при скорости vel (мм/с, мм/с, рад/с).
    Опорная тройка тянется назад на vel·t_half, переносимая — вперёд по дуге с подъёмом lift. pitch (рад, + — нос вниз)
    — наклон корпуса ногами: передние стопы ближе к корпусу, задние — дальше."""
    out = {}
    h0 = geo.stance_h + dz
    for n in geo.mounts:
        p0 = neutral(geo, n)
        u = z = 0.0
        if moving:
            pp = phase if n in TRIPOD_A else (phase + 0.5) % 1.0
            if pp < 0.5:
                u = 0.5 - 2 * pp
            else:
                s = (pp - 0.5) * 2
                u, z = -0.5 + (s - math.sin(2 * math.pi * s) / (2 * math.pi)), lift * math.sin(math.pi * s)
        a = vel[2] * t_half * u
        c, sn = math.cos(a), math.sin(a)
        x, y = c * p0[0] - sn * p0[1] + vel[0] * t_half * u, sn * p0[0] + c * p0[1] + vel[1] * t_half * u
        out[n] = (x, y, h0 + z + math.tan(pitch) * x)
    return out


class Gait:
    def __init__(self, geo: Geometry | None = None, t_half: float = 0.30, lift: float = 15.0, accel: float = 800.0,
                 turn_accel: float = 0.8, lie_rate: float = 20.0):
        self.geo = geo or load()
        self.t_half, self.lift, self.accel, self.turn_accel, self.lie_rate = t_half, lift, accel, turn_accel, lie_rate
        self.vel = [0.0, 0.0, 0.0]                  # мм/с, мм/с, рад/с
        self.phase, self.dz = 0.0, 0.0

    def accelerate(self, target, dt: float) -> None:
        """target — (мм/с, мм/с, рад/с)."""
        for i, lim in enumerate((self.accel, self.accel, self.turn_accel)):
            self.vel[i] += max(-lim * dt, min(lim * dt, target[i] - self.vel[i]))

    def moving(self) -> bool:
        return math.hypot(self.vel[0] / 1000, self.vel[1] / 1000, self.vel[2]) > 1e-3

    def legs(self, dt: float, dz: float = 0.0, pitch: float = 0.0) -> dict:
        """Углы 18 суставов ног после шага фазы на dt."""
        moving = self.moving()
        if moving:
            self.phase = (self.phase + dt / (2 * self.t_half)) % 1.0
        feet = foot_targets(self.geo, self.phase, self.vel, self.t_half, self.lift, dz, pitch, moving)
        out = {}
        for n, (x, y, h) in feet.items():
            for j, v in zip("cfk", leg_ik(self.geo, n, (x, y), h)):
                out[f"{n}_{j}"] = v
        return out

    def step(self, cmd: dict, dt: float) -> dict:
        """Команда поведения → углы всех 28 суставов, рад."""
        vx, vy, wz = cmd.get("v", (0, 0, 0))
        self.accelerate((vx, vy, math.radians(wz)), dt)
        target = self.geo.rest_drop if cmd.get("pose") == "lie" else 0.0
        self.dz += max(-self.lie_rate * dt, min(self.lie_rate * dt, target - self.dz))
        out = self.legs(dt, self.dz, math.radians(cmd.get("pitch", 0.0)))
        for s in "LR":
            for j, a in zip("ype", self.geo.tuck_deg):
                out[f"{s}_{j}"] = math.radians(a)
            out[f"{s}_g"] = 0.0
            out[f"{s}_s"] = 0.0
        return out

    def velocity(self) -> tuple:
        """Скорость корпуса, как её шлют в RP2350 (мм/с, мм/с, °/с)."""
        return self.vel[0], self.vel[1], math.degrees(self.vel[2])
