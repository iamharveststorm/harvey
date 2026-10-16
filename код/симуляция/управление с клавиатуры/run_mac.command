#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d .venv ] || { echo "[1/3] Создаю окружение Python..."; $PY -m venv .venv; }
. .venv/bin/activate
echo "[2/3] Устанавливаю MuJoCo и numpy..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt
echo "[3/3] Запуск. На macOS окно MuJoCo открывается через mjpython. Клавиши — в этом терминале."
mjpython harvey_teleop.py
