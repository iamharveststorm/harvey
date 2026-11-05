"""Копирует голову с ПК на Pi одной командой: tar по ssh с той же раскладкой папок, что в репозитории.

    python setup/deploy.py harvey.local --install     # скопировать и настроить Pi (provision.py под sudo)
    python setup/deploy.py harvey.local               # только скопировать (обновление кода)

Голова ищет код/прошивка/rp2350/link.py и документы/GC9D01 — код запуска Waveshare 0.71.txt по относительным
путям, поэтому на Pi они лежат в ~/harvey на тех же местах. Пароли не трогаются: SSH — по ключу пользователя.
"""
import argparse
import io
import socket
import subprocess
import sys
import tarfile
from pathlib import Path

HEAD = Path("код/голова")
EXTRA = (HEAD / "servo_calib.json", Path("код/прошивка/rp2350/link.py"),
         Path("документы/GC9D01 — код запуска Waveshare 0.71.txt"))
TREES = (HEAD / "harvey_head", HEAD / "setup")


def repo_root() -> Path:
    return Path(__file__).absolute().parents[3]


def files(root: Path) -> list[Path]:
    """Относительные пути файлов для Pi: без __pycache__, *.pyc, тестов; необязательные — только если есть."""
    found = []
    for tree in TREES:
        found += [p.relative_to(root) for p in sorted((root / tree).rglob("*"))
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    found += [p for p in EXTRA if (root / p).is_file()]
    return found


def make_tar(root: Path, paths: list[Path]) -> bytes:
    """tar.gz, имена UTF-8 в POSIX-виде."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT, encoding="utf-8") as tar:
        for path in paths:
            tar.add(root / path, arcname=path.as_posix(), recursive=False)
    return buffer.getvalue()


def ssh_commands(host: str, brain: str, install: bool) -> list[list[str]]:
    commands = [["ssh", host, "mkdir -p ~/harvey && tar xzf - -C ~/harvey"]]
    if install:
        commands.append(["ssh", "-t", host, "sudo python3 ~/harvey/код/голова/setup/provision.py --apply --brain " + brain])
    return commands


def default_brain() -> str:
    return socket.gethostname().lower() + ".local"


def main(argv=None, run=subprocess.run) -> int:
    parser = argparse.ArgumentParser(description="Скопировать голову Харви на Pi по ssh")
    parser.add_argument("host", help="адрес Pi, например harvey.local или pi@harvey.local")
    parser.add_argument("--brain", default=default_brain(), help="адрес ПК с «большим мозгом» (по умолчанию имя этого ПК)")
    parser.add_argument("--install", action="store_true", help="после копирования настроить Pi (provision.py --apply)")
    args = parser.parse_args(argv)
    root = repo_root()
    tar = make_tar(root, files(root))
    for number, command in enumerate(ssh_commands(args.host, args.brain, args.install)):
        result = run(command, input=tar) if number == 0 else run(command)
        if result.returncode:
            print("Не вышло: " + " ".join(command), file=sys.stderr)
            return result.returncode
    print("Скопировано в ~/harvey на " + args.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
