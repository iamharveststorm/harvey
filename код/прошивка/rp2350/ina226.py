# Харви — INA226: напряжение, ток и мощность батареи (I2C).
# Источник: документы/INA226 — даташит TI.pdf (SBOS547C): регистры — табл. 7-1, CONFIG — табл. 7-2…7-6,
# шина 1,25 мВ/разряд, шунт 2,5 мкВ/разряд (разд. 7.1.2–7.1.3), калибровка — ф. 1 (CAL = 0,00512 / (Current_LSB × R)),
# мощность = 25 × Current_LSB (разд. 6.5.1), Mask/Enable — табл. 7-12, адрес 0x40 при A0 = A1 = GND (табл. 6-2).

from compat import const, sleep_ms

CONFIG, SHUNT, BUS, POWER, CURRENT, CALIB, MASK, ALERT = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07
MANUF_ID, DIE_ID = 0xFE, 0xFF
TI = const(0x5449)

AVG_16 = const(0b010 << 9)
CT_1100US = const(0b100)
MODE_CONT = const(0b111)                       # шунт и шина непрерывно
RESET = const(0x8000)

BUL = const(1 << 12)                           # тревога: напряжение шины ниже порога
AFF = const(1 << 4)                            # флаг сработавшей тревоги
LEN = const(1 << 0)                            # держать тревогу, пока не прочитают Mask/Enable

BUS_LSB_V = 0.00125
SHUNT_LSB_V = 0.0000025


def signed16(v):
    return v - 0x10000 if v & 0x8000 else v


def calibration(current_lsb_a, shunt_ohm):
    """Значение регистра калибровки (ф. 1 даташита)."""
    return int(0.00512 / (current_lsb_a * shunt_ohm))


class INA226:
    def __init__(self, i2c, addr=0x40, shunt_ohm=0.010, current_lsb_a=0.00025):
        self.i2c, self.addr, self.lsb = i2c, addr, current_lsb_a
        if self._read(MANUF_ID) != TI:
            raise OSError("INA226 не отвечает по адресу 0x%02X" % addr)
        self._write(CONFIG, RESET)
        sleep_ms(1)
        self._write(CONFIG, AVG_16 | (CT_1100US << 6) | (CT_1100US << 3) | MODE_CONT)   # 16 × (1,1 + 1,1) мс ≈ 35 мс
        self._write(CALIB, calibration(current_lsb_a, shunt_ohm))

    def _read(self, reg):
        b = self.i2c.readfrom_mem(self.addr, reg, 2)
        return (b[0] << 8) | b[1]

    def _write(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, bytes([(value >> 8) & 0xFF, value & 0xFF]))

    def volts(self):
        return self._read(BUS) * BUS_LSB_V

    def shunt_volts(self):
        return signed16(self._read(SHUNT)) * SHUNT_LSB_V

    def amps(self):
        """Ток через шунт; знак «+» — разряд, если шунт впаян по схеме (ПРОВЕРИТЬ НА СТЕНДЕ: при заряде — «−»)."""
        return signed16(self._read(CURRENT)) * self.lsb

    def watts(self):
        return self._read(POWER) * 25 * self.lsb

    def alert_below(self, volts):
        """ALERT (открытый сток, активный 0) — когда батарея ниже volts; тревога держится до чтения Mask/Enable."""
        self._write(ALERT, int(volts / BUS_LSB_V))
        self._write(MASK, BUL | LEN)

    def alert_fired(self):
        return bool(self._read(MASK) & AFF)
