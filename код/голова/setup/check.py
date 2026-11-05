"""Проверка железа и связи на Pi (запускать на Pi, без sudo):  python3 ~/harvey/код/голова/setup/check.py

Таблица: ✓ — в порядке, ✗ — не так, ? — проверить не удалось (нет команды). Код выхода 0, если все ✓.
ПРЕДВАРИТЕЛЬНО, проверить на стенде: имя карты I2S (`sndrpigooglevoi` для оверлея googlevoicehat-soundcard) и камера.
"""
import glob as _glob
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from harvey_head import config  # noqa: E402

ENV_PATH = "/etc/harvey/head.env"


def cards(aplay_output: str) -> list[str]:
    """Имена карт из `aplay -l` / `arecord -l`."""
    return re.findall(r"^card \d+: (\S+)", aplay_output, re.MULTILINE)


def has_spi(paths: Iterable[str]) -> bool:
    return {"/dev/spidev0.0", "/dev/spidev0.1"} <= set(paths)


def camera_found(rpicam_output: str) -> bool:
    return bool(rpicam_output.strip()) and "No cameras available" not in rpicam_output


def spine_ports(paths: Iterable[str]) -> list[str]:
    return sorted(p for p in paths if p.startswith("/dev/ttyACM"))


def parse_env(text: str) -> dict:
    pairs = (line.split("=", 1) for line in text.splitlines() if "=" in line and not line.lstrip().startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


def brain_reachable(host, port, connect=socket.create_connection, timeout=3) -> tuple[bool, str]:
    try:
        connect((host, port), timeout=timeout).close()
    except OSError as error:
        return False, f"ПК {host}:{port} не отвечает: {error} (брандмауэр Windows? запущен ли harvey_brain?)"
    return True, f"ПК {host}:{port} отвечает"


def _output(run, *cmd):
    """Вывод команды или None, если её нет."""
    try:
        return run(list(cmd), capture_output=True, text=True, timeout=15).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _mark(ok):
    return "?" if ok is None else "✓" if ok else "✗"


def _sound(output, direction):
    if output is None:
        return None, "команда не найдена"
    names = cards(output)
    return bool(names), (", ".join(names) if names else f"нет карты {direction}: оверлей I2S в config.txt? (после sudo reboot)")


def main(run=subprocess.run, glob=_glob.glob, connect=socket.create_connection, read=None, env=None) -> int:
    read = read or (lambda path: Path(path).read_text(encoding="utf-8") if Path(path).exists() else "")
    settings = config.from_env({**parse_env(read(ENV_PATH)), **(os.environ if env is None else env)})
    camera = _output(run, "rpicam-hello", "--list-cameras")
    ports = spine_ports(glob("/dev/ttyACM*"))
    brain_ok, brain_text = brain_reachable(settings["BRAIN_HOST"], settings["BRAIN_PORT"], connect)
    service = _output(run, "systemctl", "is-active", "harvey-head")
    rows = [("SPI (глаза)", has_spi(glob("/dev/spidev*")), "spidev0.0 и spidev0.1"),
            ("звук: вывод", *_sound(_output(run, "aplay", "-l"), "вывода")),
            ("звук: ввод", *_sound(_output(run, "arecord", "-l"), "ввода")),
            ("камера", None if camera is None else camera_found(camera), "rpicam-hello --list-cameras"),
            ("RP2350", bool(ports), ", ".join(ports) or "нет /dev/ttyACM*: кабель USB, main.py на плате"),
            ("ПК", brain_ok, brain_text),
            ("служба", None if service is None else service.strip() == "active", "harvey-head")]
    for name, ok, note in rows:
        print(f"{_mark(ok)} {name:<12} {note}")
    return 0 if all(ok for _, ok, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
