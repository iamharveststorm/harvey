"""Поведение Харви «Компакт мини» в симуляции: голова (harvey_head/behavior.py) управляет роботом только по его датчикам.

    (окружение C:/venvs/harvey) python mini_behave.py        # все сценарии, итог в behave_results.json
Робот — mini_robot.SimRobot: настоящий Spine прошивки RP2350 с имитациями датчиков. Голова — настоящая (Head + Body:
поведение и походка, 50 раз в секунду, как на Pi). Видит она то же, что на роботе: телеметрию и события RP2350 и
«зрение» (рука в кадре и метка станции — заглушка разбора кадра).
"""
import json
import math

import numpy as np
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _head_dir():
    for base in (Path(__file__).absolute(), Path(__file__).resolve()):
        p = base.parents[2] / "голова"
        if (p / "harvey_head" / "behavior.py").exists():
            return p
    raise FileNotFoundError("не найдена код/голова")


sys.path.insert(0, str(_head_dir()))
import mini_robot as mr  # noqa: E402
from harvey_head.behavior import Behavior  # noqa: E402
from harvey_head.body import Body  # noqa: E402
from harvey_head.gait import Gait  # noqa: E402
from harvey_head.head import Head  # noqa: E402

HEAD_EVERY = round(0.02 / mr.TICK)                  # голова — 50 раз в секунду

HERE = os.path.dirname(os.path.abspath(__file__))
DOCK = (0.15, 0.0)                                   # центр площадки; башенка за ней по +x
HOME_TABLE = (-0.45, 0.65, -0.35, 0.35)
END = {"look": ("idle", "at_hand"), "hand": ("at_hand",), "home": ("docked", "home_lost", "home_failed")}


def run(robot, goal, limit_s, during=None):
    """Голова ведёт робота к цели, пока не дойдёт до конечного состояния или не выйдет время.
    during(robot) — что делает мир на каждом шаге (двигает руку, поднимает робота)."""
    port = robot.link()
    body = Body(port, Behavior(robot.t), Gait(), vision=lambda now: robot.vision(), now=robot.t)
    head = Head(port, body=body, now=robot.t)
    body.request(goal, robot.t)
    b = body.behavior
    log = {"states": [], "fell": False, "max_tilt": 0.0, "yaw": 0.0}
    prev = robot.pose()[2]
    t_end = robot.t + limit_s
    while robot.t < t_end:
        if during:
            during(robot)
        robot.physics()
        if round(robot.t / mr.TICK) % HEAD_EVERY == 0:
            head.tick(robot.t)
            if not log["states"] or log["states"][-1] != b.state:
                log["states"].append(b.state)
        y = robot.pose()[2]
        log["yaw"] += (y - prev + 180) % 360 - 180
        prev = y
        log["fell"] |= not robot.on_table()
        log["max_tilt"] = max(log["max_tilt"], robot.sim.tilt())
        if b.state in END[goal]:
            break
    log.update(t=round(robot.t, 1), state=b.state, yaw=round(log["yaw"]), max_tilt=round(log["max_tilt"], 1))
    return log


# ---------- сценарии ----------
def miss_mm(robot):
    x, y, _ = robot.pose()
    return [round((x - DOCK[0]) * 1000), round((y - DOCK[1]) * 1000)]


class NoCamera:
    """Темно: камера не видит метку — только датчики RP2350 (ИК-маяк с двумя светодиодами)."""

    def __init__(self, robot):
        self.robot = robot

    def __getattr__(self, name):
        return getattr(self.robot, name)

    def vision(self):
        return {}


def scenario_home(start, camera=True, limit_s=120.0):
    r = mr.SimRobot(table=HOME_TABLE, dock_pos=DOCK, start=start)
    log = run(r if camera else NoCamera(r), "home", limit_s)
    log.update(start=list(start), camera=camera, charging=r.charging(), miss_mm=miss_mm(r))
    return log


# старты перед станцией: расстояние до контактов, направление от оси станции, курс Харви (°)
HOME_STARTS = [(0.25, 0, 0), (0.30, 15, 40), (0.20, -20, -30), (0.35, 30, 90), (0.25, -40, 150), (0.30, 45, -120),
               (0.18, 10, 180), (0.33, -25, 60), (0.22, 35, -60), (0.28, -50, 0)]


def start_at(dist, deg, yaw):
    a = math.radians(deg)
    return (DOCK[0] - dist * math.cos(a), DOCK[1] + dist * math.sin(a), yaw)


def scenario_behind_station():
    r = mr.SimRobot(table=HOME_TABLE, dock_pos=DOCK, start=(DOCK[0] + 0.25, 0.0, 180.0))
    log = run(r, "home", 30.0)
    log.update(on_table=r.on_table())
    return log


def scenario_look():
    r = mr.SimRobot()
    x0, y0, _ = r.pose()
    log = run(r, "look", 40.0)
    x, y, _ = r.pose()
    log.update(drift_mm=round(math.hypot(x - x0, y - y0) * 1000))
    return log


def hand_dist_mm(robot):
    v = mr.ms.see_hand(robot.sim)
    return v and v["dist_mm"]


def scenario_hand(hand, goal="hand", limit_s=40.0, start=(0.0, 0.0, 0.0)):
    r = mr.SimRobot(start=start, hand=hand)
    log = run(r, goal if goal != "look" else "look", limit_s)
    if goal == "look" and log["state"] == "idle":
        log["found"] = False
    log.update(hand_mm=hand_dist_mm(r), on_table=r.on_table())
    return log


def scenario_hand_beyond_edge(side):
    """Рука за краем стола: Харви идёт к ней, рефлекс останавливает, поведение уводит назад — и так по кругу."""
    edge = mr.TABLE[1]
    start = {"front": (edge - 0.16, 0.0, 0.0), "left": (0.0, edge - 0.16, 90.0),
             "back": (-edge + 0.16, 0.0, 180.0), "right": (0.0, -edge + 0.16, -90.0)}[side]
    yaw = math.radians(start[2])
    hand = (start[0] + 0.30 * math.cos(yaw), start[1] + 0.30 * math.sin(yaw))
    r = mr.SimRobot(start=start, hand=hand)
    log = run(r, "hand", 25.0)
    log.update(side=side, on_table=r.on_table(), edge_seen="edge" in log["states"])
    return log


LIFT_MM, LIFT_SPEED, HOLD_S = 50.0, 0.15, 1.0          # поднять рукой на 5 см со скоростью 15 см/с, подержать, поставить


def scenario_lift():
    """Подняли во время осмотра и поставили: приводы отпущены быстро, потом Харви снова осматривается."""
    r = mr.SimRobot()
    t_lift, seen = 1.0, {}
    m, d = r.sim.m, r.sim.d
    tid = m.body("torso").id
    va = m.jnt_dofadr[m.body("torso").jntadr[0]]
    mass = float(sum(m.body_mass))
    z0 = float(d.body("torso").xpos[2])
    up_s = LIFT_MM / 1000 / LIFT_SPEED

    def hand(robot):
        t = robot.t - t_lift
        if t < 0 or t > 2 * up_s + HOLD_S:
            d.xfrc_applied[tid] = 0
            return
        h = LIFT_MM / 1000 * min(1.0, t / up_s, max(0.0, (2 * up_s + HOLD_S - t) / up_s))
        z, vz = float(d.body("torso").xpos[2]), float(d.qvel[va + 2])
        d.xfrc_applied[tid, 2] = mass * 9.81 + mass * (400 * (z0 + h - z) - 40 * vz)   # ладонь держит корпус
        up = d.body("torso").xmat.reshape(3, 3)[:, 2]
        d.xfrc_applied[tid, 3:] = 2.0 * np.cross(up, (0, 0, 1)) - 0.1 * d.qvel[va + 3:va + 6]   # и держит ровно
        if robot.tel.get("relaxed") and "relaxed" not in seen:
            seen["relaxed"] = t
    log = run(r, "look", 12.0, during=hand)
    log.update(relaxed_after_s=round(seen.get("relaxed", 99.0), 3), on_table=r.on_table())
    return log


def all_scenarios():
    res = {"домой_при_свете": [scenario_home(start_at(*s)) for s in HOME_STARTS],
           "домой_в_темноте": [scenario_home(start_at(*s), camera=False) for s in HOME_STARTS],
           "станция_сзади": scenario_behind_station(),
           "осмотреться": scenario_look(),
           "рука_впереди": scenario_hand((0.0662 + 0.30 * math.cos(math.radians(30)), 0.30 * math.sin(math.radians(30)))),
           "рука_сзади": scenario_hand((-0.25, 0.05), goal="look"),
           "рука_за_краем": [scenario_hand_beyond_edge(s) for s in ("front", "left", "back", "right")],
           "подняли": scenario_lift()}
    return res


if __name__ == "__main__":
    res = all_scenarios()
    json.dump(res, open(os.path.join(HERE, "behave_results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for k, v in res.items():
        print(k, v)
