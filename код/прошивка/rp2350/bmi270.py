# Харви — BMI270: ускорение и угловая скорость корпуса (I2C).
# Источник: документы/BMI270 — даташит Bosch.pdf (BST-BMI270-DS000-08):
#   запуск — стр. 18–20: PWR_CONF = 0, ждать ≥ 450 мкс, INIT_CTRL = 0, файл конфигурации 8 КБ в INIT_DATA,
#   INIT_CTRL = 1, через ≥ 20 мс INTERNAL_STATUS.message = 1; частями — INIT_ADDR = смещение / 2 (сноска 4, разд. 5.2.65–66);
#   обычный режим — стр. 22: PWR_CTRL = 0x0E, ACC_CONF = 0xA8, GYR_CONF = 0xA9, PWR_CONF = 0x02;
#   CHIP_ID = 0x24 (разд. 5.2.1), адрес 0x68 при SDO на GND (разд. 7), ACC_RANGE / GYR_RANGE — разд. 5.2.42, 5.2.44,
#   INT1_IO_CTRL — 5.2.58, INT_MAP_DATA — 5.2.63, данные DATA_8…DATA_19 с 0x0C (младший байт первым).
# Файл конфигурации bmi270_config.bin — массив bmi270_config_file из Bosch BMI270 Sensor API v2.86.1 (BSD-3-Clause,
# лицензия — BMI270-CONFIG-LICENSE.txt рядом).

from compat import const, sleep_ms

CHIP_ID, DATA, INTERNAL_STATUS = 0x00, 0x0C, 0x21
ACC_CONF, ACC_RANGE, GYR_CONF, GYR_RANGE = 0x40, 0x41, 0x42, 0x43
INT1_IO_CTRL, INT_MAP_DATA = 0x53, 0x58
INIT_CTRL, INIT_ADDR_0, INIT_ADDR_1, INIT_DATA = 0x59, 0x5B, 0x5C, 0x5E
PWR_CONF, PWR_CTRL = 0x7C, 0x7D
BMI270_ID = const(0x24)
CONFIG_SIZE = const(8192)

ACC_LSB_PER_G = {0: 16384, 1: 8192, 2: 4096, 3: 2048}               # ±2 / 4 / 8 / 16 g
GYR_LSB_PER_DPS = {0: 16.4, 1: 32.8, 2: 65.6, 3: 131.2, 4: 262.4}  # ±2000 / 1000 / 500 / 250 / 125 °/с


def s16(lo, hi):
    v = lo | (hi << 8)
    return v - 0x10000 if v & 0x8000 else v


def init_chunks(config, chunk):
    """Части файла конфигурации: (INIT_ADDR_0, INIT_ADDR_1, байты). Адрес — смещение в словах (байты / 2)."""
    for off in range(0, len(config), chunk):
        word = off // 2
        yield word & 0x0F, (word >> 4) & 0xFF, config[off:off + chunk]


class BMI270:
    def __init__(self, i2c, config, addr=0x68, acc_range=1, gyr_range=1, chunk=256):
        if len(config) != CONFIG_SIZE:
            raise ValueError("файл конфигурации BMI270 — %d байт, нужно %d" % (len(config), CONFIG_SIZE))
        self.i2c, self.addr = i2c, addr
        if self._r(CHIP_ID) != BMI270_ID:
            raise OSError("BMI270 не отвечает по адресу 0x%02X" % addr)
        self._w(PWR_CONF, 0x00)                       # выключить adv_power_save
        sleep_ms(1)                                   # ≥ 450 мкс
        self._w(INIT_CTRL, 0x00)
        for a0, a1, part in init_chunks(config, chunk):
            self._w(INIT_ADDR_0, a0)
            self._w(INIT_ADDR_1, a1)
            self.i2c.writeto_mem(addr, INIT_DATA, part)
        self._w(INIT_CTRL, 0x01)
        for _ in range(10):                           # ≥ 20 мс; ждём до 100 мс
            sleep_ms(10)
            if self._r(INTERNAL_STATUS) & 0x0F == 0x01:
                break
        else:
            raise OSError("BMI270: файл конфигурации не принят (INTERNAL_STATUS = 0x%02X)" % self._r(INTERNAL_STATUS))
        self._w(PWR_CTRL, 0x0E)                       # ускорение, гироскоп, температура
        self._w(ACC_CONF, 0xA8)                       # 100 Гц, обычная фильтрация
        self._w(GYR_CONF, 0xA9)                       # 200 Гц
        self._w(PWR_CONF, 0x02)
        self._w(ACC_RANGE, acc_range)
        self._w(GYR_RANGE, gyr_range)
        self.acc_lsb, self.gyr_lsb = ACC_LSB_PER_G[acc_range], GYR_LSB_PER_DPS[gyr_range]
        self._w(INT1_IO_CTRL, 0x0A)                   # выход включён, активный 1, двухтактный
        self._w(INT_MAP_DATA, 0x04)                   # «данные готовы» → INT1

    def _r(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _w(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def read(self):
        """(ax, ay, az) в g и (gx, gy, gz) в °/с — оси датчика (как он стоит в корпусе — проверить на стенде)."""
        b = self.i2c.readfrom_mem(self.addr, DATA, 12)
        acc = tuple(s16(b[i], b[i + 1]) / self.acc_lsb for i in (0, 2, 4))
        gyr = tuple(s16(b[i], b[i + 1]) / self.gyr_lsb for i in (6, 8, 10))
        return acc, gyr
