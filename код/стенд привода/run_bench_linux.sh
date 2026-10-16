#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
python -m pip install -q -r requirements.txt
python -c "from serial.tools import list_ports; [print('  ', p.device, '-', p.description) for p in list_ports.comports()]"
read -rp "Порт адаптера (например /dev/ttyUSB0) или SIM: " PORT
if [ "${PORT^^}" = "SIM" ]; then python -m harvey_bench.bench --sim; else python -m harvey_bench.bench --port "$PORT"; fi
