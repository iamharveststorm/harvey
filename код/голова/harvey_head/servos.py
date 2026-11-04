"""Приводы Харви «Компакт мини»: номер на шине по суставу и позиция STS по углу.

ID = 10 × конечность + сустав (схемы/README.md «Номера приводов»): ноги LF 1, LM 2, LB 3, RF 4, RM 5, RB 6 (поворот,
бедро, колено = 1–3), клешни L 7, R 8 (поворот плеча, подъём, локоть, захват = 1–4), глаза 91, 92.
Позиция STS: 4096 на оборот, 2048 — ноль сустава (предварительно: нули задаются при сборке, на стенде проверить).
"""
from __future__ import annotations

import math

from .protocol import joints

LEG_LIMB = {"LF": 1, "LM": 2, "LB": 3, "RF": 4, "RM": 5, "RB": 6}
SERVO_IDS = {f"{n}_{j}": 10 * k + i for n, k in LEG_LIMB.items() for i, j in enumerate("cfk", 1)}
SERVO_IDS.update({f"{s}_{j}": 10 * k + i for s, k in (("L", 7), ("R", 8)) for i, j in enumerate("ypeg", 1)})
SERVO_IDS.update({"L_s": 91, "R_s": 92})
JOINT_OF = {v: k for k, v in SERVO_IDS.items()}
STEPS = 4096


def to_pos(rad: float) -> int:
    return round(2048 + rad * STEPS / (2 * math.pi))


def to_rad(pos: int) -> float:
    return (pos - 2048) * 2 * math.pi / STEPS


def message(angles: dict, velocity: tuple) -> dict:
    """Сообщение `j` для RP2350: позиции всех приводов и скорость корпуса (по ней RP2350 решает про край стола)."""
    return joints({SERVO_IDS[k]: to_pos(a) for k, a in angles.items()}, tuple(round(v, 1) for v in velocity))
