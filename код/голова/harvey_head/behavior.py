"""Поведение Харви: телеметрия и события «спинного мозга» + «зрение» → команда корпусу.

Команда — {"v": (вперёд мм/с, влево мм/с, поворот °/с, + — налево), "pose": "stand" | "lie", "state": …}; её превращает
в шаги модуль походки. Рефлексы края и «подняли» остаются в RP2350: поведение лишь решает, что делать дальше.

Цели (request): «look» — осмотреться, «hand» — подойти к руке, «home» — на станцию по ИК-маяку.
Числа — оценки по симуляции (код/симуляция/мини/mini_behave.py), ПРЕДВАРИТЕЛЬНО: уточнить на роботе.
"""
from __future__ import annotations

STILL = (0, 0, 0)
FRONT, BACK, LEFT, RIGHT = (0, 1), (2, 3), (4,), (5,)    # индексы датчиков края: FL, FR, BL, BR, L, R

LOOK_RATE, LOOK_STEP, LOOK_PAUSE, LOOK_STOPS = 40.0, 60.0, 1.0, 6
HAND_TURN, HAND_SPEED, HAND_GAIN, HAND_AIM, HAND_STOP_MM, HAND_LOST_S = 30.0, 40.0, 1.5, 8.0, 90, 0.5
EDGE_SPEED, EDGE_EXTRA_S, EDGE_TURN, EDGE_RATE = 30.0, 0.5, 120.0, 40.0
LIFTED_CLEAR_S = 1.0
SEARCH_RATE, SEARCH_TURN = 30.0, 378.0                    # полный оборот с запасом 5 %
CENTER_RATE = 20.0
APPROACH_SPEED, DROP_MM, BACK_MM = 40.0, 8, 4             # площадка и башенка ближе стола на ≥ 8 мм; «снова стол» — в 4 мм
OVERSHOOT_S = 0.45                                        # башенку видно, когда корпус на ~17 мм дальше контактов
LIE_WAIT_S, RETRY_BACK_S = 3.0, 2.0
CHARGE_A = -0.05                                          # ток заряда (как spine.CHARGE_A)


class Behavior:
    def __init__(self, now: float = 0.0):
        self.goal, self.state = "idle", "idle"
        self.t0 = now
        self.data: dict = {}
        self.retries = 0

    # ---------- управление ----------
    def request(self, goal: str, now: float) -> None:
        self.goal = goal
        self.retries = 0
        self._begin(goal, now)

    def _begin(self, goal: str, now: float) -> None:
        start = {"look": "look", "hand": "hand", "home": "home_search", "idle": "idle"}
        self._go(start[goal], now)

    def _go(self, state: str, now: float, **data) -> None:
        self.state, self.t0, self.data = state, now, data

    def update(self, tel: dict, events: list[str], vision: dict | None, now: float) -> dict:
        self._interrupts(tel, events, now)
        v, pose = STATES[self.state](self, tel, events, vision, now)
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
        if vision is not None and self.goal in ("look", "hand"):
            self.goal = "hand"
            self._go("hand", now)
            return STILL, "stand"
        cycle = LOOK_PAUSE + LOOK_STEP / LOOK_RATE
        k, phase = divmod(now - self.t0, cycle)
        if k >= LOOK_STOPS:
            self.goal = "idle"
            self._go("idle", now)
            return STILL, "stand"
        return ((0, 0, LOOK_RATE) if phase >= LOOK_PAUSE else STILL), "stand"

    def _hand(self, tel, events, vision, now):
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
        if vision is not None and vision["dist_mm"] > HAND_STOP_MM + 30:
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
            return self.data.get("away", STILL), "stand"
        if now - clear < EDGE_EXTRA_S + EDGE_TURN / EDGE_RATE:
            return (0, 0, EDGE_RATE), "stand"
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
        if tel.get("beacon", "none") != "none":
            self._go("home_center", now, phase="edge")
            return STILL, "stand"
        if now - self.t0 >= SEARCH_TURN / SEARCH_RATE:
            self._go("home_lost", now)
            return STILL, "stand"
        return (0, 0, SEARCH_RATE), "stand"

    def _home_center(self, tel, events, vision, now):
        """Пройти сектор, где маяк видят оба приёмника, и вернуться на его середину (по времени поворота)."""
        seen = tel.get("beacon", "none")
        if seen == "none":
            self._go("home_search", now)
            return STILL, "stand"
        step = CENTER_STEPS[self.data["phase"]]
        return step(self, seen, now), "stand"

    def _center_edge(self, seen, now):
        if seen == "ahead":
            return (0, 0, -CENTER_RATE)
        self.data.update(phase="sweep", sign=1 if seen == "left" else -1, t_in=None)
        return (0, 0, self.data["sign"] * CENTER_RATE)

    def _center_sweep(self, seen, now):
        d = self.data
        if seen == "ahead" and d["t_in"] is None:
            d["t_in"] = now
        elif seen != "ahead" and d["t_in"] is not None:
            d.update(phase="back", t_end=now + (now - d["t_in"]) / 2)
        return (0, 0, d["sign"] * CENTER_RATE * (-1 if d["phase"] == "back" else 1))

    def _center_back(self, seen, now):
        if now >= self.data["t_end"]:
            self._go("home_approach", now, ref=None, step="pad")
            return STILL
        return (0, 0, -self.data["sign"] * CENTER_RATE)

    def _home_approach(self, tel, events, vision, now):
        """Вперёд, пока передние датчики края не покажут: площадка (ближе), снова стол, башенка (ближе)."""
        edge = tel.get("edge") or [0] * 6
        d = (edge[FRONT[0]] + edge[FRONT[1]]) / 2
        ref = self.data["ref"] = self.data["ref"] or d
        step = self.data["step"]
        if step == "pad" and d <= ref - DROP_MM:
            self.data["step"] = "table"
        elif step == "table" and d >= ref - BACK_MM:
            self.data["step"] = "tower"
        elif step == "tower" and d <= ref - DROP_MM:
            self._go("home_back", now)
            return STILL, "stand"
        return (APPROACH_SPEED, 0, 0), "stand"

    def _home_back(self, tel, events, vision, now):
        if now - self.t0 >= OVERSHOOT_S:
            self._go("home_lie", now)
            return STILL, "lie"
        return (-APPROACH_SPEED, 0, 0), "stand"

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
        if now - self.t0 >= RETRY_BACK_S:
            self._go("home_search", now)
            return STILL, "stand"
        return (-APPROACH_SPEED, 0, 0), "stand"

    def _docked(self, tel, events, vision, now):
        return STILL, "lie"

    def _stopped(self, tel, events, vision, now):
        return STILL, "stand"


def away_from(far) -> tuple:
    """Шаг прочь от датчиков, под которыми пусто."""
    vx = (EDGE_SPEED if any(far[i] for i in BACK) else 0) - (EDGE_SPEED if any(far[i] for i in FRONT) else 0)
    vy = (EDGE_SPEED if any(far[i] for i in RIGHT) else 0) - (EDGE_SPEED if any(far[i] for i in LEFT) else 0)
    return (vx, vy, 0)


STATES = {"idle": Behavior._idle, "look": Behavior._look, "hand": Behavior._hand, "at_hand": Behavior._at_hand,
          "edge": Behavior._edge, "lifted": Behavior._lifted, "home_search": Behavior._home_search,
          "home_center": Behavior._home_center, "home_approach": Behavior._home_approach, "home_back": Behavior._home_back,
          "home_lie": Behavior._home_lie, "home_retry": Behavior._home_retry, "docked": Behavior._docked,
          "home_lost": Behavior._stopped, "home_failed": Behavior._stopped}
CENTER_STEPS = {"edge": Behavior._center_edge, "sweep": Behavior._center_sweep, "back": Behavior._center_back}
