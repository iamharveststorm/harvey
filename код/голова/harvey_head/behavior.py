"""Поведение Харви: телеметрия и события «спинного мозга» + «зрение» → команда корпусу.

Команда — {"v": (вперёд мм/с, влево мм/с, поворот °/с, + — налево), "pose": "stand" | "lie", "state": …}; её превращает
в шаги модуль походки. Рефлексы края и «подняли» остаются в RP2350: поведение лишь решает, что делать дальше.

Цели (request): «look» — осмотреться, «hand» — подойти к руке, «home» — на станцию, «turn» (deg=…) — повернуться
на угол на месте (к человеку; + — налево).
«Зрение» (камера, разбор — на голове, harvey_head/dock_tag.py, или на ПК) — словарь находок: "hand" и "dock" —
{"bearing_deg", "dist_mm"} руки или метки AprilTag станции в кадре.
Домой — без ПК и в темноте: найти станцию (метка или ИК-маяк), повернуться к ней (по метке — сразу, по маяку — проход
сектора туда и обратно), выйти на ось станции по центральному ИК-приёмнику (tel["axis"]: станция шлёт пачки левого и
правого светодиода, за перегородкой оба видны только в клине вдоль оси) шагом вбок, держа станцию перед собой, и идти
прямо, поправляясь вбок и по курсу по тому же клину. Метка лишь точнее держит направление; ось даёт только маяк.
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
CENTER_RATE = 30.0                                        # проход сектора маяка; опоздание сигнала гасит проход в обе стороны
APPROACH_SPEED, DROP_MM, BACK_MM = 40.0, 8, 4             # площадка и башенка ближе стола на ≥ 8 мм; «снова стол» — в 4 мм
HOLD_GAIN, HOLD_MAX = 2.0, 15.0                           # держать курс при ходьбе
FACE_DONE = 1.0                                           # повернулся к метке — в 1°
AXIS_V, AXIS_D, AXIS_TIMEOUT_S, AXIS_CREEP = 25.0, 400.0, 25.0, 20.0   # шаг вбок к оси; до станции, если метки нет
FINE_V, LOST_S, AXIS_DONE_MM = 5.0, 1.0, 1.0              # на заходе: ушёл из клина — шаг вбок 5 мм/с (резкая смена шага вбок дёргает корпус); середина клина — в 1 мм
OVERSHOOT_S = 0.45                                        # башенку видно, когда корпус на ~17 мм дальше контактов
TABLE_HOLD_S = 0.6                                        # «снова стол» — не меньше 0,6 с: у края площадки луч дрожит от шага
LIE_WAIT_S, RETRY_BACK_S = 3.0, 5.0                       # повтор: отойти на 20 см — чтобы снова увидеть площадку
CHARGE_A = -0.05                                          # ток заряда (как spine.CHARGE_A)


class Behavior:
    def __init__(self, now: float = 0.0):
        self.goal, self.state = "idle", "idle"
        self.t0 = now
        self.data: dict = {}
        self.retries = 0
        self.heading, self.t_last, self.dt = 0.0, now, 0.0
        self.on_axis = False                                # на оси станции — осталось повернуться к ней и идти

    # ---------- управление ----------
    def request(self, goal: str, now: float, **data) -> None:
        self.goal = "idle" if goal == "turn" else goal       # поворот — разовое действие: после края возвращаемся в покой
        self.retries = 0
        self.on_axis = False
        self._begin(goal, now, **data)

    def _begin(self, goal: str, now: float, **data) -> None:
        start = {"look": "look", "hand": "hand", "home": "home_search", "idle": "idle", "turn": "turn"}
        self._go(start[goal], now, **data)

    def _go(self, state: str, now: float, **data) -> None:
        self.state, self.t0, self.data = state, now, dict(data, h0=self.heading)

    def turn_to(self, target: float, rate: float) -> tuple | None:
        """Поворот к курсу target; None — уже на нём."""
        err = target - self.heading
        if abs(err) < TURN_DONE:
            return None
        return (0, 0, max(-rate, min(rate, TURN_GAIN * err)))

    def update(self, tel: dict, events: list[str], vision: dict | None, now: float) -> dict:
        self.dt = now - self.t_last
        self.heading += (tel.get("gyr") or [0, 0, 0])[2] * self.dt
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

    def _turn(self, tel, events, vision, now):
        """Повернуться на data["deg"] (+ — налево) по гироскопу, потом покой. Угол — короткой дорогой, в (−180, 180]."""
        turn = self.turn_to(self.data["h0"] + short_way(self.data["deg"]), LOOK_RATE)
        if turn is None:
            self.goal = "idle"
            self._go("idle", now)
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
    def _faced(self, now):
        """Повернулся к станции: если уже на оси — заход, иначе — выйти на ось."""
        if self.on_axis:
            self._go("home_approach", now, ref=None, step="pad", lost=None)
        else:
            self._go("home_axis", now, lat=0.0, vy=0.0, edges=[], inside=None)

    def _home_search(self, tel, events, vision, now):
        self.on_axis = False
        if vision.get("dock"):
            self._go("home_face", now)
            return STILL, "stand"
        if tel.get("beacon", "none") != "none":
            self._go("home_center", now, phase="edge")
            return STILL, "stand"
        if self.heading - self.data["h0"] >= SEARCH_TURN:
            self._go("home_lost", now)
            return STILL, "stand"
        return (0, 0, SEARCH_RATE), "stand"

    def _home_face(self, tel, events, vision, now):
        """Метка в кадре — повернуться прямо к ней."""
        dock = vision.get("dock")
        if dock is None:
            self._go("home_search", now)
            return STILL, "stand"
        if abs(dock["bearing_deg"]) < FACE_DONE:
            self._faced(now)
            return STILL, "stand"
        return (0, 0, clip(TURN_GAIN * dock["bearing_deg"], CENTER_RATE)), "stand"

    def _home_axis(self, tel, events, vision, now):
        """Выйти на ось станции: шагом вбок пройти клин, где центральный приёмник видит оба светодиода, туда и обратно
        (как сектор маяка) и встать на его середину. Станцию держать перед собой (по метке — доворот на неё, без метки —
        доворот на шаг вбок с расстояния AXIS_D, курс держит гироскоп): если смотреть прямо на маяк и приёмник на оси,
        то и центр корпуса на оси. Потом снова повернуться к станции — точнее, чем доворот на ходу."""
        side, dock, d = tel.get("axis", "none"), vision.get("dock"), self.data
        if now - self.t0 > AXIS_TIMEOUT_S:
            self._go("home_search", now)
            return STILL, "stand"
        d["lat"] += d["vy"] * self.dt
        if side == "none":
            d.update(edges=[], inside=None, vy=0.0)
            return (AXIS_CREEP, 0, self._facing(dock, 0.0)), "stand"
        if d["edges"] == [] and d["inside"] is None:
            d["inside"] = side == "on"
        vy = self._cross_wedge(side, d)
        if vy is None:
            self.on_axis = True
            self._go("home_center" if dock is None else "home_face", now, phase="edge")
            return STILL, "stand"
        d["vy"] = vy
        return (0, vy, self._facing(dock, vy)), "stand"

    def _facing(self, dock, vy) -> float:
        """Доворот, чтобы станция оставалась впереди при шаге вбок. По метке — на неё; без метки — заданный курс
        сдвигается на доворот от шага вбок с расстояния AXIS_D, а гироскоп держит его против увода."""
        if dock:
            return clip(TURN_GAIN * dock["bearing_deg"] + math.degrees(-vy / dock["dist_mm"]), CENTER_RATE)
        turn = math.degrees(-vy / AXIS_D)
        self.data["h_hold"] = self.data.get("h_hold", self.heading) + turn * self.dt
        return clip(turn + HOLD_GAIN * (self.data["h_hold"] - self.heading), CENTER_RATE)

    def _cross_wedge(self, side, d) -> float | None:
        """Скорость вбок, чтобы пройти клин туда и обратно и встать на середину; None — уже на середине.
        Корпус догоняет команду шага с запаздыванием ~0,3 с, и край, замеченный на ходу, сдвинут по ходу. Четыре края —
        два прохода в разные стороны — это сдвиг гасят; на месте счёт шагов по командам точен."""
        inside = side == "on"
        if inside != d["inside"]:
            d["inside"] = inside
            if d["edges"] or inside:
                d["edges"].append(d["lat"])
                if len(d["edges"]) == 2:
                    d["dir"] = -d["dir"]
        if len(d["edges"]) >= 4:
            err = sum(d["edges"][:4]) / 4 - d["lat"]
            return None if abs(err) < AXIS_DONE_MM else clip(2.0 * err, AXIS_V)
        if not d["edges"]:                                  # ещё не входили в клин: к оси (изнутри — сначала вправо)
            d["dir"] = AXIS_V if side == "right" else -AXIS_V
        return d["dir"]

    def _home_center(self, tel, events, vision, now):
        """Пройти сектор, где маяк видят оба приёмника, туда и обратно и встать на его середину. Направление на маяк
        приходит с опозданием (окно счёта 100 мс), и края сектора замечаются позже по ходу поворота; при проходе
        в обе стороны опоздания гасятся."""
        seen = tel.get("beacon", "none")
        if vision.get("dock"):
            self._go("home_face", now)
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
            self._faced(now)
            return STILL
        return turn

    def _home_approach(self, tel, events, vision, now):
        """Вперёд, пока передние датчики края не покажут: площадка (ближе), снова стол, башенка (ближе)."""
        if self._passed_pad_reached_tower(tel.get("edge") or [0] * 6, now):
            self._go("home_back", now)
            return STILL, "stand"
        side = tel.get("axis", "none")
        if side == "none":
            lost = self.data["lost"] = self.data["lost"] or now
            if now - lost > LOST_S:
                self.on_axis = False
                self._go("home_axis", now, lat=0.0, vy=0.0, edges=[], inside=None)
                return STILL, "stand"
        else:
            self.data["lost"] = None
        return self._steer(side), "stand"

    def _passed_pad_reached_tower(self, edge, now) -> bool:
        d = (edge[FRONT[0]] + edge[FRONT[1]]) / 2
        ref = self.data["ref"] = self.data["ref"] or d
        near, table = d <= ref - DROP_MM, d >= ref - BACK_MM
        step = self.data["step"]
        if step == "pad":
            if near:
                self.data["step"] = "table"
            return False
        if step == "table":
            if table:
                self.data.update(step="tower", t_table=now)
            return False
        return near and self._table_held(now)

    def _table_held(self, now) -> bool:
        """Стол под датчиками держался TABLE_HOLD_S — значит, это башенка; иначе луч дрогнул у края площадки."""
        if now - self.data["t_table"] >= TABLE_HOLD_S:
            return True
        self.data["step"] = "table"
        return False

    def _steer(self, side) -> tuple:
        """Прямо по оси, курс — гироскопом (его задал поворот к станции с оси). Вышел из клина — шаг вбок к оси.
        Приёмник клина — в 71 мм перед центром корпуса, поэтому важен именно курс: 2,5° мимо оси — это 3 мм брюха мимо
        контактов. На метку у самой станции не довернуть: с близкого расстояния это раскачивает."""
        vy = -FINE_V if side == "left" else FINE_V if side == "right" else 0
        return (APPROACH_SPEED, vy, clip(HOLD_GAIN * (self.data["h0"] - self.heading), HOLD_MAX))

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
        """Не замкнулось: отойти и сразу снова выйти на ось — Харви стоит лицом к станции почти на ней, искать не нужно."""
        if now - self.t0 >= RETRY_BACK_S:
            self.on_axis = False
            self._faced(now)
            return STILL, "stand"
        return (-APPROACH_SPEED, 0, 0), "stand"

    def _docked(self, tel, events, vision, now):
        return STILL, "lie"

    def _stopped(self, tel, events, vision, now):
        return STILL, "stand"


def clip(v: float, limit: float) -> float:
    return max(-limit, min(limit, v))


def short_way(deg: float) -> float:
    """Угол в (−180, 180]: 350° — это −10°."""
    deg %= 360.0
    return deg - 360.0 if deg > 180.0 else deg


def away_from(far) -> tuple:
    """Шаг прочь от датчиков, под которыми пусто."""
    vx = (EDGE_SPEED if any(far[i] for i in BACK) else 0) - (EDGE_SPEED if any(far[i] for i in FRONT) else 0)
    vy = (EDGE_SPEED if any(far[i] for i in RIGHT) else 0) - (EDGE_SPEED if any(far[i] for i in LEFT) else 0)
    return (vx, vy, 0)


STATES = {"idle": Behavior._idle, "look": Behavior._look, "turn": Behavior._turn, "hand": Behavior._hand, "at_hand": Behavior._at_hand,
          "edge": Behavior._edge, "lifted": Behavior._lifted, "home_search": Behavior._home_search,
          "home_face": Behavior._home_face, "home_axis": Behavior._home_axis, "home_center": Behavior._home_center, "home_approach": Behavior._home_approach, "home_back": Behavior._home_back,
          "home_lie": Behavior._home_lie, "home_retry": Behavior._home_retry, "docked": Behavior._docked,
          "home_lost": Behavior._stopped, "home_failed": Behavior._stopped}
CENTER_STEPS = {"edge": Behavior._center_edge, "sweep": Behavior._center_sweep, "back": Behavior._center_back}
