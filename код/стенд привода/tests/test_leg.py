"""Нога «Компакт мини» на имитации стенда: калибровка, позы, стойка, момент бедра, шаг, батарея."""
import json
import math

import pytest

from harvey_bench import sts
from harvey_bench.bench import Bench
from harvey_bench.fake import FakeBus
from harvey_bench.leg import CAL_FILE, CHECK_POSES, GEOM, IDS, LIMITS, NAMES, REF, Leg, LegCal, clamp
from helpers import answer, result


# ---------- калибровка в файле ----------
def test_calibration_survives_save_and_load():
    cal = LegCal(sign={"coxa": -1, "femur": 1, "knee": -1}, offset={"coxa": 3, "femur": 0, "knee": -7}, checked=True)
    cal.save()
    back = LegCal.load()
    assert (back.sign, back.offset, back.checked) == (cal.sign, cal.offset, True)


def test_broken_calibration_file_falls_back_to_defaults():
    CAL_FILE.write_text("{не json", encoding="utf-8")
    cal = LegCal.load()
    assert cal.sign == {j: 1 for j in IDS} and cal.offset == {j: 0 for j in IDS} and not cal.checked


def test_missing_checked_flag_means_not_checked():
    CAL_FILE.write_text(json.dumps({"sign": {j: 1 for j in IDS}, "offset": {j: 0 for j in IDS}}), encoding="utf-8")
    assert LegCal.load().checked is False


# ---------- правила движения и геометрия ----------
@pytest.mark.parametrize("joint", list(LIMITS))
def test_clamp_keeps_angles_inside_motion_rules(joint):
    lo, hi = LIMITS[joint]
    assert clamp(joint, lo - 50) == lo
    assert clamp(joint, hi + 50) == hi
    assert clamp(joint, (lo + hi) / 2) == (lo + hi) / 2


def test_femur_for_height_puts_foot_on_the_surface():
    qk = math.radians(-110)
    qf = GEOM.femur_for_height(qk, -GEOM.zj, math.radians(10))
    assert GEOM.foot(qf, qk)[1] == pytest.approx(-GEOM.zj, abs=0.01)


def test_femur_for_height_keeps_guess_when_surface_out_of_reach():
    guess = math.radians(10)
    assert GEOM.femur_for_height(math.radians(-110), 500.0, guess) == guess


def test_horizontal_is_the_foot_reach():
    qf, qk = math.radians(20), math.radians(-110)
    assert GEOM.horizontal(qf, qk) == GEOM.foot(qf, qk)[0]
    assert GEOM.horizontal(0.0, -math.pi / 2) == pytest.approx(GEOM.fem)


# ---------- приводы на шине ----------
def test_missing_servo_is_named_and_stops_the_test(leg, bus, capsys):
    del bus.servos[3]
    assert leg.require() is False
    assert "№3 (колено)" in capsys.readouterr().out


def test_tests_refuse_to_run_before_calibration(leg, capsys):
    leg.poses()
    leg.stance_scale(hold_s=1)
    leg.femur_torque()
    leg.gait(minutes=0.01)
    assert leg.b.results == []
    assert capsys.readouterr().out.count("Сначала калибровка ноги") == 4


def test_center_all_puts_every_servo_to_middle_and_releases_it(leg, bus):
    bus.table = False                                         # до сборки стенд у края стола, нога свисает
    leg.center_all()
    for s in bus.servos.values():
        assert abs(s.pos - sts.MIDDLE) <= 2
        assert s.mem[sts.TORQUE_ENABLE[0]] == 0
    r = result(leg.b, "сб")
    assert r["verdict"] == "ОК" and "3 привод" in r["measured"]


def test_center_all_with_empty_bus_records_nothing(capsys):
    bus = FakeBus(ids=(), profile=sts.PROFILES["sts3032"])
    leg = Leg(Bench(bus, auto=True, speedup=50, clock=bus.clock, profile=sts.PROFILES["sts3032"]))
    leg.center_all()
    assert leg.b.results == [] and "Приводов нет" in capsys.readouterr().out


# ---------- калибровка ноги ----------
def test_calibration_makes_pose_g_the_middle_and_saves(leg, bus):
    leg.calibrate()
    assert leg.cal.checked and leg.cal.sign == {j: 1 for j in IDS} and leg.cal.offset == {j: 0 for j in IDS}
    assert LegCal.load().checked
    assert all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in bus.servos.values())
    assert bus.table is True                                  # стенд вернули на стол
    assert result(leg.b, "к")["verdict"] == "ОК"


def test_calibration_answer_no_reverses_that_joint(leg):
    answer(leg.b, {"голени ушёл НАРУЖУ": "н"})
    leg.calibrate()
    assert leg.cal.sign == {"coxa": 1, "femur": 1, "knee": -1}
    assert "колено −" in result(leg.b, "к")["measured"]


def test_calibration_stops_when_a_servo_is_missing(leg, bus):
    del bus.servos[2]
    leg.calibrate()
    assert not leg.cal.checked and leg.b.results == []


# ---------- движение ----------
def test_goto_reaches_pose_and_obeys_limits(calibrated):
    calibrated.hold_current_pose()
    calibrated.goto(0.0, 200.0, -110.0, seconds=1.0)          # бедро выше правил — остановится на 85°
    a = calibrated.angles()
    assert a["femur"] == pytest.approx(LIMITS["femur"][1], abs=1.0)
    assert a["knee"] == pytest.approx(-110.0, abs=1.0)


def test_stream_sends_calibrated_goals_to_all_three(calibrated, bus):
    calibrated.cal.sign["knee"] = -1
    calibrated.stream(5.0, 30.0, -100.0)
    for j, deg in (("coxa", 5.0), ("femur", 30.0), ("knee", -100.0)):
        assert bus.servos[IDS[j]].mem[sts.GOAL_POS[0]] == calibrated.cal.to_pos(j, deg)


def test_hold_current_pose_turns_torque_on_with_limit(calibrated, bus):
    calibrated.hold_current_pose(limit=40)
    for s in bus.servos.values():
        assert s.mem[sts.TORQUE_ENABLE[0]] == 1 and s.mem[sts.TORQUE_LIMIT[0]] == 400       # регистр — в десятых долях процента


# ---------- Н1: позы ----------
def test_poses_pass_and_skip_poses_below_the_table(calibrated, bus):
    calibrated.poses()
    below = sum(GEOM.foot(math.radians(qf), math.radians(qk))[1] < -GEOM.zj - 0.5 for _, qf, qk in CHECK_POSES)
    r = result(calibrated.b, "Н1")
    assert below > 0
    assert r["verdict"] == "ОК" and f"({len(CHECK_POSES) - below} из {len(CHECK_POSES)})" in r["test"]
    assert f"{below} поз ниже стола" in r["note"]
    assert all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in bus.servos.values())


def test_poses_fail_when_leg_hits_something(calibrated):
    answer(calibrated.b, {"задевало": "д"})
    calibrated.poses()
    r = result(calibrated.b, "Н1")
    assert r["verdict"] == "НЕ ОК" and r["note"].startswith("задевало")


def test_poses_stop_on_low_voltage(calibrated, bus):
    for s in bus.servos.values():
        s.volt = 5.0
    calibrated.poses()
    assert calibrated.b.results == []


# ---------- Н2: стойка на весах ----------
def test_stance_holds_robot_weight_on_the_scale(calibrated, bus):
    calibrated.stance_scale(hold_s=5)
    r = result(calibrated.b, "Н2")
    assert r["verdict"] == "ОК"
    assert calibrated.stand["grams"] >= 300 and calibrated.stand["end"] >= 0.9 * calibrated.stand["grams"]
    assert calibrated.press_mm >= 0.5
    assert all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in bus.servos.values())


def test_stance_fails_when_scale_shows_weight_loss(calibrated):
    answer(calibrated.b, {"весы сейчас": "100"})
    calibrated.stance_scale(hold_s=2)
    assert result(calibrated.b, "Н2")["verdict"] == "НЕ ОК"


# ---------- Н3: момент бедра ----------
def test_femur_torque_matches_datasheet_stall(calibrated):
    calibrated.femur_torque()
    r = result(calibrated.b, "Н3")
    nm = float(r["measured"].split()[0])
    assert r["verdict"] == "ОК" and nm == pytest.approx(0.44, abs=0.05)


def test_femur_torque_below_norm_fails(calibrated):
    answer(calibrated.b, {"Максимум на весах": "500"})
    calibrated.femur_torque()
    assert result(calibrated.b, "Н3")["verdict"] == "НЕ ОК"


def test_femur_torque_not_measured_has_no_verdict(calibrated):
    answer(calibrated.b, {"Максимум на весах": "-"})
    calibrated.femur_torque()
    r = result(calibrated.b, "Н3")
    assert r["verdict"] == "—" and r["measured"] == "не измерен"


# ---------- Н4–Н5: шаг на месте и батарея ----------
def test_gait_logs_temperatures_and_estimates_battery(calibrated, bus):
    calibrated.gait(minutes=0.1)
    assert result(calibrated.b, "Н4")["verdict"] == "ОК"
    assert result(calibrated.b, "Н5")["n"] == "Н5"
    assert calibrated.b.log_rows and len(calibrated.b.log_rows[0]) == len(calibrated.b.log_header) == 11
    assert all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in bus.servos.values())


def test_gait_stops_when_femur_overheats(calibrated, bus):
    check = calibrated.precheck

    def heat_after_check():
        ok = check()
        bus.servos[IDS["femur"]].temp = 66.0
        return ok

    calibrated.precheck = heat_after_check
    calibrated.gait(minutes=1.0)
    r = result(calibrated.b, "Н4")
    assert r["verdict"] == "НЕ ОК" and "65 °C" in r["note"]


def test_gait_with_sweep_moves_the_coxa(calibrated, bus):
    answer(calibrated.b, {"вперёд-назад": "д"})
    goals = []
    stream = calibrated.stream
    calibrated.stream = lambda qc, qf, qk: (goals.append(qc), stream(qc, qf, qk))
    calibrated.gait(minutes=0.05)
    assert max(goals) > 5 and min(goals) < -5


def test_battery_estimate_from_leg_current(leg):
    leg.stand = {}
    leg.battery(0.3)                            # 6 ног × 0,3 А × 6 В / 0,88 + 2,5 Вт = 14,8 Вт → 22 Вт·ч / 14,8 = 1,5 ч
    r = result(leg.b, "Н5")
    assert "ходьба без остановки ≈ 1.5 ч (14.8 Вт)" in r["measured"] and r["verdict"] == "ОК"


def test_battery_standing_uses_stance_measurement(leg):
    leg.stand = {"grams": 300.0, "amps": 0.66}  # нога на 1/6 веса: 0,06 + 0,6 × 148,8 / 300 = 0,358 А → 17,1 Вт
    leg.battery(0.3)
    assert "стоя ≈ 1.3 ч (17.1 Вт)" in result(leg.b, "Н5")["measured"]


# ---------- траектория шага (чистая функция) ----------
DOWN, UP = (20.0, -110.0), (35.0, -120.0)


@pytest.mark.parametrize("ph, pose", [
    (0.0, (10.0, *DOWN)),                     # начало опоры: стопа впереди на столе
    (0.25, (0.0, *DOWN)),                     # середина опоры: под бедром
    (0.5, (-10.0, *DOWN)),                    # конец опоры — начало переноса: стопа сзади, ещё на столе
    (0.75, (0.0, *UP)),                       # середина переноса: стопа выше всего
])
def test_step_pose_support_then_swing(ph, pose):
    from harvey_bench.leg import step_pose

    assert step_pose(ph, 10.0, DOWN, UP) == pytest.approx(pose, abs=1e-9)


def test_step_pose_closes_the_cycle():
    from harvey_bench.leg import step_pose

    assert step_pose(1.0 - 1e-9, 10.0, DOWN, UP) == pytest.approx(step_pose(0.0, 10.0, DOWN, UP), abs=1e-6)


def test_step_pose_swing_lifts_proportionally():
    from harvey_bench.leg import step_pose

    _, qf, qk = step_pose(0.5 + 1 / 12, 0.0, DOWN, UP)      # синус 30° — половина подъёма
    assert (qf, qk) == pytest.approx((27.5, -115.0), abs=1e-9)


# ---------- точные числа: геометрия и пересчёт шагов ----------
def test_foot_in_pose_g_is_straight_below_the_knee():
    assert GEOM.foot(0.0, -math.pi / 2) == pytest.approx((GEOM.fem, -GEOM.tib), abs=1e-9)
    assert GEOM.foot(math.pi / 2, 0.0) == pytest.approx((0.0, GEOM.fem + GEOM.l2 - GEOM.foot_r), abs=1e-9)


def test_to_pos_uses_offset_and_direction():
    cal = LegCal(sign={"coxa": 1, "femur": -1, "knee": 1}, offset={"coxa": 0, "femur": 12, "knee": -5})
    assert cal.to_pos("femur", 10.0) == round(sts.MIDDLE + 12 - 10.0 / sts.DEG_PER_STEP)
    assert cal.to_pos("knee", -100.0) == round(sts.MIDDLE - 5 - 10.0 / sts.DEG_PER_STEP)
    assert cal.to_deg("femur", sts.MIDDLE + 12) == 0.0


def test_femur_for_height_is_precise():
    qk = math.radians(-100)
    qf = GEOM.femur_for_height(qk, -30.0, 0.0)
    assert GEOM.foot(qf, qk)[1] == pytest.approx(-30.0, abs=1e-6)


# ---------- калибровка: середина не записалась, качание на 10° ----------
def test_calibration_remembers_offset_when_middle_is_not_written(leg, bus, monkeypatch):
    monkeypatch.setattr(sts.Servo, "set_middle", lambda self: None)       # привод не принял команду
    start = {j: round(bus.servos[IDS[j]].pos) for j in IDS}
    leg.calibrate()
    for j in IDS:
        if abs(start[j] - sts.MIDDLE) > 3:
            assert abs(leg.cal.offset[j] - (start[j] - sts.MIDDLE)) <= 1
            assert leg.cal.to_deg(j, start[j]) == pytest.approx(REF[j], abs=0.2)
    assert any(leg.cal.offset.values())


def test_calibration_swings_each_joint_ten_degrees_when_asking(leg, bus):
    moved = {}

    def ask(text, default=""):
        for j, i in IDS.items():
            if NAMES[j].capitalize() + " сдвинулся" in text:
                moved[j] = (leg.b.servo(i).pos() - sts.MIDDLE) * sts.DEG_PER_STEP     # чтение обновляет имитацию
        return default

    leg.b.ask = ask
    leg.calibrate()
    assert moved == pytest.approx({j: 10.0 for j in IDS}, abs=1.0)


def test_goto_speed_brings_all_joints_together(calibrated, bus):
    calibrated.hold_current_pose()
    calibrated.goto(0.0, 40.0, -110.0, seconds=0.01)
    now = {j: calibrated.b.servo(IDS[j]).pos() for j in IDS}
    calibrated.goto(0.0, 10.0, -110.0, seconds=2.0, wait=False)
    fm = bus.servos[IDS["femur"]]
    expected = abs(calibrated.cal.to_pos("femur", 10.0) - now["femur"]) / 2.0
    assert fm.mem[sts.GOAL_SPEED[0]] == pytest.approx(expected, abs=3)
    assert bus.servos[IDS["coxa"]].mem[sts.GOAL_SPEED[0]] == 50          # стоит на месте — минимальная скорость


# ---------- Н2: пороги стойки ----------
def test_stance_stops_pressing_at_the_typed_weight(calibrated):
    answer(calibrated.b, {"стопа ниже на +1.0 мм": "350,5", "стопа ниже": ""})    # до +1,0 мм — Enter «сильнее»
    calibrated.stance_scale(hold_s=1)
    assert calibrated.press_mm == 1.0 and calibrated.stand["grams"] == 350.5


def test_stance_keeps_pressing_while_weight_is_too_low(calibrated):
    answer(calibrated.b, {"стопа ниже": "299"})
    calibrated.stance_scale(hold_s=1)
    assert calibrated.press_mm == 7.5
    assert result(calibrated.b, "Н2")["verdict"] == "НЕ ОК"


@pytest.mark.parametrize("grams, end, verdict", [("300", "270", "ОК"), ("400", "359", "НЕ ОК"), ("299", "299", "НЕ ОК")])
def test_stance_norm_300_grams_and_10_percent(calibrated, grams, end, verdict):
    answer(calibrated.b, {"стопа ниже на +1.0 мм": grams, "стопа ниже на +7.5": grams, "стопа ниже": "", "весы сейчас": end})
    calibrated.stance_scale(hold_s=1)
    assert result(calibrated.b, "Н2")["verdict"] == verdict


def test_stance_uses_power_supply_reading(calibrated):
    answer(calibrated.b, {"ампер": "0.77"})
    calibrated.stance_scale(hold_s=1)
    assert calibrated.stand["amps"] == 0.77 and "ток 0.77 А" in result(calibrated.b, "Н2")["measured"]


# ---------- Н3: расчёт момента и тока ----------
def test_femur_torque_from_grams_and_arm(calibrated):
    answer(calibrated.b, {"Максимум на весах": "1000", "Максимум тока": "1.5"})
    calibrated.femur_torque()
    r = result(calibrated.b, "Н3")
    arm = float(r["measured"].split("плече ")[1].split()[0])
    nm = float(r["measured"].split()[0])
    assert nm == pytest.approx(1.0 * 9.81 * arm / 1000, abs=0.001)    # 1 кг на плече arm мм; плечо в отчёте — до 0,1 мм
    assert f"({nm / 0.0981:.1f} кг·см)" in r["measured"]
    assert r["verdict"] == "НЕ ОК"                                      # 0,26 Н·м < 0,36
    assert "ток в упоре ≈ 1.46 А" in r["note"]                           # 1,5 − 2 × 0,02 (покой двух других)


def test_femur_torque_without_power_reading_has_no_current(calibrated):
    answer(calibrated.b, {"Максимум тока": "-"})
    calibrated.femur_torque()
    assert "ток" not in result(calibrated.b, "Н3")["note"]


# ---------- Н4: пороги нагрева и напряжения при шаге ----------
@pytest.mark.parametrize("case, verdict", [("60", "ОК"), ("61", "НЕ ОК"), ("-", "ОК")])
def test_gait_case_temperature_norm_60(calibrated, case, verdict):
    answer(calibrated.b, {"термопаре в конце": case, "в среднем показывал": "0.5"})
    calibrated.gait(minutes=0.05)
    r = result(calibrated.b, "Н4")
    assert r["verdict"] == verdict and "ток ноги 0.50 А" in r["measured"]


def test_gait_stops_on_low_voltage(calibrated, bus):
    check = calibrated.precheck

    def sag_after_check():
        ok = check()
        for s in bus.servos.values():
            s.volt = 5.0
        return ok

    calibrated.precheck = sag_after_check
    calibrated.gait(minutes=1.0)
    r = result(calibrated.b, "Н4")
    assert r["verdict"] == "НЕ ОК" and "напряжение" in r["note"]
    assert len(calibrated.b.log_rows) == 1


# ---------- нормы и разбор ввода (чистые функции) ----------
@pytest.mark.parametrize("text, grams", [("350", 350.0), ("350,5", 350.5), ("350.5", 350.5), ("", None), ("много", None),
                                         ("1.2.3", None), ("-5", None)])
def test_parse_grams_reads_scale_input(text, grams):
    from harvey_bench.leg import parse_grams

    assert parse_grams(text) == grams


@pytest.mark.parametrize("grams, end, load, ok", [
    (300, 270, 80, True),                     # ровно на границах норм
    (299, 299, 10, False),                    # мало веса
    (400, 359, 10, False),                    # просадка больше 10 %
    (400, 400, 81, False),                    # бедро на пределе
    (None, 400, 10, False),                   # вес не ввели
    (400, None, 10, False),                   # конец не ввели
])
def test_stance_ok_norms(grams, end, load, ok):
    from harvey_bench.leg import stance_ok

    assert stance_ok(grams, end, load) is ok


@pytest.mark.parametrize("peak, volt, reason", [
    ({"coxa": 30, "femur": 64, "knee": 30}, 6.0, ""),
    ({"coxa": 65, "femur": 40, "knee": 30}, 6.0, "остановлен: датчик привода 65 °C"),
    ({"coxa": 30, "femur": 40, "knee": 30}, 5.39, "остановлен: напряжение 5.4 В"),
    ({"coxa": 30, "femur": 40, "knee": 30}, 5.4, ""),
])
def test_abort_reason_heat_then_voltage(peak, volt, reason):
    from harvey_bench.leg import abort_reason

    assert abort_reason(peak, volt, vmin=5.4) == reason


@pytest.mark.parametrize("aborted, femur, case, ok", [
    ("", 60, 60, True), ("", 61, None, False), ("", 50, 61, False), ("", 50, None, True), ("остановлен", 40, 40, False)])
def test_gait_ok_norms(aborted, femur, case, ok):
    from harvey_bench.leg import gait_ok

    assert gait_ok(aborted, femur, case) is ok
