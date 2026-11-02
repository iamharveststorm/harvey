"""Программа стенда целиком: меню «Компакт» и «Компакт мини» на имитации, выход, Ctrl+C, отчёт."""
import builtins
import json
from pathlib import Path

import pytest

from harvey_bench import bench, sts
from harvey_bench.fake import FakeBus


def report() -> dict:
    files = list(Path(".").glob("bench_results_*.json"))
    assert len(files) == 1, files
    return json.loads(files[0].read_text(encoding="utf-8"))


def typed(monkeypatch, *keys: str) -> None:
    """Человек вводит с клавиатуры keys по очереди; дальше — Ctrl+C."""
    queue = list(keys)

    def fake_input(prompt=""):
        if not queue:
            raise KeyboardInterrupt
        return queue.pop(0)

    monkeypatch.setattr(builtins, "input", fake_input)


def test_without_port_lists_ports_and_exits_2(monkeypatch, capsys):
    from serial.tools import list_ports

    monkeypatch.setattr(list_ports, "comports", lambda: [])
    assert bench.main([]) == 2
    assert "Укажи порт" in capsys.readouterr().out


def test_compact_auto_runs_every_servo_test_and_saves_report():
    assert bench.main(["--sim", "--auto", "--heat-min", "0.02"]) == 0
    r = report()
    assert r["servo"] == "sts3215"
    assert [x["n"] for x in r["results"]] == ["1", "2а", "2б", "3", "4", "5", "6", "7"]
    assert list(Path(".").glob("bench_results_*.xlsx"))


def test_mini_auto_runs_servo_and_leg_program():
    assert bench.main(["--sim", "--auto", "--servo", "sts3032", "--heat-min", "0.02"]) == 0
    r = report()
    assert r["servo"] == "sts3032"
    assert [x["n"] for x in r["results"]] == ["1"] + ["р"] * 5 + ["2а", "4", "6", "к", "Н1", "Н2", "Н3", "Н4", "Н5"]
    assert len(r["log_header"]) == 11                        # журнал шага ноги, а не одного привода


def test_unknown_choice_is_ignored_and_zero_saves(monkeypatch):
    typed(monkeypatch, "x", "15", "0")
    assert bench.main(["--sim"]) == 0
    assert report()["results"] == []


def test_mini_menu_tests_the_servo_found_by_scan(monkeypatch):
    typed(monkeypatch, "1", "6", "", "", "0")                # найти, скорость: номер по умолчанию, Enter, выход
    assert bench.main(["--sim", "--servo", "sts3032"]) == 0
    tests = [x["test"] for x in report()["results"]]
    assert tests[0].startswith("Связь") and "Поворот на 90°" in tests[1]


def test_compact_menu_single_test_uses_typed_servo_number(monkeypatch):
    typed(monkeypatch, "3", "1", "", "-", "0")               # ток: привод 1, Enter у упора, БП не смотрел
    assert bench.main(["--sim"]) == 0
    assert [x["n"] for x in report()["results"]] == ["2а", "2б"]


def test_ctrl_c_releases_every_servo_and_returns_1(monkeypatch):
    released = []
    write = FakeBus.write

    def spy(self, sid, reg, value):
        if sid == sts.BROADCAST and reg == sts.TORQUE_ENABLE:
            released.append(value)
        return write(self, sid, reg, value)

    monkeypatch.setattr(FakeBus, "write", spy)
    typed(monkeypatch)
    assert bench.main(["--sim", "--servo", "sts3032"]) == 1
    assert released == [0]
    assert not list(Path(".").glob("bench_results_*.json"))
