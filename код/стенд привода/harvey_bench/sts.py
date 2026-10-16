"""Минимальный драйвер шины Feetech STS (STS3215 / STS3032) по протоколу SCS/STS.

Пакет команды:  FF FF ID LEN INSTR PARAMS... CHK,  LEN = len(PARAMS) + 2,
CHK = ~(ID + LEN + INSTR + sum(PARAMS)) & 0xFF.
Пакет ответа:   FF FF ID LEN ERROR PARAMS... CHK.

Адреса регистров — таблица SMS/STS (та же, что в LeRobot и фирменном SDK Feetech).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

# --- инструкции ---
PING, READ, WRITE, SYNC_WRITE = 0x01, 0x02, 0x03, 0x83
BROADCAST = 0xFE

# --- регистры (адрес, длина) ---
MODEL = (3, 2)
ID = (5, 1)
BAUD = (6, 1)
MIN_ANGLE = (9, 2)
MAX_ANGLE = (11, 2)
MAX_TEMP = (13, 1)
MAX_TORQUE = (16, 2)          # EEPROM, 0..1000 = 0..100 %
MODE = (33, 1)                # 0 — позиционный режим
TORQUE_ENABLE = (40, 1)
ACCEL = (41, 1)
GOAL_POS = (42, 2)
GOAL_TIME = (44, 2)
GOAL_SPEED = (46, 2)
TORQUE_LIMIT = (48, 2)        # RAM, 0..1000 = 0..100 %
LOCK = (55, 1)                # 0 — EEPROM открыт для записи
PRESENT_POS = (56, 2)
PRESENT_SPEED = (58, 2)
PRESENT_LOAD = (60, 2)
PRESENT_VOLT = (62, 1)        # 0,1 В
PRESENT_TEMP = (63, 1)        # °C
MOVING = (66, 1)
PRESENT_CURRENT = (69, 2)

MODEL_STS3215 = 777
STEPS_PER_REV = 4096
DEG_PER_STEP = 360.0 / STEPS_PER_REV
# Масштаб тока: по данным сообщества ~6,5 мА на единицу. Замер №2 сверяет его с экраном блока питания.
CURRENT_LSB_A = 0.0065


class BusError(Exception):
    """Ошибка связи с приводом."""


def checksum(body: bytes) -> int:
    return (~sum(body)) & 0xFF


def make_packet(servo_id: int, instr: int, params: bytes = b"") -> bytes:
    if not 0 <= servo_id <= 0xFE:
        raise ValueError(f"номер привода вне диапазона: {servo_id}")
    body = bytes([servo_id, len(params) + 2, instr]) + params
    return b"\xff\xff" + body + bytes([checksum(body)])


def parse_status(buf: bytes, servo_id: int) -> tuple[int, bytes, int, int] | None:
    """Ищет в буфере пакет от привода servo_id. Возвращает (байт ошибки, данные, начало, конец) или None,
    если целого пакета с верной контрольной суммой пока нет."""
    i = 0
    while True:
        j = buf.find(b"\xff\xff", i)
        if j < 0 or j + 4 > len(buf):
            return None
        sid, ln = buf[j + 2], buf[j + 3]
        if sid == 0xFF or ln < 2:
            i = j + 1
            continue
        end = j + 4 + ln
        if end > len(buf):
            return None                      # пакет ещё не дошёл целиком
        body = buf[j + 2:end - 1]
        if sid == servo_id and checksum(body) == buf[end - 1]:
            return buf[j + 4], bytes(buf[j + 5:end - 1]), j, end
        i = j + 1


def to_signed(value: int, sign_bit: int) -> int:
    """У Feetech знак хранится отдельным битом (бит 15 — позиция и скорость, бит 10 — нагрузка)."""
    mag = value & ((1 << sign_bit) - 1)
    return -mag if value & (1 << sign_bit) else mag


def u16(data: bytes) -> int:
    return data[0] | (data[1] << 8)


def le16(value: int) -> bytes:
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


class SerialBus:
    """Шина через USB-адаптер (FE-URT-1). Полудуплекс: эхо собственного пакета отбрасывается."""

    def __init__(self, port: str, baud: int = 1_000_000, timeout: float = 0.03):
        import serial  # pyserial

        self.ser = serial.Serial(port, baud, timeout=0)
        self.timeout = timeout

    def close(self) -> None:
        self.ser.close()

    def _txrx(self, servo_id: int, instr: int, params: bytes, expect_reply: bool = True) -> tuple[int, bytes]:
        pkt = make_packet(servo_id, instr, params)
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        self.ser.flush()
        if not expect_reply:
            return 0, b""
        buf = bytearray()
        t_end = time.monotonic() + self.timeout
        while time.monotonic() < t_end:
            chunk = self.ser.read(64)
            if not chunk:
                time.sleep(0.0005)
                continue
            buf += chunk
            while True:
                res = parse_status(bytes(buf), servo_id)
                if res is None:
                    break
                err, data, start, end = res
                if bytes(buf[start:end]) == pkt:     # эхо собственного пакета в полудуплексе
                    del buf[:end]
                    continue
                return err, data
        raise BusError(f"привод {servo_id} не ответил")

    def ping(self, servo_id: int) -> bool:
        try:
            self._txrx(servo_id, PING, b"")
            return True
        except BusError:
            return False

    def read(self, servo_id: int, reg: tuple[int, int]) -> bytes:
        addr, n = reg
        err, data = self._txrx(servo_id, READ, bytes([addr, n]))
        if len(data) != n:
            raise BusError(f"привод {servo_id}: ждали {n} байт, пришло {len(data)}")
        return data

    def write(self, servo_id: int, reg: tuple[int, int], value: int) -> None:
        addr, n = reg
        data = bytes([value & 0xFF]) if n == 1 else le16(value)
        self._txrx(servo_id, WRITE, bytes([addr]) + data, expect_reply=servo_id != BROADCAST)

    def sync_write(self, reg: tuple[int, int], values: dict[int, int]) -> None:
        addr, n = reg
        params = bytearray([addr, n])
        for sid, v in values.items():
            params += bytes([sid]) + (bytes([v & 0xFF]) if n == 1 else le16(v))
        self._txrx(BROADCAST, SYNC_WRITE, bytes(params), expect_reply=False)


@dataclass
class State:
    pos: int
    speed: int
    load_pct: float
    volt: float
    temp: int
    current_a: float


class Servo:
    """Удобные операции поверх шины для одного привода."""

    def __init__(self, bus, servo_id: int, current_lsb: float = CURRENT_LSB_A):
        self.bus, self.id, self.current_lsb = bus, servo_id, current_lsb

    def model(self) -> int:
        return u16(self.bus.read(self.id, MODEL))

    def torque(self, on: bool) -> None:
        self.bus.write(self.id, TORQUE_ENABLE, 1 if on else 0)

    def set_torque_limit(self, pct: float) -> None:
        self.bus.write(self.id, TORQUE_LIMIT, int(max(0.0, min(100.0, pct)) * 10))

    def move(self, pos: int, speed: int = 0, accel: int = 0) -> None:
        """speed = 0 и accel = 0 — максимально быстро."""
        pos = max(0, min(STEPS_PER_REV - 1, int(pos)))
        self.bus.write(self.id, ACCEL, accel)
        self.bus.write(self.id, GOAL_SPEED, speed)
        self.bus.write(self.id, GOAL_POS, pos)

    def pos(self) -> int:
        return to_signed(u16(self.bus.read(self.id, PRESENT_POS)), 15)

    def state(self) -> State:
        pos = to_signed(u16(self.bus.read(self.id, PRESENT_POS)), 15)
        spd = to_signed(u16(self.bus.read(self.id, PRESENT_SPEED)), 15)
        load = to_signed(u16(self.bus.read(self.id, PRESENT_LOAD)), 10) / 10.0
        volt = self.bus.read(self.id, PRESENT_VOLT)[0] / 10.0
        temp = self.bus.read(self.id, PRESENT_TEMP)[0]
        cur = to_signed(u16(self.bus.read(self.id, PRESENT_CURRENT)), 15) * self.current_lsb
        return State(pos, spd, load, volt, temp, abs(cur))

    def set_id(self, new_id: int) -> None:
        if not 1 <= new_id <= 253:
            raise ValueError("номер привода должен быть от 1 до 253")
        self.bus.write(self.id, LOCK, 0)
        self.bus.write(self.id, ID, new_id)
        self.id = new_id
        self.bus.write(self.id, LOCK, 1)
