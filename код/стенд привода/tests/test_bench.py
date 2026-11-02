"""Замеры одного привода на имитации: связь и номер, ток, момент, скорость, люфт, точность, нагрев, размеры, калибровка тока."""
import json
from pathlib import Path

import pytest

from harvey_bench import fake, sts
from harvey_bench.bench import CALIB_FILE, STEP_DEG, Bench, measure_servo
from harvey_bench.fake import FakeBus, FakeServo
from helpers import answer, result

SPEEDUP = 50.0


def make(key: str, ids=(1,)) -> Bench:
    bus = FakeBus(ids=ids, speedup=SPEEDUP, profile=sts.PROFILES[key])
    return Bench(bus, auto=True, speedup=bus.speedup, clock=bus.clock, profile=sts.PROFILES[key])


@pytest.fixture
def big():
    return make("sts3215")


@pytest.fixture
def mini():
    return make("sts3032")


def released(b: Bench) -> bool:
    return all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in b.bus.servos.values())


# ---------- калибровка тока в файле ----------
def test_saved_current_scale_is_loaded_per_servo_type():
    CALIB_FILE.write_text(json.dumps({"sts3215": 0.004, "sts3032": 0.009, "sts3032_sensor": True}), encoding="utf-8")
    assert make("sts3215").lsb == 0.004
    m = make("sts3032")
    assert m.lsb == 0.009 and m.current_ok is True


def test_old_calibration_key_still_works_for_sts3215():
    CALIB_FILE.write_text(json.dumps({"current_lsb_a": 0.005}), encoding="utf-8")
    assert make("sts3215").lsb == 0.005
    assert make("sts3032").lsb == sts.CURRENT_LSB_A                 # старый ключ — только про STS3215


def test_broken_calibration_file_keeps_defaults():
    CALIB_FILE.write_text("{", encoding="utf-8")
    b = make("sts3032")
    assert b.lsb == sts.CURRENT_LSB_A and b.current_ok is False


def test_calibrate_current_rescales_from_power_supply(big):
    big.calibrate_current(raw_a=2.0, real_a=2.5)
    assert big.lsb == pytest.approx(sts.CURRENT_LSB_A * 1.25) and big.current_ok
    d = json.loads(CALIB_FILE.read_text(encoding="utf-8"))
    assert d["sts3215"] == d["current_lsb_a"] == big.lsb and d["sts3215_sensor"] is True


def test_calibrate_current_notes_missing_sensor(mini):
    CALIB_FILE.write_text(json.dumps({"sts3215": 0.004}), encoding="utf-8")
    mini.calibrate_current(raw_a=0.0, real_a=1.2)
    d = json.loads(CALIB_FILE.read_text(encoding="utf-8"))
    assert d == {"sts3215": 0.004, "sts3032": sts.CURRENT_LSB_A, "sts3032_sensor": False}
    assert "current_lsb_a" not in d and mini.lsb == sts.CURRENT_LSB_A


@pytest.mark.parametrize("real", [None, 0.0, 0.3])
def test_calibrate_current_ignores_small_or_missing_reading(big, real):
    big.calibrate_current(raw_a=2.0, real_a=real)
    assert not CALIB_FILE.exists() and big.lsb == sts.CURRENT_LSB_A


def test_amps_from_register_or_from_load(big, mini):
    st = sts.State(pos=0, speed=0, load_pct=-50.0, volt=6.0, temp=30, current_a=0.7)
    assert big.amps(st) == 0.7
    assert mini.amps(st) == pytest.approx(0.02 + 0.5 * 1.2)         # покой + половина тока упора


# ---------- безопасность ----------
@pytest.mark.parametrize("volt, temp, ok", [(12.0, 30, True), (10.0, 59, True), (13.0, 30, True),
                                            (9.9, 30, False), (13.1, 30, False), (12.0, 60, False)])
def test_precheck_voltage_window_and_temperature(big, volt, temp, ok):
    s = big.bus.servos[1]
    s.volt, s.temp = volt, temp + 0.5                    # имитация остывает при чтении: +0,5 °C, чтобы прочиталось temp
    assert big.precheck(big.servo(1)) is ok


# ---------- замер 1: связь и номер ----------
def test_scan_finds_sts3215_by_model(big, capsys):
    assert big.scan() == [1]
    r = result(big, "1")
    assert r["verdict"] == "ОК" and r["measured"] == "1" and str(sts.MODEL_STS3215) in r["note"]
    assert "привод №1: STS3215" in capsys.readouterr().out


def test_scan_warns_about_wrong_model(big, capsys):
    big.bus.servos[1].mem[sts.MODEL[0]] = 1234
    big.scan()
    assert "модель 1234 — НЕ STS3215" in capsys.readouterr().out


def test_scan_shows_model_number_for_unknown_mini(mini, capsys):
    mini.scan()
    assert "модель 2312 — номер запишется" in capsys.readouterr().out


@pytest.mark.parametrize("key, hint", [("sts3215", "питание 12 В"), ("sts3032", "6,0 В на клеммах")])
def test_scan_empty_bus_fails_with_hint(key, hint, capsys):
    b = make(key, ids=())
    assert b.scan() == []
    assert result(b, "1")["verdict"] == "НЕ ОК" and hint in capsys.readouterr().out


def test_assign_id_renumbers_the_only_servo(mini):
    answer(mini, {"Новый номер": "21"})
    mini.assign_id()
    assert list(mini.bus.servos) == [21] and mini.bus.servos[21].mem[sts.LOCK[0]] == 1


def test_assign_id_refuses_with_two_servos(capsys):
    b = make("sts3032", ids=(1, 2))
    b.assign_id()
    assert sorted(b.bus.servos) == [1, 2] and "Найдено приводов: 2" in capsys.readouterr().out


# ---------- замер 2: ток ----------
def test_current_idle_and_stall_on_sts3215(big):
    big.current_test(1)
    idle, stall = result(big, "2а"), result(big, "2б")
    assert idle["verdict"] == "ОК" and float(idle["measured"].split()[0]) == pytest.approx(0.06, abs=0.01)
    assert stall["verdict"] == "ОК" and float(stall["measured"].split()[0]) == pytest.approx(2.7, abs=0.15)
    assert released(big) and big.bus.servos[1].block_at is None


def test_stall_reading_from_power_supply_rescales_current(big):
    answer(big, {"во время упора": "2.6"})
    big.current_test(1)
    r = result(big, "2б")
    assert r["measured"] == "2.60 А" and "масштаб тока уточнён" in r["note"]
    assert big.lsb != sts.CURRENT_LSB_A and json.loads(CALIB_FILE.read_text(encoding="utf-8"))["current_lsb_a"] == big.lsb


@pytest.mark.parametrize("amps, verdict", [("2.4", "ОК"), ("3.0", "ОК"), ("2.39", "НЕ ОК"), ("3.01", "НЕ ОК")])
def test_stall_norm_2_4_to_3_0_amps(big, amps, verdict):
    answer(big, {"во время упора": amps})
    big.current_test(1)
    assert result(big, "2б")["verdict"] == verdict


def test_stall_without_power_reading_keeps_default_scale(big):
    answer(big, {"во время упора": "-"})
    big.current_test(1)
    assert result(big, "2б")["note"] == "масштаб тока по умолчанию" and not CALIB_FILE.exists()


@pytest.mark.parametrize("amps, verdict", [("0.05", "ОК"), ("0.08", "ОК"), ("0.09", "НЕ ОК")])
def test_mini_idle_current_is_read_from_power_supply(mini, amps, verdict):
    answer(mini, {"блок питания": amps})
    mini.current_test(1)
    r = result(mini, "2а")
    assert r["verdict"] == verdict and r["measured"] == f"{float(amps):.3f} А" and r["note"] == "паспорт 20 мА"
    assert len(mini.results) == 1 and released(mini)                # упор у мини — на ноге


def test_push_never_presses_longer_than_two_seconds(big):
    s = big.servo(1)
    s.torque(True)
    big.bus.servos[1].block_at = s.pos() + 50
    t0 = big.clock()
    amps = big.push(s, s.pos() + 400, seconds=5.0)
    assert big.clock() - t0 <= 2.2 and amps == pytest.approx(2.7, abs=0.15)
    assert abs(big.bus.servos[1].mem[sts.GOAL_POS[0]] - big.bus.servos[1].pos) <= 2     # усилие снято


# ---------- замер 3: момент ----------
def test_torque_at_12_volts(big):
    answer(big, {"Максимум на весах": "2.6"})
    big.torque_test(1)
    r = result(big, "3")
    assert r["test"] == "Момент при 12.0 В" and r["measured"] == "2.60 кг (26.0 кг·см)" and r["verdict"] == "ОК"
    assert released(big) and big.bus.servos[1].block_at is None


def test_torque_at_low_voltage_has_its_own_norm():
    b = make("sts3215")
    replies = {"12,0 В? (д/н)": "н", "10,2 В? (д/н)": "д", "Максимум на весах": "1.9"}

    def ask(text, default=""):
        if "Выставь на блоке 10.2 В" in text:
            b.bus.servos[1].volt = 10.2                                # человек выставил 10,2 В на блоке питания
        return next((v for k, v in replies.items() if k in text), default)

    b.ask = ask
    b.torque_test(1)
    r = result(b, "3")
    assert r["test"] == "Момент при 10.2 В" and r["norm"] == "≥ 2,0 кг" and r["verdict"] == "НЕ ОК"


def test_torque_default_follows_stall_current(big):
    asked = answer(big, {})
    big.torque_test(1)
    kg = float(result(big, "3")["measured"].split()[0])
    assert kg == pytest.approx(3.0, abs=0.2)                         # паспорт: 30 кг·см на 12 В
    assert any("Максимум на весах" in q for q in asked)


def test_torque_skipped_reading_records_nothing(big):
    answer(big, {"Максимум на весах": "-"})
    big.torque_test(1)
    assert big.results == []


def test_torque_on_mini_is_measured_on_the_leg(mini, capsys):
    mini.torque_test(1)
    assert mini.results == [] and "на собранной ноге" in capsys.readouterr().out


# ---------- замер 4: скорость ----------
@pytest.mark.parametrize("key", ["sts3215", "sts3032"])
def test_speed_matches_datasheet(key):
    b = make(key)
    b.speed_test(1)
    r = result(b, "4")
    t90 = float(r["measured"].split()[0])
    assert r["verdict"] == "ОК" and t90 == pytest.approx(b.p.t90_spec, rel=0.15)
    assert r["norm"] == f"≤ {str(round(b.p.t90_spec * 1.2, 2)).replace('.', ',')} с" and released(b)


def test_slow_servo_fails_speed_norm(big):
    big.bus.servos[1].vmax_free /= 2
    big.speed_test(1)
    r = result(big, "4")
    assert r["verdict"] == "НЕ ОК" and float(r["measured"].split()[0]) == pytest.approx(0.67, rel=0.15)


def test_speed_turns_away_from_the_end_of_range(big, monkeypatch):
    big.bus.servos[1].pos = 3000.0                                    # у верхнего края: поворот вниз, а не за 4095
    goals, move = [], sts.Servo.move
    monkeypatch.setattr(sts.Servo, "move", lambda self, pos, speed=0, accel=0: (goals.append(pos), move(self, pos, speed, accel)))
    big.speed_test(1)
    assert min(goals) == pytest.approx(3000 - 1024, abs=2) and max(goals) <= 3002


# ---------- замер 5: люфт ----------
def test_backlash_from_laser_spot(big):
    answer(big, {"до стены": "2000", "Размах пятна": "17.45"})
    big.backlash_test(1)
    r = result(big, "5")
    assert r["measured"] == "0.50° (17 мм на 2000 мм)" and r["verdict"] == "ОК" and released(big)


def test_backlash_over_one_degree_fails(big):
    answer(big, {"Размах пятна": "18"})
    big.backlash_test(1)
    assert result(big, "5")["verdict"] == "НЕ ОК"                    # 18 мм на 1 м = 1,03°


def test_backlash_not_measured(big):
    answer(big, {"Размах пятна": "-"})
    big.backlash_test(1)
    r = result(big, "5")
    assert r["verdict"] == "—" and r["measured"] == "не измерен"


# ---------- замер 6: точность возврата ----------
def test_repeatability_of_a_good_servo(big):
    answer(big, {"указки": "2"})
    big.repeat_test(1)
    r = result(big, "6")
    assert r["verdict"] == "ОК" and r["note"] == "по указке: 2 мм" and float(r["measured"][:-1]) <= 0.3


def test_repeatability_fails_when_returns_scatter(big, monkeypatch):
    jitter = iter([10, -10] * 50)
    monkeypatch.setattr(fake.random, "uniform", lambda a, b: next(jitter) if (a, b) == (-0.6, 0.6) else 0.0)
    answer(big, {"указки": "-"})
    big.repeat_test(1)
    r = result(big, "6")
    assert r["verdict"] == "НЕ ОК" and r["note"] == "" and float(r["measured"][:-1]) == pytest.approx(20 * STEP_DEG, abs=0.1)


# ---------- замер 7: нагрев ----------
def test_heat_short_run_logs_and_passes(big):
    big.heat_test(1, minutes=0.2)
    r = result(big, "7")
    assert r["verdict"] == "ОК" and r["test"] == "Нагрев на номинале, 0 мин"
    assert big.log_rows and len(big.log_rows[0]) == len(big.log_header) == 5
    assert released(big) and big.bus.servos[1].ext_load_frac == 0.0


@pytest.mark.parametrize("case, verdict", [("65", "ОК"), ("66", "НЕ ОК"), ("-", "ОК")])
def test_heat_case_norm_65(big, case, verdict):
    answer(big, {"термопаре": case})
    big.heat_test(1, minutes=0.1)
    assert result(big, "7")["verdict"] == verdict


def test_heat_stops_at_70_degrees(big):
    check = big.precheck

    def hot(s, **kw):
        ok = check(s, **kw)
        big.bus.servos[1].temp = 70.5
        return ok

    big.precheck = hot
    big.heat_test(1, minutes=1.0)
    r = result(big, "7")
    assert r["verdict"] == "НЕ ОК" and r["note"] == "остановлен: 70 °C" and len(big.log_rows) == 1


def test_heat_stops_after_five_seconds_of_overcurrent(big, monkeypatch):
    monkeypatch.setattr(FakeServo, "current", lambda self: 2.5)
    big.heat_test(1, minutes=1.0)
    r = result(big, "7")
    assert r["note"] == "остановлен: ток > 2,2 А дольше 5 с" and r["verdict"] == "НЕ ОК"
    assert 4 <= len(big.log_rows) <= 5                               # отсчёт раз в 2 с: 0, 2, 4, 6 с


def test_heat_mean_current_over_norm_fails(big, monkeypatch):
    monkeypatch.setattr(FakeServo, "current", lambda self: 1.2)
    big.heat_test(1, minutes=0.1)
    r = result(big, "7")
    assert r["verdict"] == "НЕ ОК" and r["note"] == ""
    assert float(r["measured"].split("ток ")[1].split()[0]) == pytest.approx(1.2, abs=0.04)     # регистр с шумом ±3 %


def test_heat_on_mini_is_measured_on_the_leg(mini):
    mini.heat_test(1)
    assert mini.results == []


# ---------- размеры привода ----------
def test_servo_dimensions_go_to_report_and_file(mini):
    answer(mini, {"horn_top": "5.2", "shaft_from_end": "5.8", "body_L": "-"})       # допуск ±0,3: 5,2 вне, 5,8 в
    measure_servo(mini)
    rows = {r["test"]: r for r in mini.results}
    assert rows["Размер horn_top"]["verdict"] == "НЕ ОК" and rows["Размер horn_top"]["note"] == "поправить CAD перед печатью"
    assert rows["Размер shaft_from_end"]["verdict"] == "ОК" and rows["Размер shaft_from_end"]["note"] == ""
    assert "Размер body_L" not in rows
    saved = json.loads(Path("servo_measurements.json").read_text(encoding="utf-8"))
    assert saved == {"horn_top": 5.2, "shaft_from_end": 5.8, "body_D": 27.5, "total_D": 37.2}


def test_servo_dimensions_all_skipped_write_no_file(mini):
    answer(mini, {"": "-"})
    measure_servo(mini)
    assert mini.results == [] and not Path("servo_measurements.json").exists()


# ---------- отчёт ----------
def test_save_writes_excel_and_json(big):
    big.add("1", "Связь", "1", "все", True)
    big.log_rows = [[0.0, 26, 0.06, 12.0, 2048]]
    path = big.save()
    assert path.exists()
    d = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    assert d["servo"] == "sts3215" and d["results"][0]["verdict"] == "ОК" and d["log"] == big.log_rows


# ---------- нормы нагрева (чистые функции) ----------
@pytest.mark.parametrize("temp, amps, over_since, now, expected", [
    (69, 1.0, None, 100.0, ("", None)),                                   # всё в норме
    (70, 1.0, None, 100.0, ("остановлен: 70 °C", None)),                  # датчик дошёл до 70 °C
    (40, 2.3, None, 100.0, ("", 100.0)),                                  # перегрузка началась — засекаем
    (40, 2.3, 100.0, 105.0, ("", 100.0)),                                 # ровно 5 с — ещё можно
    (40, 2.3, 100.0, 105.1, ("остановлен: ток > 2,2 А дольше 5 с", 100.0)),
    (40, 2.2, 100.0, 110.0, ("", None)),                                  # ток вернулся к 2,2 А — отсчёт сброшен
])
def test_heat_abort_by_temperature_and_long_overcurrent(temp, amps, over_since, now, expected):
    from harvey_bench.bench import heat_abort

    assert heat_abort(temp, amps, over_since, now) == expected


@pytest.mark.parametrize("peak, mean_i, case, aborted, ok", [
    (70, 1.1, 65, "", True), (71, 1.0, 50, "", False), (60, 1.11, 50, "", False), (60, 1.0, 66, "", False),
    (60, 1.0, None, "", True), (60, 1.0, 50, "остановлен", False)])
def test_heat_ok_norms(peak, mean_i, case, aborted, ok):
    from harvey_bench.bench import heat_ok

    assert heat_ok(peak, mean_i, case, aborted) is ok


def test_heat_holds_the_weight_with_torque_on(big):
    held = []
    sleep = big.sleep
    big.sleep = lambda sec: (held.append(big.bus.servos[1].mem[sts.TORQUE_ENABLE[0]]), sleep(sec))
    big.heat_test(1, minutes=0.1)
    assert held and all(held) and released(big)                      # всё время замера — с моментом, в конце отпущен


def test_heat_case_default_is_sensor_minus_three(big):
    big.heat_test(1, minutes=0.1)
    measured = result(big, "7")["measured"]
    sensor = int(measured.split("датчик ")[1].split()[0])
    assert f"корпус {float(sensor - 3)} °C" in measured
