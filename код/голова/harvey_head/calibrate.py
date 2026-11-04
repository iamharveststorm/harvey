"""Калибровка нулей приводов «Компакт мини» — один раз после сборки (и после переборки ноги или клешни).

    python -m harvey_head.calibrate            # на Pi Zero, RP2350 подключён по USB

1. Приводы отпускаются. Харви ставится на калибровочную подставку (модели/мини: calib_jig) — поза A: ноги — поворот 0,
   бедро горизонтально, голень отвесно (стопа в гнезде); клешни — плечо прямо и горизонтально, предплечье отвесно вниз,
   губки сомкнуты до упора и стоят кончиком на столбике; стебельки глаз вертикально. Позиции всех приводов запоминаются.
2. По очереди для каждой ноги, клешни и глаз: сдвинуть суставы рукой на 15–30° в указанную сторону — поза B.
   Направление привода = знак сдвига; ноль = позиция в позе A минус угол позы A.
3. Проверяется, что рабочий ход каждого сустава не переходит через край 0/4095 (иначе переставить качалку на шлиц),
   и итог сохраняется в servo_calib.json. Проверка: приводы держат позу A — ничего не должно дёрнуться.
Углы позы A — mini_geometry.json (CAD, export_head).
"""
from __future__ import annotations

import json
import math
import time

from . import gait, servos

DIRECTION = {"c": 1, "f": 1, "k": 1, "y": 1, "p": 1, "e": 1, "g": -1, "s": -1}   # куда просим сдвинуть сустав (знак угла)
MIN_MOVE = round(math.radians(5) * servos.K)          # сдвиг меньше 5° — сустав не сдвинули
LEG_TEXT = "поверните ногу против часовой стрелки (если смотреть сверху), поднимите бедро, разогните колено"
CLAW_TEXT = "поверните плечо наружу, поднимите клешню, поднимите предплечье, раскройте губки"
GROUPS = [(f"Нога {n}", [f"{n}_{j}" for j in "cfk"], LEG_TEXT) for n in ("LF", "LM", "LB", "RF", "RM", "RB")]
GROUPS += [(f"Клешня {s}", [f"{s}_{j}" for j in "ypeg"], CLAW_TEXT) for s in "LR"]
GROUPS += [("Глаза", ["L_s", "R_s"], "наклоните оба глаза наружу")]


def load_pose(path=gait.GEOMETRY) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)["calib_deg"]


def pose_a(calib_deg: dict) -> dict:
    """Углы всех суставов (°) в позе A на подставке."""
    out = {}
    for _, joints, _ in GROUPS:
        for j in joints:
            if j.endswith("_s"):
                out[j] = calib_deg["eye"]
            elif j[-1] in "cfk":
                out[j] = calib_deg["leg"]["cfk".index(j[-1])]
            else:
                out[j] = calib_deg["claw"]["ypeg".index(j[-1])]
    return out


def wrap(d: int) -> int:
    """Разница позиций на окружности 0…4095 → −2048…2047."""
    return (d + 2048) % servos.STEPS - 2048


def read_positions(link, ids, wait, timeout=1.0) -> dict | None:
    """Где сейчас приводы: {id: позиция}; None — RP2350 не ответил."""
    link.send({"t": "pos?", "ids": list(ids)})
    for _ in range(round(timeout / 0.05)):
        wait(0.05)
        for msg in link.poll(time.monotonic()):
            if msg.get("t") == "pos":
                return {int(k): v for k, v in msg["q"].items()}
    return None


def compute(pos_a: dict, pos_b: dict, angles_a: dict) -> tuple:
    """(калибровка, замечания) по позициям в позах A и B: {сустав: позиция}."""
    zero, sign, notes = {}, {}, []
    for joint, a in angles_a.items():
        if joint not in pos_a or joint not in pos_b:
            notes.append(f"{joint}: привод не ответил")
            continue
        d = wrap(pos_b[joint] - pos_a[joint])
        if abs(d) < MIN_MOVE:
            notes.append(f"{joint}: сустав не сдвинулся (сдвиг {d} при нужных ≥ {MIN_MOVE}) — повторите калибровку")
            continue
        sign[joint] = DIRECTION[joint[-1]] * (1 if d > 0 else -1)
        zero[joint] = (pos_a[joint] - sign[joint] * round(math.radians(a) * servos.K)) % servos.STEPS
    return servos.Calibration(zero, sign), notes


def run(link, ask=input, say=print, wait=time.sleep, path=servos.CALIB_FILE):
    """Провести калибровку; вернуть её (и сохранить) или None, если RP2350 молчит."""
    angles = pose_a(load_pose())
    ids = {servos.SERVO_IDS[j]: j for j in angles}
    link.send({"t": "relax"})
    say("Приводы отпущены. Поставьте Харви на калибровочную подставку: стопы в гнёзда, корпус на опору; клешни —"
        " плечо прямо, предплечье отвесно вниз, губки сомкнуты до упора и стоят кончиком на столбиках; глаза вертикально.")
    ask("Готово? Enter ")
    raw = read_positions(link, ids, wait)
    if raw is None:
        say("RP2350 не отвечает — проверьте USB и что на плате запущен main.py.")
        return None
    pos_a = {ids[i]: p for i, p in raw.items()}
    pos_b = {}
    for title, joints, text in GROUPS:
        say(f"{title}: {text} — на 15–30°, и держите.")
        ask("Держите и нажмите Enter ")
        now = read_positions(link, [servos.SERVO_IDS[j] for j in joints], wait) or {}
        pos_b.update({ids[i]: p for i, p in now.items()})
    c, notes = compute(pos_a, pos_b, angles)
    for n in notes:
        say(n)
    for joint in c.out_of_range():
        say(f"{joint}: рабочий ход переходит через край 0/4095 — переставьте качалку на шлиц (на 1–2 зуба) и повторите")
    c.save(path)
    say(f"Сохранено: {path} — {len(c.zero)} из {len(angles)} приводов.")
    hold = {j: math.radians(a) for j, a in angles.items() if j in c.zero}
    link.send(servos.message(hold, (0, 0, 0), c))
    say("Приводы держат позу A: если что-то дёрнулось или поехало — этот сустав откалиброван неверно.")
    wait(1.0)
    link.send({"t": "relax"})
    return c


def main() -> None:
    import serial

    from . import config
    from .links import SpineLink
    link = SpineLink(lambda: serial.Serial(config.SPINE_PORT, config.SPINE_BAUD, timeout=0))
    run(link)


if __name__ == "__main__":
    main()
