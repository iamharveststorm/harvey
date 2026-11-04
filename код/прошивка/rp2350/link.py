# Харви — обмен «спинной мозг» RP2350 ↔ «голова» Pi Zero 2 W по USB (виртуальный COM-порт).
# Одна строка — одно сообщение JSON, поле "t" — тип. Этот же файл использует программа головы (код/голова),
# поэтому формат проверяется с обеих сторон одними тестами.
#
# Pi → RP2350:
#   {"t":"j","v":[vx,vy,wz],"q":{"11":2048,…}}  цели суставов (позиции 0…4095) и куда хочет ехать корпус (мм/с, °/с)
#   {"t":"cal"}                                 запомнить расстояние до стола под датчиками края (робот стоит на столе)
#   {"t":"relax"} / {"t":"hold"}                отпустить все приводы / держать текущую позу
#   {"t":"pos?","ids":[11,…]}                   где сейчас приводы (калибровка нулей) → {"t":"pos","q":{"11":2048,…},"missing":[…]}
# RP2350 → Pi:
#   {"t":"tel","ms":…,"edge":[мм…],"far":[0/1…],"tilt":[крен,тангаж],"acc":[g…],"gyr":[°/с…],"bat":[В,А],
#    "ir":[[L,R] слева,[L,R] по центру,[L,R] справа],"beacon":"…","axis":"on"|"left"|"right"|"none"}
#                                               gyr — вращение по осям x, y, z (z — поворот налево): голова считает курс;
#                                               ir — пачки левого и правого светодиода станции; axis — где корпус от оси станции
#   {"t":"ev","ev":"edge"|"fall"|"shock"|"tip"|"lifted"|"bat_low"|"bat_critical"|"docked","info":…}
#   {"t":"err","msg":"…"}

import json

VERSION = 1
MAX_LINE = 2048


def encode(msg):
    return (json.dumps(msg, separators=(",", ":")) + "\n").encode()


def joints(q, v=(0.0, 0.0, 0.0)):
    return {"t": "j", "v": list(v), "q": {str(k): int(p) for k, p in q.items()}}


def decode(line):
    """Строка → сообщение или None, если строка битая (обрыв, мусор при подключении USB)."""
    try:
        msg = json.loads(line)
    except ValueError:
        return None
    return msg if isinstance(msg, dict) and "t" in msg else None


class LineReader:
    """Склеивает куски байт из порта в целые строки. Слишком длинная строка без конца отбрасывается."""

    def __init__(self):
        self.buf = b""

    def feed(self, data):
        self.buf += data
        out = []
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            msg = decode(line.strip())
            if msg is not None:
                out.append(msg)
        if len(self.buf) > MAX_LINE:
            self.buf = b""
        return out
