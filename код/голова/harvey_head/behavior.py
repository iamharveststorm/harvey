"""Поведение Харви: телеметрия и события «спинного мозга» + «зрение» → команда корпусу.

Команда — {"v": (вперёд мм/с, влево мм/с, поворот °/с, + — налево), "pose": "stand" | "lie", "state": …}; её превращает
в шаги модуль походки. Рефлексы края и «подняли» остаются в RP2350: поведение лишь решает, что делать дальше.

Цели (request): «look» — осмотреться, «hand» — подойти к руке, «home» — на станцию.
«Зрение» (камера, разбор — на ПК или голове) — словарь находок: "hand" — {"bearing_deg", "dist_mm"} руки в кадре,
"dock" — {"x_mm", "y_mm", "yaw_deg"}: где корпус в системе станции по метке AprilTag на башенке (x — к башенке, 0 — над
контактами). Домой: по метке выйти на ось станции, потом прямо, поправляясь по метке; без метки — по ИК-маяку
(только направление: попадает на контакты, лишь если Харви уже стоит почти на оси).
Курс — интеграл вращения гироскопа (tel["gyr"][2], °/с): повороты — на угол, а не по времени (корпус разгоняется
и тормозит с запаздыванием), при ходьбе курс держится сам.
Числа — оценки по симуляции (код/симуляция/мини/mini_behave.py), ПРЕДВАРИТЕЛЬНО: уточнить на роботе.
"""
from __future__ import annotations

import math

STILL = (0, 0, 0)
FRONT, BACK, LEFT, RIGHT = (0, 1), (2, 3), (4,), (5,)    # индексы датчиков края: FL, FR, BL, BR, L, R

TURN_GAIN, TURN_DONE = 3.0, 0.5                            # поворот на угол: скорость 3 °/с на градус остатка; готово — в 0,5°
LOOK_RATE, LOOK_STEP, LOOK_PAUSE, LOOK_STOPS = 40.0, 60.0, 1.0, 6
HAND_TURN, HAND_SPEED, HAND_GAIN, HAND_AIM, HAND_STOP_MM, HAND_LOST_S = 30.0, 40.0, 1.5, 8.0, 90, 0.5
EDGE_SPEED, EDGE_EXTRA_S, EDGE_TURN, EDGE_RATE = 30.0, 0.5, 120.0, 40.0
LIFTED_CLEAR_S = 1.0
SEARCH_RATE, SEARCH_TURN = 30.0, 370.0                    # полный оборот с запасом
CENTER_RATE = 20.0
APPROACH_SPEED, DROP_MM, BACK_MM = 40.0, 8, 4             # площадка и башенка ближе стола на ≥ 8 мм; «снова стол» — в 4 мм
HOLD_GAIN, HOLD_MAX = 2.0, 15.0                           # держать курс при ходьбе
ALIGN_X, ALIGN_TOL = -250.0, (8.0, 2.0, 1.5)              # точка на оси станции перед заходом; допуск x, y мм и курс °
ALIGN_GAIN, ALIGN_V, ALIGN_TURN, TAG_LOST_S = 1.5, (40.0, 30.0), 20.0, 1.0
SIDE_GAIN, SIDE_MAX = 3.0, 15.0                           # на заходе — поправка вбок по метке
REALIGN_MM, REALIGN_DEG = 10.0, 5.0                       # на заходе ушёл с оси дальше — снова выйти на ось
OVERSHOOT_S = 0.45                                        # башенку видно, когда корпус на ~17 мм дальше контактов
LIE_WAIT_S, RETRY_BACK_S = 3.0, 2.0
CHARGE_A = -0.05                                          # ток заряда (как spine.CHARGE_A)


class Behavior:
    def __init__(self, now: float = 0.0):
        self.goal, self.state = "idle", "idle"
        self.t0 = now
        self.data: dict = {}
        self.retries = 0
        self.heading, self.t_last = 0.0, now

    # ---------- управление ----------
    def request(self, goal: str, now: float) -> None:
        self.goal = goal
        self.retries = 0
        self._begin(goal, now)

    def _begin(self, goal: str, now: float) -> None:
        start = {"look": "look", "hand": "hand", "home": "home_search", "idle": "idle"}
        self._go(start[goal], now)

    def _go(self, state: str, now: float, **data) -> None:
        self.state, self.t0, self.data = state, now, dict(data, h0=self.heading)

    def turn_to(self, target: float, rate: float) -> tuple | None:
        """Поворот к курсу target; None — уже на нём."""
        err = target - self.heading
        if abs(err) < TURN_DONE:
            return None
        return (0, 0, max(-rate, min(rate, TURN_GAIN * err)))

    def update(self, tel: dict, events: list[str], vision: dict | None, now: float) -> dict:
        self.heading += (tel.get("gyr") or [0, 0, 0])[2] * (now - self.t_last)
        self.t_last = now
        self._interrupts(tel, events, now)
        v, pose = STATES[self.state](self, tel, events, vision or {}, now)
        return {"v": v, "pose": pose, "state": self.state}

    def _interrupts(self, tel: dict, events: list[str], now: float) -> None:
        if "lifted" in events and self.state != "lifted":
            self._go("lifted", now)
        elif "edge" in events and self.state not in ("lifted", "edge"):
            self._go("edge", now, clear=None)
        elif "bat_low" in events and not self.goal == "home":
            self.request("home", now)

    # ---------- состояния: каждое возвращает (v, pose) ----------
    def _idle(self, tel, events, vision, now):
        return STILL, "stand"

    def _look(self, tel, events, vision, now):
        if vision.get("hand") and self.goal in ("look", "hand"):
            self.goal = "hand"
            self._go("hand", now)
            return STILL, "stand"
        d = self.data
        k = d.setdefault("k", 0)
        if "pause" not in d:
            d["pause"] = now
        if now - d["pause"] < LOOK_PAUSE:
            return STILL, "stand"
        if k >= LOOK_STOPS:
            self.goal = "idle"
            self._go("idle", now)
            return STILL, "stand"
        turn = self.turn_to(d["h0"] + LOOK_STEP * (k + 1), LOOK_RATE)
        if turn is None:
            d.update(k=k + 1, pause=now)
            return STILL, "stand"
        return turn, "stand"

    def _hand(self, tel, events, vision, now):
        vision = vision.get("hand")
        if vision is None:
            seen = self.data.get("seen", self.t0)
            if now - seen > HAND_LOST_S:
                self._go("look", now)
            return STILL, "stand"
        self.data["seen"] = now
        b = vision["bearing_deg"]
        if vision["dist_mm"] <= HAND_STOP_MM:
            self._go("at_hand", now)
            return STILL, "stand"
        if abs(b) > HAND_AIM:
            return (0, 0, HAND_TURN if b > 0 else -HAND_TURN), "stand"
        return (HAND_SPEED, 0, HAND_GAIN * b), "stand"

    def _at_hand(self, tel, events, vision, now):
        hand = vision.get("hand")
        if hand is not None and hand["dist_mm"] > HAND_STOP_MM + 30:
            self._go("hand", now)
        return STILL, "stand"

    def _edge(self, tel, events, vision, now):
        far = tel.get("far") or [0] * 6
        if any(far):
            self.data["away"], self.data["clear"] = away_from(far), None
            return self.data["away"], "stand"
        clear = self.data.get("clear") or now
        self.data["clear"] = clear
        if now - clear < EDGE_EXTRA_S:
            self.data["h_turn"] = self.heading + EDGE_TURN
            return self.data.get("away", STILL), "stand"
        turn = self.turn_to(self.data["h_turn"], EDGE_RATE)
        if turn is not None:
            return turn, "stand"
        self._begin("look" if self.goal == "hand" else self.goal, now)
        return STILL, "stand"

    def _lifted(self, tel, events, vision, now):
        far = tel.get("far") or [1] * 6
        if any(far):
            self.data["down"] = None
            return STILL, "stand"
        down = self.data.get("down") or now
        self.data["down"] = down
        if now - down >= LIFTED_CLEAR_S:
            self.goal = "look"
            self._go("look", now)
        return STILL, "stand"

    # ---------- домой ----------
    def _home_search(self, tel, events, vision, now):
        if vision.get("dock"):
            self._go("home_align", now, seen=now)
            return STILL, "stand"
        if tel.get("beacon", "none") != "none":
            self._go("home_center", now, phase="edge")
            return STILL, "stand"
        if self.heading - self.data["h0"] >= SEARCH_TURN:
            self._go("home_lost", now)
            return STILL, "stand"
        return (0, 0, SEARCH_RATE), "stand"

    def _home_align(self, tel, events, vision, now):
        """По метке — в точку на оси станции лицом к башенке: шагом вперёд-назад, вбок и поворотом сразу."""
        dock = vision.get("dock")
        if dock is None:
            if now - self.data["seen"] > TAG_LOST_S:
                self._go("home_search", now)
            return STILL, "stand"
        self.data["seen"] = now
        ex, ey, eyaw = ALIGN_X - dock["x_mm"], -dock["y_mm"], -dock["yaw_deg"]
        if abs(ex) < ALIGN_TOL[0] and abs(ey) < ALIGN_TOL[1] and abs(eyaw) < ALIGN_TOL[2]:
            self._go("home_approach", now, ref=None, step="pad")
            return STILL, "stand"
        c, s = math.cos(math.radians(dock["yaw_deg"])), math.sin(math.radians(dock["yaw_deg"]))
        rx, ry = c * ex + s * ey, -s * ex + c * ey                  # ошибка в системе корпуса
        return (clip(ALIGN_GAIN * rx, ALIGN_V[0]), clip(ALIGN_GAIN * ry, ALIGN_V[1]),
                clip(TURN_GAIN * eyaw, ALIGN_TURN)), "stand"

    def _home_center(self, tel, events, vision, now):
        """Пройти сектор, где маяк видят оба приёмника, туда и обратно и встать на его середину. Направление на маяк
        приходит с опозданием (окно счёта 100 мс), и края сектора замечаются позже по ходу поворота; при проходе
        в обе стороны опоздания гасятся."""
        seen = tel.get("beacon", "none")
        if vision.get("dock"):
            self._go("home_align", now, seen=now)
            return STILL, "stand"
        if seen == "none":
            self._go("home_search", now)
            return STILL, "stand"
        step = CENTER_STEPS[self.data["phase"]]
        return step(self, seen, now), "stand"

    def _center_edge(self, seen, now):
        if seen == "ahead":
            return (0, 0, -CENTER_RATE)
        self.data.update(phase="sweep", sign=1 if seen == "left" else -1, edges=[], inside=False)
        return (0, 0, self.data["sign"] * CENTER_RATE)

    def _center_sweep(self, seen, now):
        d = self.data
        if (seen == "ahead") != d["inside"]:
            d["inside"] = not d["inside"]
            d["edges"].append(self.heading)
            if len(d["edges"]) == 2:
                d["sign"] = -d["sign"]
            elif len(d["edges"]) == 4:
                d.update(phase="back", target=sum(d["edges"]) / 4)
                return STILL
        return (0, 0, d["sign"] * CENTER_RATE)

    def _center_back(self, seen, now):
        turn = self.turn_to(self.data["target"], CENTER_RATE)
        if turn is None:
            self._go("home_approach", now, ref=None, step="pad")
            return STILL
        return turn

    def _home_approach(self, tel, events, vision, now):
        """Вперёд, пока передние датчики края не покажут: площадка (ближе), снова стол, башенка (ближе)."""
        if self._passed_pad_reached_tower(tel.get("edge") or [0] * 6):
            self._go("home_back", now)
            return STILL, "stand"
        dock = vision.get("dock")
        if dock is not None and (abs(dock["y_mm"]) > REALIGN_MM or abs(dock["yaw_deg"]) > REALIGN_DEG):
            self._go("home_align", now, seen=now)
            return STILL, "stand"
        return self._steer(dock), "stand"

    def _passed_pad_reached_tower(self, edge) -> bool:
        d = (edge[FRONT[0]] + edge[FRONT[1]]) / 2
        ref = self.data["ref"] = self.data["ref"] or d
        step = self.data["step"]
        if step == "pad" and d <= ref - DROP_MM:
            self.data["step"] = "table"
        elif step == "table" and d >= ref - BACK_MM:
            self.data["step"] = "tower"
        return step == "tower" and d <= ref - DROP_MM

    def _steer(self, dock) -> tuple:
        """Прямо к станции: по метке — поправка вбок и по курсу, без неё — держать курс гироскопом."""
        if dock is not None:
            return (APPROACH_SPEED, clip(-SIDE_GAIN * dock["y_mm"], SIDE_MAX), clip(-HOLD_GAIN * dock["yaw_deg"], HOLD_MAX))
        return (APPROACH_SPEED, 0, clip(HOLD_GAIN * (self.data["h0"] - self.heading), HOLD_MAX))

    def _back_for(self, sec, then, pose, now):
        """Пятиться sec секунд, потом — состояние then."""
        if now - self.t0 >= sec:
            self._go(then, now)
            return STILL, pose
        return (-APPROACH_SPEED, 0, 0), "stand"

    def _home_back(self, tel, events, vision, now):
        return self._back_for(OVERSHOOT_S, "home_lie", "lie", now)

    def _home_lie(self, tel, events, vision, now):
        bat = tel.get("bat") or [0, 0]
        if "docked" in events or (len(bat) > 1 and bat[1] < CHARGE_A):
            self.goal = "idle"
            self._go("docked", now)
        elif now - self.t0 >= LIE_WAIT_S:
            if self.retries:
                self._go("home_failed", now)
                return STILL, "stand"
            self.retries += 1
            self._go("home_retry", now)
            return (-APPROACH_SPEED, 0, 0), "stand"
        return STILL, "lie"

    def _home_retry(self, tel, events, vision, now):
        return self._back_for(RETRY_BACK_S, "home_search", "stand", now)

    def _docked(self, tel, events, vision, now):
        return STILL, "lie"

    def _stopped(self, tel, events, vision, now):
        return STILL, "stand"


def clip(v: float, limit: float) -> float:
    return max(-limit, min(limit, v))


def away_from(far) -> tuple:
    """Шаг прочь от датчиков, под которыми пусто."""
    vx = (EDGE_SPEED if any(far[i] for i in BACK) else 0) - (EDGE_SPEED if any(far[i] for i in FRONT) else 0)
    vy = (EDGE_SPEED if any(far[i] for i in RIGHT) else 0) - (EDGE_SPEED if any(far[i] for i in LEFT) else 0)
    return (vx, vy, 0)


STATES = {"idle": Behavior._idle, "look": Behavior._look, "hand": Behavior._hand, "at_hand": Behavior._at_hand,
          "edge": Behavior._edge, "lifted": Behavior._lifted, "home_search": Behavior._home_search,
          "home_align": Behavior._home_align, "home_center": Behavior._home_center, "home_approach": Behavior._home_approach, "home_back": Behavior._home_back,
          "home_lie": Behavior._home_lie, "home_retry": Behavior._home_retry, "docked": Behavior._docked,
          "home_lost": Behavior._stopped, "home_failed": Behavior._stopped}
CENTER_STEPS = {"edge": Behavior._center_edge, "sweep": Behavior._center_sweep, "back": Behavior._center_back}
