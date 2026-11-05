# Установка головы на Pi Zero 2 W — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Когда приедет Pi Zero 2 W: пользователь пишет карту в Raspberry Pi Imager, затем одна команда с ПК копирует голову на Pi, настраивает систему и включает автозапуск; вторая команда на Pi проверяет железо.

**Architecture:** В `код/голова/setup/`: `deploy.py` (ПК, stdlib) упаковывает нужные файлы в tar и передаёт через `ssh host "tar xzf - -C ~/harvey"` с той же раскладкой папок, что в репозитории (голова ищет `код/прошивка/rp2350/link.py` и `документы/GC9D01 — код запуска Waveshare 0.71.txt` по относительным путям); `provision.py` (Pi, python3 stdlib, под sudo) — пакеты, venv, `config.txt`, служба systemd, файл настроек; `check.py` (Pi) — проверка железа и связи. Настройки головы, зависящие от места (адрес ПК, порт RP2350, устройство ALSA), читаются из переменных окружения поверх `config.py`.

**Tech Stack:** Python 3 stdlib (tarfile, subprocess, argparse, socket), OpenSSH (ssh в Windows), systemd, Raspberry Pi OS Lite 64-bit (Bookworm или новее).

**Spec:** этот документ; решения — ведущего (пользователь выбрал пункт «готовая установка для Pi Zero 2 W»).

## Global Constraints
- Не придумывать факты железа. Оверлей звука `googlevoicehat-soundcard` для INMP441 + MAX98357A, имя карты ALSA, VID/PID RP2350 — **предварительно, проверить на стенде**; в коде — комментарий с этой пометкой, в README — шаг проверки.
- Пароли и Wi-Fi код не трогает: их вводит пользователь в Raspberry Pi Imager. SSH — по ключу пользователя.
- Всё повторяемо: второй запуск `provision.py --apply` ничего не дублирует (`config.txt` и файлы — те же байты).
- Код — по `.claude/skills/ub-mode/SKILL.md` (падающий тест первым). Тесты — `C:\venvs\harvey-head\Scripts\python.exe -m pytest -q tests` из `код/голова`; ни одной настоящей команды ssh / apt / systemctl в тестах — исполнитель команд подменяется.
- Пути к файлам вне `код/голова` — и как есть, и через `resolve()`.

## Review Focus
1. `config.txt` уже содержит `dtparam=spi=on` или блок Харви — повтор не дублирует строки (задача 2).
2. В `config.txt` есть секции `[pi4]`, `[cm4]` после `[all]` — блок Харви попадает под `[all]` в конце файла (задача 2).
3. Имена файлов с кириллицей (`код/голова`, `документы/…`) — в tar в UTF-8, распаковываются на Linux теми же именами (задача 1).
4. ПК без `servo_calib.json` (калибровки ещё нет) — deploy не падает, просто не кладёт его (задача 1).
5. ПК недоступен по сети с Pi — `check.py` пишет понятно «ПК <host>:8765 не отвечает: … (брандмауэр Windows?)», а не трассировку (задача 3).

---

### Task 1: Настройки из окружения и deploy
**Files:** Modify `код/голова/harvey_head/config.py`; Create `код/голова/setup/__init__.py` (пустой), `код/голова/setup/deploy.py`; Tests `код/голова/tests/test_config_env.py`, `код/голова/tests/test_deploy.py`.

**Produces:**
- `config.py`: `BRAIN_HOST`, `BRAIN_PORT`, `SPINE_PORT`, `ALSA_DEVICE` берутся из `HARVEY_BRAIN_HOST`, `HARVEY_BRAIN_PORT` (int), `HARVEY_SPINE_PORT`, `HARVEY_ALSA_DEVICE`, иначе прежние значения. Функция `config.from_env(env: Mapping[str, str]) -> dict` (чистая; модуль применяет её к `os.environ`).
- `deploy.py`: `repo_root() -> Path`; `files(root: Path) -> list[Path]` — относительные пути: всё в `код/голова/harvey_head/` и `код/голова/setup/` (без `__pycache__`, `*.pyc`), `код/голова/harvey_head/mini_geometry.json`, `код/голова/servo_calib.json` (если есть), `код/прошивка/rp2350/link.py`, `документы/GC9D01 — код запуска Waveshare 0.71.txt`; `make_tar(root, paths) -> bytes` (gzip, имена UTF-8 POSIX); `ssh_commands(host: str, brain: str, install: bool) -> list[list[str]]` — `["ssh", host, "mkdir -p ~/harvey && tar xzf - -C ~/harvey"]` и при `install` — `["ssh", "-t", host, "sudo python3 ~/harvey/код/голова/setup/provision.py --apply --brain " + brain]`; `main(argv, run=subprocess.run)`: `python setup/deploy.py HOST [--brain NAME] [--install]`; `--brain` по умолчанию `socket.gethostname().lower() + ".local"`.

- [ ] Step 1: тесты — `from_env({"HARVEY_BRAIN_HOST": "pc.local", "HARVEY_BRAIN_PORT": "9000"})` → host `pc.local`, port `9000`, остальные — прежние; пустой env → прежние значения; `files()` на временном дереве: нет `tests/`, нет `__pycache__`, есть `link.py` и файл GC9D01, нет `servo_calib.json`, если его нет; `make_tar` → `tarfile` читает имена `код/голова/harvey_head/head.py` и т. п.; `ssh_commands("harvey.local", "pc.local", True)` — два списка выше; `main` с подменным `run` передаёт tar первому ssh через `input=`.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 2: provision.py
**Files:** Create `код/голова/setup/provision.py`; Test `код/голова/tests/test_provision.py`.

**Produces (чистые функции + шаги):**
- `BLOCK_BEGIN = "# --- harvey ---"`, `BLOCK_END = "# --- /harvey ---"`; `HARVEY_LINES = ("dtparam=spi=on", "dtparam=i2c_arm=on", "dtparam=i2s=on", "dtoverlay=googlevoicehat-soundcard", "camera_auto_detect=1")` (оверлей — предварительно).
- `edit_config(text: str) -> str` — убрать старый блок Харви, если есть, и дописать в конец `[all]`, затем блок с `HARVEY_LINES`; результат — с переводом строки в конце; `edit_config(edit_config(t)) == edit_config(t)`.
- `unit_text(user: str, home: str) -> str` — служба `harvey-head.service`: `After=network-online.target sound.target`, `Wants=network-online.target`, `User={user}`, `SupplementaryGroups=gpio spi i2c audio video dialout`, `EnvironmentFile=-/etc/harvey/head.env`, `WorkingDirectory={home}/harvey/код/голова`, `ExecStart={home}/harvey/venv/bin/python -m harvey_head.main`, `Restart=always`, `RestartSec=3`, `[Install] WantedBy=multi-user.target`.
- `env_text(brain: str) -> str` — `HARVEY_BRAIN_HOST={brain}\nHARVEY_BRAIN_PORT=8765\n`.
- `APT = ("python3-venv", "python3-numpy", "python3-pil", "python3-spidev", "python3-gpiozero", "python3-lgpio", "alsa-utils", "python3-opencv", "python3-picamera2")` (как в README головы).
- `plan(user, home, brain, config_path="/boot/firmware/config.txt") -> list[Step]` — `Step` = (описание по-русски, действие); порядок: apt install → venv `--system-site-packages` + `pip install pyserial` → копия `config.txt.harvey.bak` (только если её нет) → запись `config.txt` (только если изменился) → `/etc/harvey/head.env` (только если его нет — не затирать правки пользователя) → unit → `systemctl daemon-reload` → `systemctl enable harvey-head`.
- `main(argv, run=subprocess.run, fs=…)`: `--apply` выполняет, `--dry-run` (по умолчанию) печатает шаги; `--brain` обязателен с `--apply`; user — из `SUDO_USER`. В конце: «Готово. Перезагрузите Pi: sudo reboot».

- [ ] Step 1: тесты — `edit_config` на образце Bookworm (`[all]`, `dtparam=audio=on`, секции `[pi4]`, `[cm5]`) — блок в конце после `[all]`; повтор — те же байты; старый блок с другими строками заменяется; `unit_text("pi", "/home/pi")` содержит строки выше; `plan` с подменной ФС: при существующем `head.env` шага записи нет, при неизменном `config.txt` — нет записи; `--dry-run` ничего не запускает.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные.

### Task 3: check.py и README
**Files:** Create `код/голова/setup/check.py`; Test `код/голова/tests/test_check.py`; Modify `код/голова/README.md` (раздел «Установка на Pi Zero 2 W» переписать), `CLAUDE.md` (строка про `код/голова/` — `setup/`), `заметки/Журнал решений.md` (строка 2026-11-05).

**Produces:**
- Чистые разборщики: `cards(aplay_l_output: str) -> list[str]` (имена карт из `aplay -l` / `arecord -l`), `has_spi(paths: Iterable[str]) -> bool` (`/dev/spidev0.0` и `/dev/spidev0.1`), `camera_found(rpicam_output: str) -> bool` (вывод `rpicam-hello --list-cameras`: нет строки «No cameras available»), `spine_ports(paths) -> list[str]` (`/dev/ttyACM*`).
- `brain_reachable(host, port, connect=socket.create_connection, timeout=3) -> tuple[bool, str]` — текст ошибки по-русски с подсказкой «брандмауэр Windows?».
- `main(run=subprocess.run, ...)` — таблица «✓ / ✗ / ?» по пунктам: SPI, звук вывод, звук ввод, камера, RP2350, ПК, служба (`systemctl is-active harvey-head`); код выхода 0, если все ✓.
- README: шаги пользователя — Imager (Raspberry Pi OS Lite 64-bit, имя `harvey`, пользователь, Wi-Fi, SSH по ключу), `python setup/deploy.py harvey.local --install`, `sudo reboot`, `python3 ~/harvey/код/голова/setup/check.py`; брандмауэр Windows для порта 8765 — пользователь разрешает сам; что проверить на стенде (оверлей, имя ALSA-карты → `HARVEY_ALSA_DEVICE` в `/etc/harvey/head.env`).

- [ ] Step 1: тесты разборщиков на образцах вывода (с картой `sndrpigooglevoi` и без), `brain_reachable` с подменным connect (успех, `ConnectionRefusedError`, `TimeoutError`), `main` с подменами — код 0 / 1.
- [ ] Step 2: падают. Step 3: реализовать. Step 4: зелёные; все тесты головы зелёные.
