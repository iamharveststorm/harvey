# Харви — шина приводов Feetech STS (STS3032, STS3215) для Pico 2 на MicroPython.
#
# Pico 2 — UART0: GP0 (TX) → RX адаптера шины, GP1 (RX) ← TX адаптера, GND — GND.
# Адаптер (Waveshare Bus Servo Adapter (A) или FE-URT-1) сам переключает направление полудуплекса.
# Пакет: FF FF ID LEN INSTR PARAMS CHK, CHK = ~(ID + LEN + INSTR + sum(PARAMS)) & 0xFF — как в код/стенд привода/harvey_bench/sts.py.
# Файл работает и на ПК (CPython) — для проверки с имитацией: см. README.

import time

try:
    from machine import UART, Pin
except ImportError:                       # ПК: UART подставляет проверка
    UART = Pin = None

try:
    ticks_us, ticks_diff = time.ticks_us, time.ticks_diff
except AttributeError:
    ticks_us = lambda: int(time.perf_counter() * 1000000)
    ticks_diff = lambda a, b: a - b

PING, READ, WRITE, SYNC_WRITE = 0x01, 0x02, 0x03, 0x83
BROADCAST = 0xFE

MODEL = (3, 2)
ID = (5, 1)
TORQUE_ENABLE = (40, 1)
ACCEL = (41, 1)
GOAL_POS = (42, 2)
GOAL_SPEED = (46, 2)
TORQUE_LIMIT = (48, 2)
LOCK = (55, 1)
STATE = (56, 15)                          # позиция, скорость, нагрузка, напряжение, температура … ток (56–70)

MIDDLE = 2048
DEG_PER_STEP = 360 / 4096


class BusError(Exception):
    pass


def checksum(body):
    return (~sum(body)) & 0xFF


def make_packet(sid, instr, params=b""):
    body = bytes([sid, len(params) + 2, instr]) + bytes(params)
    return b"\xff\xff" + body + bytes([checksum(body)])


def le16(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def u16(b, i=0):
    return b[i] | (b[i + 1] << 8)


def signed(v, bit):
    m = v & ((1 << bit) - 1)
    return -m if v & (1 << bit) else m


def find_status(buf, sid):
    """Ищет в буфере целый пакет от привода sid: (ошибка, данные, начало, конец) или None."""
    n = len(buf)
    i = 0
    while i + 4 <= n:
        if buf[i] != 0xFF or buf[i + 1] != 0xFF:
            i += 1
            continue
        s, ln = buf[i + 2], buf[i + 3]
        if s == 0xFF or ln < 2:
            i += 1
            continue
        end = i + 4 + ln
        if end > n:
            return None
        if s == sid and checksum(buf[i + 2:end - 1]) == buf[end - 1]:
            return buf[i + 4], bytes(buf[i + 5:end - 1]), i, end
        i += 1
    return None


class Bus:
    def __init__(self, uart=None, uart_id=0, tx=0, rx=1, baud=1000000, timeout_us=4000):
        if uart is None:
            uart = UART(uart_id, baudrate=baud, bits=8, parity=None, stop=1, tx=Pin(tx), rx=Pin(rx),
                        timeout=0, timeout_char=0, rxbuf=512)
        self.u = uart
        self.timeout_us = timeout_us
        self.last_us = 0                   # время последнего обмена «запрос → ответ», мкс

    def _drain(self):
        while self.u.any():
            self.u.read()

    def txrx(self, sid, instr, params=b"", reply=True):
        pkt = make_packet(sid, instr, params)
        self._drain()
        t0 = ticks_us()
        self.u.write(pkt)
        if not reply:
            return 0, b""
        buf = b""
        while ticks_diff(ticks_us(), t0) < self.timeout_us:
            k = self.u.any()
            if not k:
                continue
            chunk = self.u.read(k)
            if chunk:
                buf += chunk
            while True:
                res = find_status(buf, sid)
                if res is None:
                    break
                err, data, a, b = res
                if buf[a:b] == pkt:                   # эхо своего пакета (если адаптер его возвращает)
                    buf = buf[b:]
                    continue
                self.last_us = ticks_diff(ticks_us(), t0)
                return err, data
        raise BusError("привод %d не ответил" % sid)

    def ping(self, sid):
        try:
            self.txrx(sid, PING)
            return True
        except BusError:
            return False

    def read(self, sid, reg):
        addr, n = reg
        err, data = self.txrx(sid, READ, bytes([addr, n]))
        if len(data) != n:
            raise BusError("привод %d: ждали %d байт, пришло %d" % (sid, n, len(data)))
        return data

    def write(self, sid, reg, value):
        addr, n = reg
        data = bytes([value & 0xFF]) if n == 1 else le16(value)
        self.txrx(sid, WRITE, bytes([addr]) + data, reply=sid != BROADCAST)

    def sync_write(self, reg, values):
        """values — {номер: значение}; одним пакетом без ответа."""
        addr, n = reg
        p = bytearray([addr, n])
        for sid, v in values.items():
            p += bytes([sid]) + (bytes([v & 0xFF]) if n == 1 else le16(v))
        self.txrx(BROADCAST, SYNC_WRITE, bytes(p), reply=False)

    def state(self, sid):
        """(позиция, нагрузка %, напряжение В, температура °C) одним чтением."""
        b = self.read(sid, STATE)
        return signed(u16(b, 0), 15), signed(u16(b, 4), 10) / 10, b[6] / 10, b[7]

    def model(self, sid):
        return u16(self.read(sid, MODEL))

    def torque(self, sid, on):
        self.write(sid, TORQUE_ENABLE, 1 if on else 0)

    def release_all(self):
        self.write(BROADCAST, TORQUE_ENABLE, 0)
