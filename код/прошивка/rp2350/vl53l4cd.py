# Харви — VL53L4CD: расстояние до стола (датчики края), I2C.
# Источник: документы/VL53L4CD — даташит ST.pdf (DS13812): адрес 0x52 (7 бит — 0x29, разд. 4.2), XSHUT — активный
# низкий, загрузка ≤ 1,2 мс (рис. 6), I2C до 1 МГц. Регистров в даташите нет: ST даёт драйвер ULD (STSW-IMG026).
# Регистры, последовательность запуска и пересчёт времени замера перенесены из драйвера Adafruit CircuitPython_VL53L4CD
# (MIT, © 2022 Carter Nelson for Adafruit Industries), который сам перенесён с ULD. Переписано под machine.I2C.

import struct

from compat import const, sleep_ms

SOFT_RESET = const(0x0000)
I2C_ADDRESS = const(0x0001)
VHV_TIMEOUT_LOOP_BOUND = const(0x0008)
GPIO_HV_MUX_CTRL = const(0x0030)
GPIO_TIO_HV_STATUS = const(0x0031)
RANGE_CONFIG_A = const(0x005E)
RANGE_CONFIG_B = const(0x0061)
INTERMEASUREMENT_MS = const(0x006C)
INTERRUPT_CLEAR = const(0x0086)
SYSTEM_START = const(0x0087)
RESULT_RANGE_STATUS = const(0x0089)
RESULT_DISTANCE = const(0x0096)
RESULT_OSC_CALIBRATE = const(0x00DE)
FIRMWARE_STATUS = const(0x00E5)
MODEL_ID = const(0x010F)
DEFAULT_ADDR = const(0x29)

# 0x2D…0x87: настройки ULD по умолчанию (VL53L4CD_DEFAULT_CONFIGURATION); 0x30 = 0x11 — прерывание активным 0
DEFAULT_CONFIG = bytes((
    0x12, 0x00, 0x00, 0x11, 0x02, 0x00, 0x02, 0x08, 0x00, 0x08, 0x10, 0x01, 0x01, 0x00, 0x00, 0x00,
    0x00, 0xFF, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x0B, 0x00, 0x00, 0x02, 0x14, 0x21,
    0x00, 0x00, 0x05, 0x00, 0x00, 0x00, 0x00, 0xC8, 0x00, 0x00, 0x38, 0xFF, 0x01, 0x00, 0x08, 0x00,
    0x00, 0x01, 0xCC, 0x07, 0x01, 0xF1, 0x05, 0x00, 0xA0, 0x00, 0x80, 0x08, 0x38, 0x00, 0x00, 0x00,
    0x00, 0x0F, 0x89, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x07, 0x05, 0x06, 0x06, 0x00,
    0x00, 0x02, 0xC7, 0xFF, 0x9B, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00,
))

# сырой статус (биты 4…0) → код драйвера ULD; 0 — расстояние верное
STATUS_MAP = (255, 255, 255, 5, 2, 4, 1, 7, 3, 0, 255, 255, 9, 255, 255, 255, 255, 255, 10, 6, 255, 255, 11, 12)
VALID, SIGNAL_TOO_WEAK = 0, 12


def range_status(raw):
    raw &= 0x1F
    return STATUS_MAP[raw] if raw < len(STATUS_MAP) else 255


def macro_period_us(osc_freq):
    return int(2304 * (1073741824.0 / osc_freq)) >> 6


def _encode_timeout(budget_us, period_us, mult):
    """Время замера → (старший, младший) байт RANGE_CONFIG_A / B, как VL53L4CD_SetRangeTiming в ULD."""
    tmp = period_us * mult
    ls = int(((budget_us + ((tmp >> 6) >> 1)) / (tmp >> 6)) - 1)
    ms = 0
    while (ls >> 8) & 0xFFFFFF > 0:
        ls >>= 1
        ms += 1
    return (ms << 8) + (ls & 0xFF)


def range_config(budget_ms, osc_freq):
    """Значения RANGE_CONFIG_A и B для непрерывного режима (интервал между замерами 0)."""
    if not 10 <= budget_ms <= 200:
        raise ValueError("время замера VL53L4CD — от 10 до 200 мс")
    us = (budget_ms * 1000 - 2500) << 12
    period = macro_period_us(osc_freq)
    return _encode_timeout(us, period, 16), _encode_timeout(us, period, 12)


class VL53L4CD:
    def __init__(self, i2c, addr=DEFAULT_ADDR):
        self.i2c, self.addr = i2c, addr
        model = self._read(MODEL_ID, 2)
        if model[0] != 0xEB or model[1] != 0xAA:
            raise OSError("VL53L4CD не отвечает по адресу 0x%02X" % addr)

    # ---------- регистры: 16-битный адрес, старший байт первым ----------
    def _write(self, reg, data):
        self.i2c.writeto(self.addr, struct.pack(">H", reg) + data)

    def _read(self, reg, n=1):
        self.i2c.writeto(self.addr, struct.pack(">H", reg))
        return self.i2c.readfrom(self.addr, n)

    def _u16(self, reg):
        return struct.unpack(">H", self._read(reg, 2))[0]

    # ---------- запуск ----------
    def init(self, budget_ms=20):
        for _ in range(100):
            if self._read(FIRMWARE_STATUS)[0] == 0x03:
                break
            sleep_ms(1)
        else:
            raise OSError("VL53L4CD 0x%02X: не загрузился" % self.addr)
        self._write(0x002D, DEFAULT_CONFIG)
        self._start(0x40)                                         # VHV: первый замер калибрует датчик
        self.wait_ready()
        self.clear()
        self.stop()
        self._write(VHV_TIMEOUT_LOOP_BOUND, b"\x09")
        self._write(0x000B, b"\x00")
        self._write(0x0024, b"\x05\x00")
        self._write(INTERMEASUREMENT_MS, struct.pack(">I", 0))   # непрерывно
        a, b = range_config(budget_ms, self._u16(0x0006))
        self._write(RANGE_CONFIG_A, struct.pack(">H", a))
        self._write(RANGE_CONFIG_B, struct.pack(">H", b))

    def set_address(self, new_addr):
        self._write(I2C_ADDRESS, bytes([new_addr]))
        self.addr = new_addr

    # ---------- замеры ----------
    def _start(self, code):
        self._write(SYSTEM_START, bytes([code]))

    def start(self):
        self._start(0x21)                                         # непрерывный режим

    def stop(self):
        self._start(0x00)

    def clear(self):
        self._write(INTERRUPT_CLEAR, b"\x01")

    def ready(self):
        active_low = self._read(GPIO_HV_MUX_CTRL)[0] & 0x10
        return (self._read(GPIO_TIO_HV_STATUS)[0] & 0x01) == (0 if active_low else 1)

    def wait_ready(self, timeout_ms=1000):
        for _ in range(timeout_ms):
            if self.ready():
                return
            sleep_ms(1)
        raise OSError("VL53L4CD 0x%02X: нет данных" % self.addr)

    def measure(self):
        """(расстояние мм, статус ULD) последнего замера и сброс флага готовности."""
        status = range_status(self._read(RESULT_RANGE_STATUS)[0])
        dist = self._u16(RESULT_DISTANCE)
        self.clear()
        return dist, status
