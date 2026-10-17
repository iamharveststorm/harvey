"""Харви, этап 1: стенд привода. «Компакт» — STS3215-C018 (12 В), «Компакт мини» — STS3032-C036 (6 В) и нога целиком.

Запуск:
    python -m harvey_bench.bench --port COM5                    # «Компакт», STS3215 (номер порта — в диспетчере устройств)
    python -m harvey_bench.bench --servo sts3032 --port COM5    # «Компакт мини»: приводы и нога на стенде
    python -m harvey_bench.bench --sim                          # без железа: имитация (можно с --servo sts3032)
    python -m harvey_bench.bench --sim --auto                   # имитация с ответами по умолчанию (самопроверка)

Безопасность: перед каждым замером с включённым моментом проверяется напряжение (STS3215 — 10–13 В,
STS3032 — 5,4–6,6 В) и температура (< 60 °C); упор — не дольше 2 с; при Ctrl+C или ошибке момент отключается.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from . import sts

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CALIB_FILE = Path("bench_calibration.json")
STEP_DEG = sts.DEG_PER_STEP


class Bench:
    def __init__(self, bus, auto: bool = False, speedup: float = 1.0, clock=time.monotonic,
                 profile: sts.Profile = sts.PROFILES["sts3215"]):
        self.bus, self.auto, self.speedup, self.clock, self.p = bus, auto, speedup, clock, profile
        self.results: list[dict] = []
        self.log_rows: list[list] = []
        self.log_header = ["Время, с", "Температура, °C", "Ток, А", "Напряжение, В", "Позиция"]
        self.lsb = sts.CURRENT_LSB_A
        self.current_ok = profile.current_sensor          # есть ли ток в регистрах привода
        if CALIB_FILE.exists():
            try:
                d = json.loads(CALIB_FILE.read_text(encoding="utf-8"))
                legacy = d.get("current_lsb_a", self.lsb) if profile.key == "sts3215" else self.lsb
                self.lsb = float(d.get(profile.key, legacy))
                self.current_ok = self.current_ok or bool(d.get(profile.key + "_sensor"))
            except Exception:
                pass

    # ---------- общение с человеком ----------
    def ask(self, text: str, default: str = "") -> str:
        if self.auto:
            print(f"{text} [{default}] → {default}")
            return default
        ans = input(f"{text} [{default}]: ").strip()
        return ans or default

    def ask_float(self, text: str, default: float) -> float | None:
        while True:
            ans = self.ask(text, str(default)).replace(",", ".")
            if ans.lower() in ("-", "нет", "skip"):
                return None
            try:
                return float(ans)
            except ValueError:
                print("Нужно число (или «-», чтобы пропустить).")

    def wait_enter(self, text: str) -> None:
        self.ask(text + " Нажми Enter, когда готово", "")

    def sleep(self, sec: float) -> None:
        time.sleep(sec / self.speedup)

    def add(self, n: str, name: str, measured: str, norm: str, ok: bool | None, note: str = "") -> None:
        verdict = "—" if ok is None else ("ОК" if ok else "НЕ ОК")
        self.results.append(dict(n=n, test=name, measured=measured, norm=norm, verdict=verdict, note=note))
        print(f"  → {name}: {measured} (норма {norm}) — {verdict}")

    # ---------- проверки безопасности ----------
    def servo(self, sid: int) -> sts.Servo:
        return sts.Servo(self.bus, sid, self.lsb)

    def amps(self, st: sts.State) -> float:
        """Ток привода: из регистра, а если датчика нет (STS3032) — оценка по нагрузке: покой + нагрузка × ток упора."""
        if self.current_ok:
            return st.current_a
        return self.p.idle_a + abs(st.load_pct) / 100.0 * self.p.stall_a

    def calibrate_current(self, raw_a: float | None, real_a: float | None) -> None:
        """Сверить ток из регистра с блоком питания и запомнить масштаб (или что датчика нет)."""
        if not real_a or real_a <= 0.3:
            return
        if raw_a and raw_a > 0.05:
            self.lsb *= real_a / raw_a
            self.current_ok = True
            print(f"  Датчик тока отвечает: масштаб уточнён — {self.lsb * 1000:.2f} мА на единицу.")
        else:
            print("  В регистре тока нули — датчика тока нет (как в даташите). Ток оцениваю по нагрузке привода.")
        d = {}
        if CALIB_FILE.exists():
            try:
                d = json.loads(CALIB_FILE.read_text(encoding="utf-8"))
            except Exception:
                d = {}
        d[self.p.key] = self.lsb
        d[self.p.key + "_sensor"] = self.current_ok
        if self.p.key == "sts3215":
            d["current_lsb_a"] = self.lsb
        CALIB_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def precheck(self, s: sts.Servo, vmin: float | None = None, vmax: float | None = None) -> bool:
        vmin = self.p.vmin if vmin is None else vmin
        vmax = self.p.vmax if vmax is None else vmax
        st = s.state()
        print(f"  Напряжение {st.volt:.1f} В, температура {st.temp} °C, позиция {st.pos}")
        if not vmin <= st.volt <= vmax:
            print(f"  СТОП: напряжение {st.volt:.1f} В вне {vmin}–{vmax} В. Проверь блок питания.")
            return False
        if st.temp >= 60:
            print("  СТОП: привод горячий (≥ 60 °C). Дай остыть.")
            return False
        return True

    # ---------- замер 1: связь и номера ----------
    def scan(self) -> list[int]:
        print("Ищу приводы на шине (1–253)…")
        found = [i for i in range(1, 254) if self.bus.ping(i)]
        for i in found:
            try:
                model = self.servo(i).model()
            except sts.BusError:
                model = -1
            short = self.p.title.split()[0]
            if self.p.model is None:
                name = f"{short}? модель {model} — номер запишется в отчёт"
            elif model == self.p.model:
                name = short
            else:
                name = f"модель {model} — НЕ {short}! Проверь привод и режим стенда"
            print(f"  привод №{i}: {name}")
        if not found:
            if self.p.key == "sts3215":
                print("  Никого. Проверь питание 12 В, кабель и что красный провод от адаптера отключён (см. README).")
            else:
                print("  Никого. Проверь: 6,0 В на клеммах адаптера, переходник 1,25 → 5264 в разъёме TTL (3 контакта), USB.")
        models = sorted({self.servo(i).model() for i in found}) if found else []
        self.add("1", "Связь: найдено приводов", str(len(found)), "все подключённые", bool(found),
                 "номера: " + ", ".join(map(str, found)) + ("; модель в регистре: " + ", ".join(map(str, models)) if models else ""))
        return found

    def assign_id(self) -> None:
        print("Назначение номера. На шине должен быть ОДИН привод (у новых у всех номер 1).")
        found = [i for i in range(1, 254) if self.bus.ping(i)]
        if len(found) != 1:
            print(f"  Найдено приводов: {len(found)}. Оставь подключённым один и повтори.")
            return
        new = int(self.ask_float(f"  Сейчас номер {found[0]}. Новый номер (1–253)", 1) or found[0])
        s = self.servo(found[0])
        s.torque(False)
        s.set_id(new)
        ok = self.bus.ping(new)
        print("  Готово, привод отвечает под новым номером." if ok else "  Привод не отвечает под новым номером!")

    # ---------- замер 2: ток покоя и упора ----------
    def current_test(self, sid: int) -> None:
        s = self.servo(sid)
        v = str(self.p.volt).replace(".", ",")
        print(f"\nЗамер 2. Ток покоя{' и в упоре' if self.p.key == 'sts3215' else ''}. Блок питания: {v} В, предел тока 3 А.")
        if not self.precheck(s):
            return
        start = s.pos()
        s.set_torque_limit(100)
        s.move(start)
        s.torque(True)
        self.sleep(1.0)
        idle = statistics.median(self.amps(s.state()) for _ in range(20))
        norm = f"≤ {str(self.p.idle_max_a).replace('.', ',')} А"
        if not self.current_ok:
            psu = self.ask_float("  Датчика тока у привода нет. Сколько ампер показывает блок питания (на шине один привод)?",
                                 round(idle, 3))
            idle = psu if psu is not None else idle
        self.add("2а", "Ток покоя (удержание без нагрузки)", f"{idle:.3f} А", norm, idle <= self.p.idle_max_a,
                 f"паспорт {self.p.idle_a * 1000:.0f} мА")
        if self.p.key != "sts3215":
            s.torque(False)
            print("  Ток в упоре у мини меряем на собранной ноге: пункт «Нога: момент бедра».")
            return
        self.wait_enter("  Упор: поставь рычаг так, чтобы при повороте ПО ЧАСОВОЙ он упёрся в неподвижную преграду.")
        if isinstance(getattr(self.bus, "servos", None), dict):
            self.bus.servos[sid].block_at = start + 120           # имитация преграды
        cur = self.push(s, start + 400, 1.5)
        s.move(start, speed=800, accel=20)
        self.sleep(1.0)
        s.torque(False)
        if isinstance(getattr(self.bus, "servos", None), dict):
            self.bus.servos[sid].block_at = None
        psu = self.ask_float("  Сколько ампер показывал блок питания во время упора? («-» — не смотрел)", round(cur, 2))
        if psu and cur > 0.5:
            self.lsb *= psu / cur
            CALIB_FILE.write_text(json.dumps({"current_lsb_a": self.lsb}, ensure_ascii=False), encoding="utf-8")
            note = f"масштаб тока уточнён по блоку питания: {self.lsb * 1000:.2f} мА на единицу"
            cur = psu
        else:
            note = "масштаб тока по умолчанию"
        self.add("2б", "Ток в упоре", f"{cur:.2f} А", "2,4–3,0 А", 2.4 <= cur <= 3.0, note)

    def push(self, s: sts.Servo, goal: int, seconds: float) -> float:
        """Давит в упор не дольше seconds (максимум 2 с). Возвращает медианный ток последней секунды."""
        seconds = min(seconds, 2.0)
        s.move(goal)
        t0, samples = self.clock(), []
        try:
            while self.clock() - t0 < seconds:
                st = s.state()
                if self.clock() - t0 > seconds - 1.0:
                    samples.append(st.current_a)
        finally:
            s.move(s.pos(), speed=800, accel=20)          # сразу снять усилие
        return statistics.median(samples) if samples else 0.0

    # ---------- замер 3: момент ----------
    def torque_test(self, sid: int) -> None:
        if self.p.key != "sts3215":
            print("\nМомент STS3032 меряем на собранной ноге: пункт «Нога: момент бедра».")
            return
        s = self.servo(sid)
        print("\nЗамер 3. Момент через рычаг 100 мм и весы.")
        for v_nom, norm in ((12.0, 2.5), (10.2, 2.0)):
            if self.ask(f"  Мерить при {str(v_nom).replace('.', ',')} В? (д/н)", "д" if v_nom == 12.0 else "н").lower().startswith("н"):
                continue
            self.wait_enter(f"  Выставь на блоке {v_nom} В. Рычаг — отверстием 100 мм на весы (через подставку), весы обнули кнопкой тары.")
            if not self.precheck(s, vmin=v_nom - 0.6, vmax=v_nom + 0.6):
                continue
            start = s.pos()
            s.set_torque_limit(100)
            s.move(start)
            s.torque(True)
            if isinstance(getattr(self.bus, "servos", None), dict):
                self.bus.servos[sid].block_at = start + 30
                self.bus.servos[sid].volt = v_nom
            cur = self.push(s, start + 300, 2.0)
            s.torque(False)
            if isinstance(getattr(self.bus, "servos", None), dict):
                self.bus.servos[sid].block_at = None
            kg = self.ask_float("  Максимум на весах, кг", round(cur / 2.7 * 3.0 * v_nom / 12.0, 2))
            if kg is None:
                continue
            self.add("3", f"Момент при {v_nom} В", f"{kg:.2f} кг ({kg * 10:.1f} кг·см)", f"≥ {str(norm).replace('.', ',')} кг", kg >= norm,
                     f"ток в упоре {cur:.2f} А")

    # ---------- замер 4: скорость ----------
    def speed_test(self, sid: int) -> None:
        s = self.servo(sid)
        print("\nЗамер 4. Скорость: поворот на 90° без нагрузки (ничего не мешает).")
        self.wait_enter("  Привод лежит свободно, на качалке ничего нет (или рычаг свободен).")
        if not self.precheck(s):
            return
        start = s.pos()
        target = start + 1024 if start < 2048 else start - 1024
        s.set_torque_limit(100)
        s.move(start)
        s.torque(True)
        self.sleep(0.5)
        times = []
        for a, b in ((start, target), (target, start)):
            t0 = self.clock()
            s.move(b)
            while self.clock() - t0 < 2.0:
                if abs(s.pos() - b) <= 20:
                    break
            times.append(self.clock() - t0)
            self.sleep(0.4)
        s.torque(False)
        t90 = max(times)
        lim = round(self.p.t90_spec * 1.2, 2)
        self.add("4", "Поворот на 90°", f"{t90:.3f} с", f"≤ {str(lim).replace('.', ',')} с", t90 <= lim,
                 f"туда {times[0]:.3f} с, обратно {times[1]:.3f} с; паспорт {str(self.p.t90_spec).replace('.', ',')} с "
                 "(с опросом по USB время чуть больше настоящего)")

    # ---------- замер 5: люфт ----------
    def backlash_test(self, sid: int) -> None:
        s = self.servo(sid)
        print("\nЗамер 5. Люфт. Указка закреплена на рычаге (у мини — скотчем на бедре), луч — на стену.")
        dist = self.ask_float("  Расстояние от оси привода до стены, мм", 1000.0) or 1000.0
        if not self.precheck(s):
            return
        start = s.pos()
        s.set_torque_limit(100)
        s.move(start)
        s.torque(True)
        self.wait_enter("  Привод держит позицию. Отметь на стене крайние точки пятна, слегка покачав рычаг в обе стороны.")
        enc = [s.pos() for _ in range(30)]
        s.torque(False)
        span = self.ask_float("  Размах пятна на стене, мм", 8.0)
        enc_span = (max(enc) - min(enc)) * STEP_DEG
        if span is None:
            self.add("5", "Люфт", "не измерен", "≤ 1° (≤ 17 мм в 1 м)", None)
            return
        deg = span / dist * 57.2958
        self.add("5", "Люфт", f"{deg:.2f}° ({span:.0f} мм на {dist:.0f} мм)", "≤ 1°, хорошо ≤ 0,5°", deg <= 1.0,
                 f"датчик привода за это время: {enc_span:.2f}° (он стоит на выходном валу и люфт шестерён не видит)")

    # ---------- замер 6: точность возврата ----------
    def repeat_test(self, sid: int) -> None:
        s = self.servo(sid)
        print("\nЗамер 6. Точность возврата: 10 раз на 45° и обратно.")
        if not self.precheck(s):
            return
        start = s.pos()
        far = start + 512 if start < 2048 else start - 512
        s.set_torque_limit(100)
        s.move(start, speed=1500, accel=50)
        s.torque(True)
        self.sleep(0.6)
        back = []
        for _ in range(10):
            s.move(far, speed=1500, accel=50)
            self.sleep(0.8)
            s.move(start, speed=1500, accel=50)
            self.sleep(0.8)
            back.append(s.pos())
        s.torque(False)
        spread = (max(back) - min(back)) * STEP_DEG
        laser = self.ask_float("  Разброс пятна указки на стене при возвратах, мм («-» — не мерил)", 3.0)
        note = "" if laser is None else f"по указке: {laser:.0f} мм"
        self.add("6", "Точность возврата (по датчику)", f"{spread:.2f}°", "≤ 0,3°", spread <= 0.3, note)

    # ---------- замер 7: нагрев ----------
    def heat_test(self, sid: int, minutes: float = 10.0) -> None:
        if self.p.key != "sts3215":
            print("\nНагрев STS3032 меряем на собранной ноге: пункт «Нога: шаг на месте 10 минут».")
            return
        s = self.servo(sid)
        print(f"\nЗамер 7. Нагрев: груз 1 кг на рычаге 100 мм (10 кг·см = номинал), {minutes:.0f} мин.")
        self.wait_enter("  Рычаг горизонтально, груз подвешен в отверстие 100 мм, термопара приклеена к корпусу.")
        if not self.precheck(s):
            return
        if isinstance(getattr(self.bus, "servos", None), dict):
            self.bus.servos[sid].ext_load_frac = 0.33
        start = s.pos()
        s.set_torque_limit(100)
        s.move(start)
        s.torque(True)
        t0, peak_t, over_since, currents, aborted = self.clock(), 0, None, [], ""
        try:
            while self.clock() - t0 < minutes * 60:
                st = s.state()
                el = self.clock() - t0
                self.log_rows.append([round(el, 1), st.temp, round(st.current_a, 3), st.volt, st.pos])
                currents.append(st.current_a)
                peak_t = max(peak_t, st.temp)
                print(f"\r  {el / 60:4.1f} мин: {st.temp} °C, {st.current_a:.2f} А, {st.volt:.1f} В   ", end="", flush=True)
                if st.temp >= 70:
                    aborted = "остановлен: 70 °C"
                    break
                if st.current_a > 2.2:
                    over_since = over_since or self.clock()
                    if self.clock() - over_since > 5:
                        aborted = "остановлен: ток > 2,2 А дольше 5 с"
                        break
                else:
                    over_since = None
                self.sleep(2.0)
        finally:
            s.torque(False)
            if isinstance(getattr(self.bus, "servos", None), dict):
                self.bus.servos[sid].ext_load_frac = 0.0
            print()
        mean_i = statistics.mean(currents) if currents else 0.0
        case_t = self.ask_float("  Температура корпуса по термопаре в конце, °C («-» — не мерил)", float(peak_t - 3))
        ok = peak_t <= 70 and mean_i <= 1.1 and (case_t is None or case_t <= 65) and not aborted
        meas = f"датчик {peak_t} °C, корпус {case_t if case_t is not None else '—'} °C, ток {mean_i:.2f} А"
        self.add("7", f"Нагрев на номинале, {minutes:.0f} мин", meas, "корпус ≤ 65 °C, датчик ≤ 70 °C, ток ≤ 1,1 А", ok, aborted)

    # ---------- отчёт ----------
    def save(self) -> Path:
        from . import report

        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = Path(f"bench_results_{stamp}.xlsx")
        report.write(path, self.results, self.log_rows, title=f"Харви — стенд {self.p.title}", log_header=self.log_header)
        Path(f"bench_results_{stamp}.json").write_text(
            json.dumps(dict(servo=self.p.key, results=self.results, log_header=self.log_header, log=self.log_rows),
                       ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Отчёт сохранён: {path.resolve()}")
        return path


MENU = """
Стенд привода Харви (STS3215, «Компакт») — что делаем?
  1  Найти приводы на шине
  2  Назначить номер приводу (на шине — один привод)
  3  Замер 2: ток покоя и в упоре
  4  Замер 3: момент (весы)
  5  Замер 4: скорость
  6  Замер 5: люфт (указка)
  7  Замер 6: точность возврата
  8  Замер 7: нагрев 10 минут
  9  Все замеры 2–7 подряд
  0  Сохранить отчёт и выйти
"""

MENU_MINI = """
Стенд «Компакт мини» (STS3032, 6 В) — что делаем?
  1  Найти приводы на шине
  2  Назначить номер приводу (на шине — один привод): нога — 1 поворот, 2 бедро, 3 колено
  3  Центровка перед сборкой: все приводы в середину
  4  Размеры привода штангенциркулем — в отчёт
  5  Один привод: ток покоя
  6  Один привод: скорость
  7  Один привод: люфт (указка)
  8  Один привод: точность возврата
  9  Нога: калибровка нуля и направлений
 10  Нога: проверка поз
 11  Нога: стойка на весах (300–400 г, 60 с)
 12  Нога: момент бедра (упор в весы)
 13  Нога: шаг на месте 10 минут — нагрев, ток, батарея
 14  Всё с ноги подряд (10–13)
  0  Сохранить отчёт и выйти
"""


def measure_servo(bench: Bench) -> None:
    """Размеры, которых нет на чертеже Feetech, — по ним поправим CAD перед печатью."""
    print("\nРазмеры привода (штангенциркуль, каждый — 3 раза, вводи среднее, мм). «-» — пропустить.")
    items = [("horn_top", "от торца корпуса до плоскости качалки (вдоль вала)", 4.8),
             ("shaft_from_end", "от оси вала до ближнего узкого торца корпуса", 5.7),
             ("body_L", "длина корпуса поперёк вала (без ушек)", 23.0),
             ("body_D", "корпус вдоль вала, между торцами (без качалок)", 27.5),
             ("total_D", "вдоль вала вместе с обеими качалками", 37.2)]
    got = {}
    for key, text, cad in items:
        v = bench.ask_float(f"  {key}: {text} (в CAD {str(cad).replace('.', ',')})", cad)
        if v is None:
            continue
        got[key] = v
        bench.add("р", f"Размер {key}", f"{v:.2f} мм", f"CAD {cad} мм, допуск ±0,3", abs(v - cad) <= 0.3,
                  "" if abs(v - cad) <= 0.3 else "поправить CAD перед печатью")
    if got:
        Path("servo_measurements.json").write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  Записано в servo_measurements.json — пришли файл или отчёт, поправлю CAD.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Стенд привода Харви: STS3215 («Компакт») или STS3032 и нога («Компакт мини»)")
    ap.add_argument("--port", help="последовательный порт адаптера, например COM5 или /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=1_000_000)
    ap.add_argument("--servo", choices=sorted(sts.PROFILES), default="sts3215", help="какой привод на стенде")
    ap.add_argument("--sim", action="store_true", help="имитация без железа")
    ap.add_argument("--auto", action="store_true", help="ответы по умолчанию (для самопроверки)")
    ap.add_argument("--heat-min", type=float, default=10.0, help="длительность нагрева / шага на месте, мин")
    args = ap.parse_args(argv)
    profile = sts.PROFILES[args.servo]
    mini = profile.key == "sts3032"

    if args.sim:
        from .fake import FakeBus, FakeLegBus
        from .leg import GEOM

        speed = 20.0 if args.auto else 1.0
        bus = FakeLegBus(GEOM, speedup=speed) if mini else FakeBus(ids=(1,), speedup=speed, profile=profile)
        bench = Bench(bus, auto=args.auto, speedup=bus.speedup, clock=bus.clock, profile=profile)
    else:
        if not args.port:
            from serial.tools import list_ports

            ports = [p.device for p in list_ports.comports()]
            print("Укажи порт: --port <имя>. Найдены порты:", ", ".join(ports) or "нет")
            return 2
        bus = sts.SerialBus(args.port, args.baud)
        bench = Bench(bus, profile=profile)

    sid = 1
    try:
        if mini:
            from .leg import Leg

            leg = Leg(bench)
            choices = ["1", "4", "5", "6", "8", "9", "14", "0"] if args.auto else None
            while True:
                print(MENU_MINI)
                ch = choices.pop(0) if choices else input("Выбор: ").strip()
                if ch == "1":
                    found = bench.scan()
                    if found:
                        sid = found[0]
                elif ch == "2":
                    bench.assign_id()
                elif ch == "3":
                    leg.center_all()
                elif ch == "4":
                    measure_servo(bench)
                elif ch in ("5", "6", "7", "8"):
                    sid = int(bench.ask_float("Номер привода", sid) or sid)
                    {"5": bench.current_test, "6": bench.speed_test, "7": bench.backlash_test, "8": bench.repeat_test}[ch](sid)
                elif ch == "9":
                    leg.calibrate()
                elif ch == "10":
                    leg.poses()
                elif ch == "11":
                    leg.stance_scale()
                elif ch == "12":
                    leg.femur_torque()
                elif ch == "13":
                    leg.gait(args.heat_min)
                elif ch == "14":
                    leg.poses()
                    leg.stance_scale()
                    leg.femur_torque()
                    leg.gait(args.heat_min)
                elif ch == "0":
                    bench.save()
                    return 0
        choices = ["1", "9", "0"] if args.auto else None
        while True:
            print(MENU)
            ch = choices.pop(0) if choices else input("Выбор: ").strip()
            if ch == "1":
                found = bench.scan()
                if found:
                    sid = found[0]
            elif ch == "2":
                bench.assign_id()
            elif ch in "345678" and len(ch) == 1:
                sid = int(bench.ask_float("Номер привода", sid) or sid)
                {"3": bench.current_test, "4": bench.torque_test, "5": bench.speed_test, "6": bench.backlash_test,
                 "7": bench.repeat_test}.get(ch, lambda i: bench.heat_test(i, args.heat_min))(sid)
            elif ch == "9":
                for fn in (bench.current_test, bench.torque_test, bench.speed_test, bench.backlash_test, bench.repeat_test):
                    fn(sid)
                bench.heat_test(sid, args.heat_min)
            elif ch == "0":
                bench.save()
                return 0
    except KeyboardInterrupt:
        print("\nПрервано.")
        return 1
    finally:
        try:
            bus.write(sts.BROADCAST, sts.TORQUE_ENABLE, 0)     # на всякий случай: отпустить все приводы
        except Exception:
            pass
        bus.close()


if __name__ == "__main__":
    sys.exit(main())
