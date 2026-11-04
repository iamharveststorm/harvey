"""Приводы Харви «Компакт мини»: номер на шине по суставу и позиция STS по углу.

ID = 10 × конечность + сустав (схемы/README.md «Номера приводов»): ноги LF 1, LM 2, LB 3, RF 4, RM 5, RB 6 (поворот,
бедро, колено = 1–3), клешни L 7, R 8 (поворот плеча, подъём, локоть, захват = 1–4), глаза 91, 92.
Позиция STS: 4096 на оборот. Ноль и направление каждого привода зависят от того, как его поставили при сборке, —
их находит калибровка (calibrate.py) и хранит servo_calib.json; без него — 2048 и «как в симуляции».
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .protocol import joints

LEG_LIMB = {"LF": 1, "LM": 2, "LB": 3, "RF": 4, "RM": 5, "RB": 6}
SERVO_IDS = {f"{n}_{j}": 10 * k + i for n, k in LEG_LIMB.items() for i, j in enumerate("cfk", 1)}
SERVO_IDS.update({f"{s}_{j}": 10 * k + i for s, k in (("L", 7), ("R", 8)) for i, j in enumerate("ypeg", 1)})
SERVO_IDS.update({"L_s": 91, "R_s": 92})
JOINT_OF = {v: k for k, v in SERVO_IDS.items()}
STEPS = 4096
K = STEPS / (2 * math.pi)
CALIB_FILE = Path(__file__).absolute().parent / "servo_calib.json"
# рабочий ход суставов, ° — как в симуляции (код/симуляция/мини/harvey_mini.py, build_xml) и правилах движения CAD
JOINT_RANGES_DEG = {"c": (-30, 30), "f": (-45, 85), "k": (-130, -60), "y": (-10, 70), "p": (-20, 90), "e": (-140, 60),
                    "g": (-50, 12), "s": (-90, 20)}


def to_pos(rad: float) -> int:
    return round(2048 + rad * STEPS / (2 * math.pi))


def to_rad(pos: int) -> float:
    return (pos - 2048) * 2 * math.pi / STEPS


class Calibration:
    """Ноль (позиция при угле 0) и направление (+1 / −1) каждого привода по суставу; кого нет — 2048 и +1."""

    def __init__(self, zero: dict | None = None, sign: dict | None = None):
        self.zero, self.sign = dict(zero or {}), dict(sign or {})

    def pos(self, joint: str, rad: float) -> int:
        return round(self.zero.get(joint, 2048) + self.sign.get(joint, 1) * rad * K)

    def rad(self, joint: str, pos: int) -> float:
        return self.sign.get(joint, 1) * (pos - self.zero.get(joint, 2048)) / K

    def out_of_range(self) -> list[str]:
        """Суставы, чей рабочий ход выходит за 0…4095: привод там не встанет — переставить качалку на шлиц."""
        bad = []
        for joint in self.zero:
            lo, hi = JOINT_RANGES_DEG[joint[-1]]
            ends = [self.pos(joint, math.radians(a)) for a in (lo, hi)]
            if min(ends) < 0 or max(ends) > STEPS - 1:
                bad.append(joint)
        return bad

    def save(self, path: Path = CALIB_FILE) -> None:
        Path(path).write_text(json.dumps({"zero": self.zero, "sign": self.sign}, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: Path = CALIB_FILE) -> "Calibration":
        """Калибровка из файла; нет файла — как в симуляции (нули 2048)."""
        p = Path(path)
        if not p.exists():
            return cls()
        d = json.loads(p.read_text(encoding="utf-8"))
        return cls(d.get("zero"), d.get("sign"))


def message(angles: dict, velocity: tuple, cal: Calibration | None = None) -> dict:
    """Сообщение `j` для RP2350: позиции всех приводов и скорость корпуса (по ней RP2350 решает про край стола)."""
    cal = cal or Calibration()
    return joints({SERVO_IDS[k]: cal.pos(k, a) for k, a in angles.items()}, tuple(round(v, 1) for v in velocity))
