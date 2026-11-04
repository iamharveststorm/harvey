"""Стенд без приводов — сторона ПК: залить прошивку на Pico 2 / RP2350-Zero, прогнать самопроверку и связь по USB.

    C:/venvs/harvey-bench/Scripts/python.exe bench_pc.py copy        # файлы прошивки на плату (нужен mpremote)
    C:/venvs/harvey-bench/Scripts/python.exe bench_pc.py selftest    # selftest.py на плате → отчёт ОК / НЕТ
    C:/venvs/harvey-bench/Scripts/python.exe bench_pc.py link        # main.py на плате: hello, телеметрия, цели, позиции
    C:/venvs/harvey-bench/Scripts/python.exe bench_pc.py             # всё по порядку
Перемычки для самопроверки — в начале selftest.py. Порт находится сам (USB VID 0x2E8A — Raspberry Pi).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).absolute().parent
VID_RPI = 0x2E8A
SERVO_IDS = [10 * k + i for k in range(1, 7) for i in range(1, 4)] + [10 * k + i for k in (7, 8) for i in range(1, 5)] + [91, 92]

HINTS = {
    "uart_a": ("шина A (UART0)", "перемычка GP0 → GP1"),
    "uart_b": ("шина B (UART1)", "перемычка GP4 → GP5"),
    "pio_bytes": ("шина C (PIO), по байту", "перемычка GP8 → GP9"),
    "pio_burst": ("шина C (PIO), поток 1 Мбит/с", "программа не успевает забирать байты — ответ привода потеряется"),
    "beacon": ("маяк: длины пачек", "перемычка GP16 → GP14 (слева), GP28 (центр), GP15 (справа)"),
    "i2c": ("I2C (GP12 SDA, GP13 SCL)", "датчики не подключены — это не ошибка"),
    "sensors": ("датчики", "датчик ответил, но не так — смотрите ошибку"),
    "loop": ("главный цикл", "проход дольше 5 мс"),
}


def board_files():
    """(откуда, куда) — всё, что нужно на плате: прошивка, драйвер шины, маяк станции, файл IMU."""
    out = [(p, p.name) for p in sorted(HERE.glob("*.py")) if p.name != "bench_pc.py"]
    out += [(HERE / "bmi270_config.bin", "bmi270_config.bin"), (HERE.parent / "pico" / "sts_bus.py", "sts_bus.py"),
            (HERE.parent / "станция" / "beacon_station.py", "beacon_station.py")]
    return out


def find_port():
    from serial.tools import list_ports
    for p in list_ports.comports():
        if p.vid == VID_RPI:
            return p.device
    raise SystemExit("Плата не найдена: подключите Pico 2 по USB (кабель с передачей данных) и прошейте MicroPython.")


def mpremote(port, *args, timeout=120):
    r = subprocess.run([sys.executable, "-m", "mpremote", "connect", port, *args], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return r.stdout + r.stderr


def parse(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def _detail(r: dict) -> str:
    keys = [k for k in r if k not in ("check", "ok")]
    return ", ".join(f"{k} {r[k]}" for k in keys)


def report(results: list[dict]) -> list[str]:
    lines = []
    for r in results:
        if r["check"] == "done":
            continue
        name, hint = HINTS.get(r["check"], (r["check"], ""))
        line = f"{'ОК ' if r.get('ok') else 'НЕТ'} {name}: {_detail(r)}"
        if not r.get("ok") and hint:
            line += f" — проверить: {hint}"
        lines.append(line)
    if not any(r["check"] == "done" for r in results):
        lines.append("НЕТ самопроверка не дошла до конца — смотрите текст ошибки выше")
    return lines


# ---------- связь с прошивкой main.py ----------
def _send(ser, msg):
    ser.write((json.dumps(msg, separators=(",", ":")) + "\n").encode())


def _collect(ser, wait, sec, buf):
    wait(sec)
    buf += ser.read_all()
    msgs = []
    while b"\n" in buf:
        line, rest = buf.split(b"\n", 1)
        buf[:] = rest
        try:
            msgs.append(json.loads(line))
        except ValueError:
            pass
    return msgs


def link_check(ser, clock=time.monotonic, wait=time.sleep) -> list[dict]:
    """hello → версия и чего нет; телеметрия 20 раз в секунду; цели всех 28 приводов без ошибок; позиции — шины молчат."""
    buf = bytearray()
    _send(ser, {"t": "hello"})
    t0 = clock()
    msgs = _collect(ser, wait, 2.0, buf)
    span = clock() - t0
    hello = [m for m in msgs if m.get("t") == "hello"]
    tel = [m for m in msgs if m.get("t") == "tel"]
    out = [{"check": "hello", "ok": bool(hello), "version": hello[0].get("v") if hello else None,
            "missing": hello[0].get("missing") if hello else None},
           {"check": "telemetry", "ok": 18 <= len(tel) / span <= 22, "hz": round(len(tel) / span, 1)}]
    _send(ser, {"t": "j", "v": [0, 0, 0], "q": {str(i): 2048 for i in SERVO_IDS}})
    errs = [m for m in _collect(ser, wait, 0.3, buf) if m.get("t") == "err"]
    out.append({"check": "targets", "ok": not errs, "errors": [e.get("msg") for e in errs]})
    _send(ser, {"t": "pos?", "ids": SERVO_IDS})
    pos = [m for m in _collect(ser, wait, 0.5, buf) if m.get("t") == "pos"]
    out.append({"check": "positions", "ok": bool(pos), "missing": pos[0]["missing"] if pos else None,
                "q": pos[0]["q"] if pos else None})
    _send(ser, {"t": "relax"})
    return out


LINK_HINTS = {"hello": "плата молчит: main.py не запустился? Перезагрузите плату и смотрите вывод в Thonny",
              "telemetry": "телеметрия не 20 раз в секунду", "targets": "прошивка ответила ошибкой на цели",
              "positions": "нет ответа на запрос позиций"}


def link_report(results: list[dict]) -> list[str]:
    lines = []
    for r in results:
        line = f"{'ОК ' if r['ok'] else 'НЕТ'} {r['check']}: {_detail(r)}"
        if not r["ok"]:
            line += " — " + LINK_HINTS[r["check"]]
        lines.append(line)
    return lines


def main(argv):
    what = argv[1] if len(argv) > 1 else "all"
    port = find_port()
    print("плата:", port)
    if what in ("copy", "all"):
        for src, dst in board_files():
            print("→", dst, mpremote(port, "cp", str(src), ":" + dst).strip()[-60:])
    if what in ("selftest", "all"):
        print("\n".join(report(parse(mpremote(port, "run", str(HERE / "selftest.py"))))))
    if what in ("link", "all"):
        mpremote(port, "reset")
        time.sleep(2.0)
        import serial
        with serial.Serial(port, 115200, timeout=0) as ser:
            ser.read_all = lambda: ser.read(ser.in_waiting or 1)
            print("\n".join(link_report(link_check(ser))))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main(sys.argv)
