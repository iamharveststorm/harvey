"""Прошивка на ПК: файлы прошивки, шины (код/прошивка/pico) и маяка станции — в пути импорта, machine — подмена с FakePin."""
import sys
import types
from pathlib import Path

HERE = Path(__file__).absolute().parent            # без resolve(): mutator подменяет файлы ссылками
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parents[1] / "pico"), str(HERE.parents[1] / "станция")]

from fakes import FakePin  # noqa: E402

if "machine" not in sys.modules:
    sys.modules["machine"] = types.SimpleNamespace(Pin=FakePin)

import pytest  # noqa: E402

CONFIG = HERE.parent / "bmi270_config.bin"


@pytest.fixture
def config():
    return CONFIG.read_bytes()
