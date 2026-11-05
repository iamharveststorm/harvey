"""Настройки головы из переменных окружения: адрес ПК, порт RP2350, устройство ALSA."""
from harvey_head import config

DEFAULTS = {"BRAIN_HOST": "harvey-brain.local", "BRAIN_PORT": 8765, "SPINE_PORT": "/dev/ttyACM0", "ALSA_DEVICE": "default"}


def test_empty_env_gives_defaults():
    assert config.from_env({}) == DEFAULTS


def test_env_overrides_brain():
    got = config.from_env({"HARVEY_BRAIN_HOST": "pc.local", "HARVEY_BRAIN_PORT": "9000"})
    assert got == {**DEFAULTS, "BRAIN_HOST": "pc.local", "BRAIN_PORT": 9000}


def test_env_overrides_spine_and_alsa():
    got = config.from_env({"HARVEY_SPINE_PORT": "/dev/ttyACM1", "HARVEY_ALSA_DEVICE": "plughw:1,0"})
    assert got["SPINE_PORT"] == "/dev/ttyACM1" and got["ALSA_DEVICE"] == "plughw:1,0"
    assert got["BRAIN_HOST"] == DEFAULTS["BRAIN_HOST"]


def test_empty_values_ignored():
    assert config.from_env({"HARVEY_BRAIN_HOST": "", "HARVEY_BRAIN_PORT": ""}) == DEFAULTS


def test_module_constants_follow_from_env():
    assert config.BRAIN_PORT == int(config.BRAIN_PORT) and isinstance(config.BRAIN_HOST, str)
