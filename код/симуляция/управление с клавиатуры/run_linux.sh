#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d .venv ] || { echo "[1/3] Создаю окружение Python..."; $PY -m venv .venv; }
. .venv/bin/activate
echo "[2/3] Устанавливаю MuJoCo и numpy..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt
if [ "$1" = "--test" ]; then python harvey_teleop.py --test; python harvey_scenarios.py surfaces edge; exit 0; fi
echo "[3/3] Запуск: откроются окно симуляции и панель управления (нужен python3-tk)."
python harvey_teleop.py
