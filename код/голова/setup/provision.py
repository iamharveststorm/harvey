"""Настройка Pi Zero 2 W под голову Харви (запускается на Pi под sudo; обычно — через deploy.py --install).

    sudo python3 provision.py --dry-run                  # только показать шаги (по умолчанию)
    sudo python3 provision.py --apply --brain pc.local   # выполнить

Повторный запуск ничего не дублирует: config.txt, служба и файл настроек пишутся только если изменились,
правки пользователя в /etc/harvey/head.env не затираются. Пароли и Wi-Fi не трогаются (их вводят в Raspberry Pi Imager).
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, NamedTuple

BLOCK_BEGIN = "# --- harvey ---"
BLOCK_END = "# --- /harvey ---"
# ПРЕДВАРИТЕЛЬНО, проверить на стенде: оверлей googlevoicehat-soundcard для INMP441 + MAX98357A (aplay -l, arecord -l).
HARVEY_LINES = ("dtparam=spi=on", "dtparam=i2c_arm=on", "dtparam=i2s=on", "dtoverlay=googlevoicehat-soundcard",
                "camera_auto_detect=1")
APT = ("python3-venv", "python3-numpy", "python3-pil", "python3-spidev", "python3-gpiozero", "python3-lgpio",
       "alsa-utils", "python3-opencv", "python3-picamera2")
CONFIG_PATH = "/boot/firmware/config.txt"
ENV_PATH = "/etc/harvey/head.env"
UNIT_PATH = "/etc/systemd/system/harvey-head.service"
BRAIN_PORT = 8765
# Группы доступа к железу; в службу не вписываются (нет группы — systemd не запустит службу), а добавляются в пользователя
GROUPS = ("gpio", "spi", "i2c", "audio", "video", "dialout")


class Step(NamedTuple):
    description: str
    action: Callable[[], None]


class Fs:
    """Файловая система Pi; в тестах подменяется."""
    def exists(self, path):
        return Path(path).exists()

    def read(self, path):
        p = Path(path)
        return p.read_text(encoding="utf-8") if p.exists() else None

    def write(self, path, text):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")


def _without_block(text: str) -> str:
    start = text.find(BLOCK_BEGIN)
    if start < 0:
        return text
    end = text.find(BLOCK_END, start)
    return text[:start] + (text[end + len(BLOCK_END):] if end >= 0 else "")


def _last_section(text: str):
    sections = re.findall(r"^\[([^\]]*)\]\s*$", text, re.MULTILINE)
    return sections[-1] if sections else None


def edit_config(text: str) -> str:
    """Блок Харви — в конец секции [all]. Строки, уже включённые у пользователя, не повторяются."""
    base = _without_block(text).rstrip()
    active = {line.strip() for line in base.splitlines()}
    lines = [line for line in HARVEY_LINES if line not in active]
    if not lines:
        return base + "\n"
    if _last_section(base) not in (None, "all"):
        base += "\n\n[all]"
    separator = "\n" if base.endswith("[all]") or not base else "\n\n"
    return base + separator + "\n".join([BLOCK_BEGIN, *lines, BLOCK_END]) + "\n"


def unit_text(user: str, home: str) -> str:
    return f"""[Unit]
Description=Харви: голова (глаза, настроение, тело)
After=network-online.target sound.target
Wants=network-online.target

[Service]
User={user}
EnvironmentFile=-{ENV_PATH}
WorkingDirectory={home}/harvey/код/голова
ExecStart={home}/harvey/venv/bin/python -m harvey_head.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""


def env_text(brain: str) -> str:
    return f"HARVEY_BRAIN_HOST={brain}\nHARVEY_BRAIN_PORT={BRAIN_PORT}\n"


def groups_to_add(existing) -> list[str]:
    return [group for group in GROUPS if group in existing]


def _add_groups(user, run):
    def action():
        present = {g for g in GROUPS if run(["getent", "group", g], check=False).returncode == 0}
        for group in GROUPS:
            if group not in present:
                print(f"   нет группы {group} — пропущено")
        for group in groups_to_add(present):
            run(["usermod", "-aG", group, user], check=True)
    return action


def _missing_config(path):
    def fail():
        raise SystemExit(f"{path} не найден: это не Raspberry Pi OS Bookworm?")
    return fail


def _config_steps(path, fs):
    current = fs.read(path)
    if current is None:
        return [Step(f"Правка {path}: файл не найден (на Pi с Bookworm он есть)", _missing_config(path))]
    new = edit_config(current)
    if new == current:
        return []
    steps = []
    if not fs.exists(path + ".harvey.bak"):
        steps.append(Step(f"Копия {path} -> {path}.harvey.bak", lambda: fs.write(path + ".harvey.bak", current)))
    steps.append(Step(f"Записать блок Харви в {path} (SPI, I2C, I2S, звук, камера)", lambda: fs.write(path, new)))
    return steps


def _write_if_changed(fs, path, text, description):
    return [] if fs.read(path) == text else [Step(description, lambda: fs.write(path, text))]


def plan(user, home, brain, config_path=CONFIG_PATH, fs=None, run=subprocess.run) -> list[Step]:
    fs = fs or Fs()
    venv = f"{home}/harvey/venv"

    def call(*cmd):
        return lambda: run(list(cmd), check=True)
    steps = [Step("Пакеты apt: " + " ".join(APT), call("apt-get", "install", "-y", *APT)),
             Step(f"Окружение Python {venv} (--system-site-packages)",
                  call("sudo", "-u", user, "python3", "-m", "venv", "--system-site-packages", venv)),
             Step("pip install pyserial", call("sudo", "-u", user, f"{venv}/bin/pip", "install", "pyserial"))]
    steps.append(Step(f"Пользователь {user} — в группы доступа к железу ({', '.join(GROUPS)}), которые есть в системе",
                      _add_groups(user, run)))
    steps += _config_steps(config_path, fs)
    if not fs.exists(ENV_PATH):
        steps.append(Step(f"Настройки {ENV_PATH} (адрес ПК {brain})", lambda: fs.write(ENV_PATH, env_text(brain))))
    steps += _write_if_changed(fs, UNIT_PATH, unit_text(user, home), f"Служба {UNIT_PATH}")
    steps += [Step("systemctl daemon-reload", call("systemctl", "daemon-reload")),
              Step("systemctl enable harvey-head", call("systemctl", "enable", "harvey-head"))]
    return steps


def _expand(path: str) -> str:
    return os.path.expanduser(path) if os.name == "posix" else path


def home_of(user: str, expand=_expand) -> str:
    home = expand("~" + user)
    return home if not home.startswith("~") else "/home/" + user


def _parse(argv, env):
    parser = argparse.ArgumentParser(description="Настроить Pi Zero 2 W под голову Харви")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="выполнить шаги (нужен sudo и --brain)")
    mode.add_argument("--dry-run", action="store_true", help="только показать шаги (по умолчанию)")
    parser.add_argument("--brain", help="адрес ПК с «большим мозгом», например pc.local")
    args = parser.parse_args(argv)
    user = env.get("SUDO_USER") or ("" if args.apply else "pi")
    if args.apply and not (args.brain and user):
        parser.error("--apply: нужны --brain и запуск через sudo (пользователь берётся из SUDO_USER)")
    return args, user


def main(argv=None, run=subprocess.run, fs=None, env=None) -> int:
    args, user = _parse(argv, os.environ if env is None else env)
    for number, step in enumerate(plan(user, home_of(user), args.brain or "<адрес ПК>", fs=fs, run=run), 1):
        print(f"{number}. {step.description}")
        if args.apply:
            step.action()
    print("Готово. Перезагрузите Pi: sudo reboot" if args.apply else "Пробный запуск, ничего не изменено. Выполнить: --apply --brain <ПК>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
