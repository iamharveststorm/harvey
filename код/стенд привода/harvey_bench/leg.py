"""Стенд одной ноги «Компакт мини» (STS3032): калибровка, позы, стойка на весах, момент бедра, шаг 10 минут.

Приводы: 1 — поворот (coxa), 2 — бедро (femur), 3 — колено (knee). Размеры и правила движения — из CAD
(модели/мини/harvey_mini_parts.py): поворот ±20°, бедро −45…+85°, колено −130…−60°, стойка (0°, 20°, −110°).
Углы: бедро «+» — вверх, колено «+» — голень наружу (от стенда), поворот «+» — против часовой, если смотреть сверху.
Поза сборки «Г»: поворот 0°, бедро 0° (горизонтально), колено −90° (голень вертикально вниз) — это середина 2048.
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from . import sts

CAL_FILE = Path("leg_calibration.json")
IDS = {"coxa": 1, "femur": 2, "knee": 3}
NAMES = {"coxa": "поворот", "femur": "бедро", "knee": "колено"}
REF = {"coxa": 0.0, "femur": 0.0, "knee": -90.0}               # поза «Г» = 2048
LIMITS = {"coxa": (-20.0, 20.0), "femur": (-45.0, 85.0), "knee": (-130.0, -60.0)}
STANCE = (0.0, 20.0, -110.0)
CHECK_POSES = [(0, 20, -110), (0, 40, -110), (0, 0, -90), (0, -20, -70), (0, 60, -130), (0, 85, -130),
               (0, -45, -60), (0, 20, -60), (0, 50, -90), (-20, 40, -110), (20, 40, -110)]

# мини целиком (для оценки батареи): модели/мини, заметки/Компакт мини.md
ROBOT_G = 893.0
BATTERY_WH = 22.0
DCDC_EFF = 0.88
ELECTRONICS_W = 2.5           # Pi Zero 2 W, камера, 2 дисплея, датчики
LEGS = 6


@dataclass(frozen=True)
class LegGeometry:
    cox: float = 27.0
    fem: float = 30.0
    tib: float = 48.0           # от оси колена до низа стопы
    foot_r: float = 5.0

    @property
    def l2(self) -> float:       # от оси колена до центра сферы стопы
        return self.tib - self.foot_r

    @property
    def zj(self) -> float:       # ось бедра над столом в стойке
        return self.tib - self.fem * math.sin(math.radians(20))

    def foot(self, qf: float, qk: float) -> tuple[float, float]:
        """(вынос от оси бедра, высота низа стопы от оси бедра), мм; углы в радианах."""
        r = self.fem * math.cos(qf) + self.l2 * math.cos(qf + qk)
        h = self.fem * math.sin(qf) + self.l2 * math.sin(qf + qk) - self.foot_r
        return r, h

    def horizontal(self, qf: float, qk: float) -> float:
        """Плечо силы стопы относительно оси бедра (мм)."""
        return self.foot(qf, qk)[0]

    def ik(self, r: float, h: float) -> tuple[float, float]:
        """Углы бедра и колена (градусы) для низа стопы в точке (r, h) от оси бедра. Решение «колено вверх»."""
        hc = h + self.foot_r
        d = min(max(math.hypot(r, hc), abs(self.l2 - self.fem) + 1e-3), self.fem + self.l2 - 1e-3)
        qf = math.atan2(hc, r) + math.acos(max(-1.0, min(1.0, (self.fem ** 2 + d * d - self.l2 ** 2) / (2 * self.fem * d))))
        qk = -(math.pi - math.acos(max(-1.0, min(1.0, (self.fem ** 2 + self.l2 ** 2 - d * d) / (2 * self.fem * self.l2)))))
        return math.degrees(qf), math.degrees(qk)

    def femur_for_height(self, qk: float, h: float, guess: float) -> float:
        """Угол бедра (рад), при котором низ стопы на высоте h при данном колене — для имитации упора."""
        lo, hi = guess, guess + 0.8                   # стопа ниже нужного: бедро поднимается, пока не коснётся
        f = lambda q: self.foot(q, qk)[1] - h
        if f(lo) * f(hi) > 0:
            return guess
        for _ in range(40):
            mid = (lo + hi) / 2
            if f(lo) * f(mid) <= 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2

    def stance_target(self) -> tuple[float, float]:
        r, h = self.foot(math.radians(STANCE[1]), math.radians(STANCE[2]))
        return r, h


GEOM = LegGeometry()


@dataclass
class LegCal:
    sign: dict = field(default_factory=lambda: {k: 1 for k in IDS})
    offset: dict = field(default_factory=lambda: {k: 0 for k in IDS})      # шагов, если «середина» не записалась
    checked: bool = False

    @classmethod
    def load(cls) -> "LegCal":
        if CAL_FILE.exists():
            try:
                d = json.loads(CAL_FILE.read_text(encoding="utf-8"))
                return cls(d["sign"], d["offset"], d.get("checked", False))
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        CAL_FILE.write_text(json.dumps(dict(sign=self.sign, offset=self.offset, checked=self.checked), ensure_ascii=False,
                                       indent=1), encoding="utf-8")

    def to_pos(self, j: str, deg: float) -> int:
        return int(round(sts.MIDDLE + self.offset[j] + self.sign[j] * (deg - REF[j]) / sts.DEG_PER_STEP))

    def to_deg(self, j: str, pos: int) -> float:
        return REF[j] + self.sign[j] * (pos - sts.MIDDLE - self.offset[j]) * sts.DEG_PER_STEP


def clamp(j: str, deg: float) -> float:
    lo, hi = LIMITS[j]
    return max(lo, min(hi, deg))


def step_pose(ph: float, sweep: float, down: tuple[float, float], up: tuple[float, float]) -> tuple[float, float, float]:
    """Поза шага на месте в фазе ph (0…1): первая половина — опора (стопа на столе с нажимом, поворот +sweep → −sweep),
    вторая — перенос (подъём по синусу до up и обратно, поворот −sweep → +sweep). Углы в градусах."""
    if ph < 0.5:
        return sweep * (1 - 4 * ph), down[0], down[1]
    k = math.sin(math.pi * (ph - 0.5) * 2)
    return (-sweep + 4 * sweep * (ph - 0.5),
            down[0] + (up[0] - down[0]) * k,
            down[1] + (up[1] - down[1]) * k)


LOG_HEADER = ["Время, с", "Темп. поворота, °C", "Темп. бедра, °C", "Темп. колена, °C",
              "Ток поворота, А", "Ток бедра, А", "Ток колена, А",
              "Нагрузка поворота, %", "Нагрузка бедра, %", "Нагрузка колена, %", "Напряжение, В"]


def parse_grams(text: str) -> float | None:
    """Показание весов, как его ввёл человек: «350», «350,5» или «350.5». Не число — None."""
    t = text.replace(",", ".")
    return float(t) if t.replace(".", "", 1).isdigit() else None


def stance_ok(grams: float | None, end: float | None, load: float) -> bool:
    """Норма стойки: держит ≥ 300 г, за время стойки просело не больше 10 %, бедро нагружено ≤ 80 %."""
    return bool(grams and grams >= 300 and end is not None and end >= 0.9 * grams and load <= 80)


def abort_reason(peak: dict, volt: float, vmin: float) -> str:
    """Почему остановить шаг: датчик привода дошёл до 65 °C или напряжение ниже допустимого. Пусто — шагать дальше."""
    if max(peak.values()) >= 65:
        return "остановлен: датчик привода 65 °C"
    if volt < vmin:
        return f"остановлен: напряжение {volt:.1f} В"
    return ""


def gait_ok(aborted: str, femur_peak: float, case: float | None) -> bool:
    """Норма шага: не остановлен, датчик бедра и корпус по термопаре (если мерили) ≤ 60 °C."""
    return not aborted and femur_peak <= 60 and (case is None or case <= 60)


QUESTIONS = {"coxa": "Нога повернулась ПРОТИВ часовой стрелки, если смотреть сверху?",
             "femur": "Бедро поднялось ВВЕРХ?",
             "knee": "Низ голени ушёл НАРУЖУ — от стенда?"}


def middle_offset(pos: int) -> int:
    """Насколько привод не принял «середину» (шагов). До 3 шагов — шум датчика, считаем, что записалась."""
    return 0 if abs(pos - sts.MIDDLE) <= 3 else pos - sts.MIDDLE


def direction(answer: str) -> int:
    """Сустав сдвинулся «+10°» туда, куда надо? «н…» — нет, направление обратное (−1); иначе +1."""
    return -1 if answer.lower().startswith("н") else 1


def torque_nm(grams: float, arm_mm: float) -> float:
    """Момент бедра (Н·м) по показанию весов (г) и плечу стопы от оси бедра (мм)."""
    return grams / 1000 * 9.81 * arm_mm / 1000


def stall_current(psu_a: float | None, idle_a: float) -> float | None:
    """Ток бедра в упоре: показание блока питания минус покой двух других приводов ноги. Нет показания — None."""
    return (psu_a - 2 * idle_a) if psu_a else None


class Leg:
    """Нога поверх стенда (Bench): позы, чтение углов, тесты."""

    def __init__(self, bench):
        self.b, self.cal = bench, LegCal.load()
        self.press_mm = 2.0                      # насколько стопа «давит вниз» в стойке (подбирается на весах)
        self.stand = {}                          # итоги стойки — для оценки батареи

    # ---------- базовое ----------
    def servos(self) -> dict:
        return {j: self.b.servo(i) for j, i in IDS.items()}

    def present(self) -> list[str]:
        return [j for j, i in IDS.items() if self.b.bus.ping(i)]

    def require(self) -> bool:
        miss = [f"№{IDS[j]} ({NAMES[j]})" for j in IDS if j not in self.present()]
        if miss:
            print("  Не отвечают приводы: " + ", ".join(miss) + ". Назначь номера 1–3 (пункт 2) и проверь кабели.")
            return False
        return True

    def angles(self) -> dict:
        return {j: self.cal.to_deg(j, s.pos()) for j, s in self.servos().items()}

    def goto(self, qc: float, qf: float, qk: float, seconds: float = 1.0, wait: bool = True) -> None:
        """Плавно в позу (углы в пределах правил) — все суставы приходят одновременно."""
        target = {"coxa": clamp("coxa", qc), "femur": clamp("femur", qf), "knee": clamp("knee", qk)}
        sv = self.servos()
        now = {j: s.pos() for j, s in sv.items()}
        for j, s in sv.items():
            goal = self.cal.to_pos(j, target[j])
            speed = max(50, int(abs(goal - now[j]) / max(seconds, 0.05)))
            s.move(goal, speed=speed, accel=30)
        if wait:
            self.b.sleep(seconds + 0.3)

    def stream(self, qc: float, qf: float, qk: float) -> None:
        """Быстрое обновление цели всех трёх одним пакетом без ответа (для шага)."""
        t = {"coxa": clamp("coxa", qc), "femur": clamp("femur", qf), "knee": clamp("knee", qk)}
        self.b.bus.sync_write(sts.GOAL_POS, {IDS[j]: self.cal.to_pos(j, t[j]) for j in IDS})

    def torque(self, on: bool) -> None:
        for s in self.servos().values():
            s.torque(on)

    def hold_current_pose(self, limit: float = 100) -> None:
        for s in self.servos().values():
            s.set_torque_limit(limit)
            p = s.pos()
            s.move(p, speed=600, accel=30)
        self.torque(True)

    def amps(self, st: sts.State) -> float:
        return self.b.amps(st)

    def precheck(self) -> bool:
        return all(self.b.precheck(s) for s in self.servos().values())

    # ---------- сборка и калибровка ----------
    def center_all(self) -> None:
        print("\nЦентровка перед сборкой: все найденные приводы — в середину (2048).")
        print("  Качалки пока без деталей. После центровки надень диски так, чтобы нога встала буквой «Г»:")
        print("  поворот — прямо от стенда, бедро — горизонтально, голень — вертикально вниз.")
        print("  В позе «Г» стопа ниже стола на 10 мм: стенд для этого ставь у края стола, нога — за краем.")
        ids = [i for i in range(1, 254) if self.b.bus.ping(i)]
        if not ids:
            print("  Приводов нет на шине.")
            return
        for i in ids:
            s = self.b.servo(i)
            if not self.b.precheck(s):
                return
            s.set_torque_limit(30)
            s.move(sts.MIDDLE, speed=600, accel=20)
            s.torque(True)
        self.b.sleep(2.0)
        for i in ids:
            s = self.b.servo(i)
            print(f"  №{i}: позиция {s.pos()}")
            s.torque(False)
        self.b.add("сб", "Центровка перед сборкой", f"{len(ids)} привод(а) в 2048", "все в середине", True)

    def calibrate(self) -> None:
        print("\nКалибровка ноги: ноль и направления суставов.")
        if not self.require():
            return
        self.torque(False)
        self.b.wait_enter("  Момент выключен. Поставь стенд у края стола — нога смотрит за край (в позе «Г» стопа ниже стола). "
                          "Рукой поставь ногу буквой «Г»: поворот прямо от стенда, бедро горизонтально (по уровню в телефоне), "
                          "голень вертикально вниз.")
        self._sim_table(False)                                    # имитация: нога за краем стола
        sv = self.servos()
        self._write_middle(sv)
        self.cal.sign = {j: self._ask_direction(j, sv[j]) for j in ("coxa", "femur", "knee")}
        self.torque(False)
        self._sim_table(True)
        self.b.wait_enter("  Готово. Верни стенд на место (нога над столом).")
        self.cal.checked = True
        self.cal.save()
        signs = ", ".join(f"{NAMES[j]} {'+' if v > 0 else '−'}" for j, v in self.cal.sign.items())
        self.b.add("к", "Калибровка ноги", f"середина записана; направления: {signs}", "поза «Г» = 2048", True,
                   f"файл {CAL_FILE}")

    def _write_middle(self, sv: dict) -> None:
        """Записать текущую позу («Г») серединой 2048 во все приводы; что не записалось — запомнить смещением."""
        for s in sv.values():
            s.set_middle()
        self.b.sleep(0.2)
        for j, s in sv.items():
            p = s.pos()
            self.cal.offset[j] = middle_offset(p)
            print(f"  {NAMES[j]}: позиция {p}" + ("" if self.cal.offset[j] == 0 else
                                                 f" — середина не записалась, учту программно ({self.cal.offset[j]:+d})"))

    def _ask_direction(self, j: str, s: sts.Servo) -> int:
        """Сдвинуть сустав на +10°, спросить, туда ли он пошёл, вернуть в «Г». Ответ — направление «+» сустава."""
        self.hold_current_pose(limit=40)
        s.move(sts.MIDDLE + self.cal.offset[j] + int(10 / sts.DEG_PER_STEP), speed=300, accel=20)
        self.b.sleep(1.0)
        sign = direction(self.b.ask(f"  {NAMES[j].capitalize()} сдвинулся на 10°. {QUESTIONS[j]} (д/н)", "д"))
        s.move(sts.MIDDLE + self.cal.offset[j], speed=300, accel=20)
        self.b.sleep(1.0)
        return sign

    def _sim_table(self, on: bool) -> None:
        """Только для имитации (--sim): есть ли под стопой стол с весами. На настоящей шине ничего не делает."""
        if hasattr(self.b.bus, "table"):
            self.b.bus.table = on

    def ensure_cal(self) -> bool:
        if not self.cal.checked:
            print("  Сначала калибровка ноги (пункт меню «Нога: калибровка»).")
            return False
        return self.require()

    # ---------- позы ----------
    def poses(self) -> None:
        print("\nПроверка поз: медленно по всем крайним позам из правил движения. Следи, чтобы ничего не задевало.")
        if not self.ensure_cal() or not self.precheck():
            return
        self.hold_current_pose(limit=50)
        worst, skipped = 0.0, 0
        try:
            for qc, qf, qk in CHECK_POSES:
                if GEOM.foot(math.radians(qf), math.radians(qk))[1] < -GEOM.zj - 0.5:
                    print(f"  поза ({qc:+.0f}°, {qf:+.0f}°, {qk:+.0f}°): стопа была бы ниже стола — на стенде пропускаю")
                    skipped += 1
                    continue
                self.goto(qc, qf, qk, seconds=1.2)
                a = self.angles()
                err = max(abs(a["coxa"] - qc), abs(a["femur"] - qf), abs(a["knee"] - qk))
                worst = max(worst, err)
                print(f"  поза ({qc:+.0f}°, {qf:+.0f}°, {qk:+.0f}°): ошибка {err:.1f}°")
            self.goto(*STANCE, seconds=1.0)
        finally:
            self.torque(False)
        hit = self.b.ask("  Что-нибудь задевало стенд или само себя? (д/н)", "н").lower().startswith("д")
        n = len(CHECK_POSES) - skipped
        self.b.add("Н1", f"Позы ноги ({n} из {len(CHECK_POSES)})", f"худшая ошибка {worst:.1f}°", "≤ 2°, ничего не задевает",
                   worst <= 2.0 and not hit, ("задевало; " if hit else "") + f"{skipped} поз ниже стола — проверены в CAD")

    # ---------- стойка на весах ----------
    def stance_scale(self, hold_s: float = 60.0) -> None:
        print("\nСтойка на весах: нога держит 300–400 г — столько приходится на ногу, когда Харви (893 г) стоит на трёх.")
        if not self.ensure_cal():
            return
        self.b.wait_enter("  Стенд прижат к столу (струбцина или тяжёлая книга на основание), под стенд — подставка "
                          "высотой с весы, стопа — на середине весов. Весы включены и обнулены.")
        if not self.precheck():
            return
        self.hold_current_pose()
        r0, h0 = GEOM.stance_target()
        self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=1.2)                     # над весами
        grams = self._press_until_weight(r0, h0)
        print(f"  Держу {hold_s:.0f} с…")
        loads, amps, rise = self._hold_stance(hold_s)
        end, amp = self._stance_readings(grams, amps)
        self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
        self.torque(False)
        load = statistics.mean(loads) if loads else 0.0
        self.stand = dict(grams=grams, end=end, load=load, amps=amp)
        self.b.add("Н2", f"Стойка на весах, {hold_s:.0f} с",
                   f"{grams or 0:.0f} → {end or 0:.0f} г, нагрузка бедра {load:.0f} %, ток {amp:.2f} А",
                   "≥ 300 г, просадка ≤ 10 %, нагрузка бедра ≤ 80 %", stance_ok(grams, end, load),
                   f"стопа ниже стойки на {self.press_mm:.1f} мм; бедро нагрелось на {rise} °C")

    def _press_until_weight(self, r0: float, h0: float) -> float | None:
        """Опускать стопу по 0,5 мм, пока человек не введёт показание весов ≥ 300 г (или до 7,5 мм). Нажим — в press_mm."""
        press, grams = -4.0, None
        while press < 8.0:
            press += 0.5
            self.goto(0.0, *GEOM.ik(r0, h0 - press), seconds=0.3)
            fm = self.servos()["femur"].state()
            ans = self.b.ask(f"  стопа ниже на {press:+.1f} мм, нагрузка бедра {abs(fm.load_pct):.0f} %. "
                             "Enter — сильнее; число — показание весов (г), если уже 300–400 г", self._scale_hint())
            typed = parse_grams(ans)
            if typed is not None:
                grams = typed
                if grams >= 300 or press >= 7.5:
                    break
        self.press_mm = max(press, 0.5)
        return grams

    def _stance_readings(self, grams: float | None, amps: list) -> tuple[float | None, float]:
        """Спросить показания в конце стойки: весы (г) и ток блока питания (А). Без ответа о токе — оценка по приводам."""
        end_default = f"{self.b.bus.scale_grams():.0f}" if hasattr(self.b.bus, "scale_grams") else str(grams or 0)
        end = self.b.ask_float("  Сколько показывают весы сейчас, г?", float(end_default or 0))
        mean_a = statistics.mean(amps) if amps else 0.0
        psu = self.b.ask_float("  Сколько ампер показывает блок питания?", round(mean_a, 2) if amps else 0.1)
        return end, (psu if psu is not None else mean_a)

    def _scale_hint(self) -> str:
        """Ответ по умолчанию в самопроверке на имитации: что показали бы весы, когда уже набрано ≥ 330 г."""
        if hasattr(self.b.bus, "scale_grams") and self.b.auto and self.b.bus.scale_grams() >= 330:
            return f"{self.b.bus.scale_grams():.0f}"
        return ""

    def _hold_stance(self, hold_s: float) -> tuple[list, list, int]:
        """Держать стойку hold_s секунд: нагрузка бедра и ток раз в секунду, нагрев бедра за всё время."""
        t0, loads, amps, temps0 = self.b.clock(), [], [], {j: s.state().temp for j, s in self.servos().items()}
        while self.b.clock() - t0 < hold_s:
            st = {j: s.state() for j, s in self.servos().items()}
            loads.append(abs(st["femur"].load_pct))
            amps.append(sum(self.amps(x) for x in st.values()))
            self.b.sleep(1.0)
        return loads, amps, self.servos()["femur"].state().temp - temps0["femur"]

    # ---------- момент бедра ----------
    def femur_torque(self) -> None:
        print("\nМомент бедра: стопа давит в весы изо всех сил ≤ 1,5 с (паспорт 0,44 Н·м = 4,5 кг·см).")
        if not self.ensure_cal():
            return
        self.b.wait_enter("  Стенд прижат струбциной или книгой ≥ 2 кг — нога поднимет до 1,5 кг. Стопа на весах, весы обнулены. "
                          "Смотри на весы и на блок питания.")
        if not self.precheck():
            return
        self.hold_current_pose()
        r0, h0 = GEOM.stance_target()
        self.goto(0.0, *GEOM.ik(r0, h0 + 1.0), seconds=1.0)
        loads, amps, raw, peak_g, a = self._press_femur(r0, h0)
        self.b.sleep(0.5)
        self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
        self.torque(False)
        grams_default = round(peak_g) if hasattr(self.b.bus, "scale_grams") else 1500
        grams = self.b.ask_float("  Максимум на весах, г", float(grams_default))
        psu = self.b.ask_float("  Максимум тока на блоке питания, А", round(max(amps), 2) if amps else 1.2)
        self._torque_report(grams, psu, a, max(loads) if loads else 0.0, max(raw) if raw else None)

    def _press_femur(self, r0: float, h0: float) -> tuple[list, list, list, float, dict]:
        """Бедро давит стопой в весы 1,5 с (цель — на 15 мм ниже стола), потом сразу снимает усилие.
        Возвращает нагрузку и ток за это время, ток бедра из регистра, пик весов имитации и углы в упоре."""
        sv = self.servos()
        qf, _ = GEOM.ik(r0, h0 - 15.0)
        sv["femur"].move(self.cal.to_pos("femur", clamp("femur", qf)))
        t0, loads, amps, raw, peak_g = self.b.clock(), [], [], [], 0.0
        try:
            while self.b.clock() - t0 < 1.5:
                st = {j: s.state() for j, s in sv.items()}
                if hasattr(self.b.bus, "scale_grams"):
                    peak_g = max(peak_g, self.b.bus.scale_grams())          # имитация: что показали бы весы
                loads.append(abs(st["femur"].load_pct))
                amps.append(sum(self.amps(x) for x in st.values()))
                raw.append(st["femur"].current_a)
        finally:
            a = self.angles()
            sv["femur"].move(self.cal.to_pos("femur", a["femur"] + 3.0), speed=800, accel=20)      # сразу снять усилие
        return loads, amps, raw, peak_g, a

    def _torque_report(self, grams: float | None, psu: float | None, a: dict, load: float, raw_a: float | None) -> None:
        if grams is None:
            self.b.add("Н3", "Момент бедра", "не измерен", "≥ 0,36 Н·м", None)
            return
        arm = GEOM.horizontal(math.radians(a["femur"]), math.radians(a["knee"]))
        nm = torque_nm(grams, arm)
        stall_i = stall_current(psu, self.b.p.idle_a)
        self.b.calibrate_current(raw_a, stall_i)
        self.b.add("Н3", "Момент бедра (упор)", f"{nm:.3f} Н·м ({nm / 0.0981:.1f} кг·см): {grams:.0f} г на плече {arm:.1f} мм",
                   "≥ 0,36 Н·м (паспорт 0,44)", nm >= 0.36,
                   f"нагрузка {load:.0f} %; ток в упоре ≈ {stall_i:.2f} А (паспорт 1,2 А)" if stall_i else f"нагрузка {load:.0f} %")

    # ---------- шаг на месте ----------
    def gait(self, minutes: float = 10.0, period: float = 1.2, lift_mm: float = 12.0) -> None:
        print(f"\nШаг на месте {minutes:.0f} мин: опора {period / 2:.1f} с с нажимом на стол, перенос {period / 2:.1f} с с подъёмом "
              f"на {lift_mm:.0f} мм. Так нагружена нога при ходьбе треногой.")
        if not self.ensure_cal():
            return
        self.b.wait_enter("  Стенд прижат, стопа на столе (весы можно убрать — тогда подставку под стенд тоже), "
                          "термопара приклеена каптоном к приводу бедра (№2).")
        sweep = 10.0 if self.b.ask("  Двигать стопу вперёд-назад ±10°? Только если под стопой гладкая бумага (д/н)",
                                   "н").lower().startswith("д") else 0.0
        if not self.precheck():
            return
        self.hold_current_pose()
        r0, h0 = GEOM.stance_target()
        down, up = GEOM.ik(r0, h0 - self.press_mm), GEOM.ik(r0, h0 + lift_mm)
        self.goto(0.0, *down, seconds=1.0)
        for s in self.servos().values():
            s.move(s.pos(), speed=0, accel=0)                      # дальше — только цели, максимальная скорость
        try:
            rows, peak, aborted = self._walk(minutes * 60, period, sweep, down, up)
        finally:
            try:
                self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
            finally:
                self.torque(False)
            print()
        self._gait_report(minutes, rows, peak, aborted)

    def _walk(self, seconds: float, period: float, sweep: float, down, up) -> tuple[list, dict, str]:
        """Шагать seconds секунд; раз в 2 с — строка журнала. Остановиться по нагреву или напряжению."""
        t0, last_log = self.b.clock(), -10.0
        rows, peak = [], {j: 0 for j in IDS}
        while (el := self.b.clock() - t0) < seconds:
            self.stream(*step_pose((el % period) / period, sweep, down, up))
            if el - last_log >= 2.0:
                last_log = el
                st = self._log_sample(el, rows)
                for j in IDS:
                    peak[j] = max(peak[j], st[j].temp)
                aborted = abort_reason(peak, st["femur"].volt, self.b.p.vmin)
                if aborted:
                    return rows, peak, aborted
            self.b.sleep(0.04)
        return rows, peak, ""

    def _log_sample(self, el: float, rows: list) -> dict:
        """Прочитать все три привода, дописать строку журнала (колонки LOG_HEADER) и показать её на экране."""
        st = {j: s.state() for j, s in self.servos().items()}
        a = {j: self.amps(x) for j, x in st.items()}
        rows.append([round(el, 1)] + [st[j].temp for j in IDS] + [round(a[j], 3) for j in IDS]
                    + [round(abs(st[j].load_pct)) for j in IDS] + [st["femur"].volt])
        print(f"\r  {el / 60:4.1f} мин: темп. {st['coxa'].temp}/{st['femur'].temp}/{st['knee'].temp} °C, "
              f"ток {sum(a.values()):.2f} А, {st['femur'].volt:.1f} В   ", end="", flush=True)
        return st

    def _gait_report(self, minutes: float, rows: list, peak: dict, aborted: str) -> None:
        self.b.log_header, self.b.log_rows = list(LOG_HEADER), rows
        mean_i = statistics.mean(sum(r[4:7]) for r in rows) if rows else 0.0
        case = self.b.ask_float("  Температура корпуса бедра по термопаре в конце, °C («-» — не мерил)", float(peak["femur"] - 3))
        psu = self.b.ask_float("  Сколько в среднем показывал блок питания при шаге, А?", round(mean_i, 2))
        leg_a = psu if psu is not None else mean_i
        self.b.add("Н4", f"Шаг на месте, {minutes:.0f} мин",
                   f"датчики {peak['coxa']}/{peak['femur']}/{peak['knee']} °C, корпус бедра "
                   f"{case if case is not None else '—'} °C, ток ноги {leg_a:.2f} А",
                   "бедро ≤ 60 °C (паспорт: работа до 60 °C, отключение 70 °C)", gait_ok(aborted, peak["femur"], case), aborted)
        self.battery(leg_a)

    def battery(self, leg_walk_a: float) -> None:
        """Ходьба: нога на стенде шагает с нажимом как в треноге — её средний ток × 6 ног.
        Стоя: на шести ногах каждая несёт 893 / 6 ≈ 150 г — ток нагрузки пересчитываем от замера стойки."""
        v = self.b.p.volt
        idle3 = 3 * self.b.p.idle_a
        walk_w = LEGS * leg_walk_a * v / DCDC_EFF + ELECTRONICS_W
        g = self.stand.get("grams") or ROBOT_G / 3
        stand_leg = idle3 + max(0.0, (self.stand.get("amps") or leg_walk_a) - idle3) * (ROBOT_G / LEGS) / g
        stand_w = LEGS * stand_leg * v / DCDC_EFF + ELECTRONICS_W
        h_walk, h_stand = BATTERY_WH / walk_w, BATTERY_WH / stand_w
        self.b.add("Н5", "Батарея 22 Вт·ч (оценка по ноге × 6)",
                   f"ходьба без остановки ≈ {h_walk:.1f} ч ({walk_w:.1f} Вт), стоя ≈ {h_stand:.1f} ч ({stand_w:.1f} Вт)",
                   "оценка в заметке: 1,5–2 ч", h_walk >= 1.0,
                   f"электроника {ELECTRONICS_W} Вт, КПД преобразователя {DCDC_EFF:.0%}")
