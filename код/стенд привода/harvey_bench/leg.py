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
        if hasattr(self.b.bus, "table"):
            self.b.bus.table = False                              # имитация: нога за краем стола
        sv = self.servos()
        for j, s in sv.items():
            s.set_middle()
        self.b.sleep(0.2)
        for j, s in sv.items():
            p = s.pos()
            self.cal.offset[j] = 0 if abs(p - sts.MIDDLE) <= 3 else p - sts.MIDDLE
            print(f"  {NAMES[j]}: позиция {p}" + ("" if self.cal.offset[j] == 0 else
                                                 f" — середина не записалась, учту программно ({self.cal.offset[j]:+d})"))
        self.cal.sign = {j: 1 for j in IDS}
        questions = {"coxa": "Нога повернулась ПРОТИВ часовой стрелки, если смотреть сверху?",
                     "femur": "Бедро поднялось ВВЕРХ?",
                     "knee": "Низ голени ушёл НАРУЖУ — от стенда?"}
        for j in ("coxa", "femur", "knee"):
            s = sv[j]
            self.hold_current_pose(limit=40)
            s.move(sts.MIDDLE + self.cal.offset[j] + int(10 / sts.DEG_PER_STEP), speed=300, accel=20)
            self.b.sleep(1.0)
            ans = self.b.ask(f"  {NAMES[j].capitalize()} сдвинулся на 10°. {questions[j]} (д/н)", "д").lower()
            self.cal.sign[j] = -1 if ans.startswith("н") else 1
            s.move(sts.MIDDLE + self.cal.offset[j], speed=300, accel=20)
            self.b.sleep(1.0)
        self.torque(False)
        if hasattr(self.b.bus, "table"):
            self.b.bus.table = True
        self.b.wait_enter("  Готово. Верни стенд на место (нога над столом).")
        self.cal.checked = True
        self.cal.save()
        signs = ", ".join(f"{NAMES[j]} {'+' if v > 0 else '−'}" for j, v in self.cal.sign.items())
        self.b.add("к", "Калибровка ноги", f"середина записана; направления: {signs}", "поза «Г» = 2048", True,
                   f"файл {CAL_FILE}")

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
        press, grams = -4.0, None
        while press < 8.0:
            press += 0.5
            self.goto(0.0, *GEOM.ik(r0, h0 - press), seconds=0.3)
            fm = self.servos()["femur"].state()
            default = ""
            if hasattr(self.b.bus, "scale_grams") and self.b.auto and self.b.bus.scale_grams() >= 330:
                default = f"{self.b.bus.scale_grams():.0f}"
            ans = self.b.ask(f"  стопа ниже на {press:+.1f} мм, нагрузка бедра {abs(fm.load_pct):.0f} %. "
                             "Enter — сильнее; число — показание весов (г), если уже 300–400 г", default)
            if ans.replace(",", ".").replace(".", "", 1).isdigit():
                grams = float(ans.replace(",", "."))
                if grams >= 300 or press >= 7.5:
                    break
        self.press_mm = max(press, 0.5)
        print(f"  Держу {hold_s:.0f} с…")
        t0, loads, amps, temps0 = self.b.clock(), [], [], {j: s.state().temp for j, s in self.servos().items()}
        while self.b.clock() - t0 < hold_s:
            sts_ = {j: s.state() for j, s in self.servos().items()}
            loads.append(abs(sts_["femur"].load_pct))
            amps.append(sum(self.amps(x) for x in sts_.values()))
            self.b.sleep(1.0)
        temps1 = {j: s.state().temp for j, s in self.servos().items()}
        end_default = f"{self.b.bus.scale_grams():.0f}" if hasattr(self.b.bus, "scale_grams") else str(grams or 0)
        end = self.b.ask_float("  Сколько показывают весы сейчас, г?", float(end_default or 0))
        psu = self.b.ask_float("  Сколько ампер показывает блок питания?", round(statistics.mean(amps), 2) if amps else 0.1)
        self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
        self.torque(False)
        load = statistics.mean(loads) if loads else 0.0
        amp = psu if psu is not None else (statistics.mean(amps) if amps else 0.0)
        self.stand = dict(grams=grams, end=end, load=load, amps=amp)
        ok = bool(grams and grams >= 300 and end is not None and end >= 0.9 * grams and load <= 80)
        rise = temps1["femur"] - temps0["femur"]
        self.b.add("Н2", f"Стойка на весах, {hold_s:.0f} с",
                   f"{grams or 0:.0f} → {end or 0:.0f} г, нагрузка бедра {load:.0f} %, ток {amp:.2f} А",
                   "≥ 300 г, просадка ≤ 10 %, нагрузка бедра ≤ 80 %", ok,
                   f"стопа ниже стойки на {self.press_mm:.1f} мм; бедро нагрелось на {rise} °C")

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
        sv = self.servos()
        qf, qk = GEOM.ik(r0, h0 - 15.0)
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
        grams_default = round(peak_g) if hasattr(self.b.bus, "scale_grams") else 1500
        self.b.sleep(0.5)
        self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
        self.torque(False)
        grams = self.b.ask_float("  Максимум на весах, г", float(grams_default))
        psu = self.b.ask_float("  Максимум тока на блоке питания, А", round(max(amps), 2) if amps else 1.2)
        arm = GEOM.horizontal(math.radians(a["femur"]), math.radians(a["knee"]))
        load = max(loads) if loads else 0.0
        if grams is None:
            self.b.add("Н3", "Момент бедра", "не измерен", "≥ 0,36 Н·м", None)
            return
        nm = grams / 1000 * 9.81 * arm / 1000
        stall_i = (psu - 2 * self.b.p.idle_a) if psu else None
        self.b.calibrate_current(max(raw) if raw else None, stall_i)
        self.b.add("Н3", "Момент бедра (упор)", f"{nm:.3f} Н·м ({nm / 0.0981:.1f} кг·см): {grams:.0f} г на плече {arm:.1f} мм",
                   "≥ 0,36 Н·м (паспорт 0,44)", nm >= 0.36,
                   f"нагрузка {load:.0f} %; ток в упоре ≈ {stall_i:.2f} А (паспорт 1,2 А)" if stall_i else f"нагрузка {load:.0f} %")

    # ---------- шаг на месте ----------
    def gait(self, minutes: float = 10.0, period: float = 1.2, lift_mm: float = 12.0) -> None:
        print(f"\nШаг на месте {minutes:.0f} мин: опора {period / 2:.1f} с с нажимом на стол, перенос {period / 2:.1f} с с подъёмом "
              f"на {lift_mm:.0f} мм. Так нагружена нога при ходьбе треногой.")
        if not self.ensure_cal():
            return
        sweep = 0.0
        self.b.wait_enter("  Стенд прижат, стопа на столе (весы можно убрать — тогда подставку под стенд тоже), "
                          "термопара приклеена каптоном к приводу бедра (№2).")
        if self.b.ask("  Двигать стопу вперёд-назад ±10°? Только если под стопой гладкая бумага (д/н)", "н").lower().startswith("д"):
            sweep = 10.0
        if not self.precheck():
            return
        self.hold_current_pose()
        r0, h0 = GEOM.stance_target()
        down = GEOM.ik(r0, h0 - self.press_mm)
        up = GEOM.ik(r0, h0 + lift_mm)
        self.goto(0.0, *down, seconds=1.0)
        for s in self.servos().values():
            s.move(s.pos(), speed=0, accel=0)                      # дальше — только цели, максимальная скорость
        sv = self.servos()
        t0, last_log, aborted = self.b.clock(), -10.0, ""
        rows, peak = [], {j: 0 for j in IDS}
        try:
            while True:
                el = self.b.clock() - t0
                if el >= minutes * 60:
                    break
                ph = (el % period) / period
                if ph < 0.5:                                       # опора: стопа на столе с нажимом
                    qc = sweep * (1 - 4 * ph)                       # +sweep → −sweep
                    qf, qk = down
                else:                                              # перенос: подъём и обратно
                    k = math.sin(math.pi * (ph - 0.5) * 2)
                    qc = -sweep + 2 * sweep * (ph - 0.5) * 2
                    qf = down[0] + (up[0] - down[0]) * k
                    qk = down[1] + (up[1] - down[1]) * k
                self.stream(qc, qf, qk)
                if el - last_log >= 2.0:
                    last_log = el
                    st = {j: s.state() for j, s in sv.items()}
                    a = {j: self.amps(x) for j, x in st.items()}
                    row = [round(el, 1)] + [st[j].temp for j in IDS] + [round(a[j], 3) for j in IDS] + \
                          [round(abs(st[j].load_pct)) for j in IDS] + [st["femur"].volt]
                    rows.append(row)
                    for j in IDS:
                        peak[j] = max(peak[j], st[j].temp)
                    print(f"\r  {el / 60:4.1f} мин: темп. {st['coxa'].temp}/{st['femur'].temp}/{st['knee'].temp} °C, "
                          f"ток {sum(a.values()):.2f} А, {st['femur'].volt:.1f} В   ", end="", flush=True)
                    if max(peak.values()) >= 65:
                        aborted = "остановлен: датчик привода 65 °C"
                        break
                    if st["femur"].volt < self.b.p.vmin:
                        aborted = f"остановлен: напряжение {st['femur'].volt:.1f} В"
                        break
                self.b.sleep(0.04)
        finally:
            try:
                self.goto(0.0, *GEOM.ik(r0, h0 + 4.0), seconds=0.8)
            finally:
                self.torque(False)
            print()
        self.b.log_header = ["Время, с", "Темп. поворота, °C", "Темп. бедра, °C", "Темп. колена, °C",
                             "Ток поворота, А", "Ток бедра, А", "Ток колена, А",
                             "Нагрузка поворота, %", "Нагрузка бедра, %", "Нагрузка колена, %", "Напряжение, В"]
        self.b.log_rows = rows
        mean_i = statistics.mean(sum(r[4:7]) for r in rows) if rows else 0.0
        case = self.b.ask_float("  Температура корпуса бедра по термопаре в конце, °C («-» — не мерил)", float(peak["femur"] - 3))
        psu = self.b.ask_float("  Сколько в среднем показывал блок питания при шаге, А?", round(mean_i, 2))
        leg_a = psu if psu is not None else mean_i
        ok = not aborted and peak["femur"] <= 60 and (case is None or case <= 60)
        self.b.add("Н4", f"Шаг на месте, {minutes:.0f} мин",
                   f"датчики {peak['coxa']}/{peak['femur']}/{peak['knee']} °C, корпус бедра "
                   f"{case if case is not None else '—'} °C, ток ноги {leg_a:.2f} А",
                   "бедро ≤ 60 °C (паспорт: работа до 60 °C, отключение 70 °C)", ok, aborted)
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
