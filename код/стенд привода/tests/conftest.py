"""Общее для тестов стенда: нога на имитации шины во временной папке."""
import random

import pytest

from harvey_bench import sts
from harvey_bench.bench import Bench
from harvey_bench.fake import FakeLegBus
from harvey_bench.leg import GEOM, Leg

SPEEDUP = 50.0                    # имитация в 50 раз быстрее: секунда стенда — 20 мс теста


@pytest.fixture(autouse=True)
def in_tmp(tmp_path, monkeypatch):
    """Файлы калибровки и отчёты стенд пишет в текущую папку — в тестах это временная папка."""
    monkeypatch.chdir(tmp_path)
    random.seed(1)
    return tmp_path


@pytest.fixture
def bus():
    return FakeLegBus(GEOM, speedup=SPEEDUP)


@pytest.fixture
def bench(bus):
    return Bench(bus, auto=True, speedup=bus.speedup, clock=bus.clock, profile=sts.PROFILES["sts3032"])


@pytest.fixture
def leg(bench):
    return Leg(bench)


@pytest.fixture
def calibrated(leg):
    leg.calibrate()
    leg.b.results.clear()
    return leg
