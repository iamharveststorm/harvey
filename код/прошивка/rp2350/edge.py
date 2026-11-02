# Харви — 6 датчиков края VL53L4CD на одной шине I2C.
# У всех датчиков при включении один адрес (0x29), поэтому их будят по одному выводом XSHUT и каждому дают свой
# (VL53L4CD — даташит, разд. 2 «XSHUT», рис. 6: загрузка ≤ 1,2 мс после подъёма XSHUT).
# Край: стол «пропал» — датчик не видит цель или видит её заметно дальше, чем стол при калибровке.

from compat import sleep_ms
from vl53l4cd import SIGNAL_TOO_WEAK, VALID, VL53L4CD

FAR_STATUS = (SIGNAL_TOO_WEAK, 255)             # цели нет или замер не удался — считаем, что под датчиком пусто


def is_edge(dist_mm, status, base_mm, margin_mm):
    """Край под одним датчиком: цели нет или она дальше стола больше чем на margin_mm. До калибровки края нет."""
    if base_mm is None:
        return False
    if status in FAR_STATUS:
        return True
    return status == VALID and dist_mm > base_mm + margin_mm


def baseline(samples):
    """Опорное расстояние до стола: медиана верных замеров (или None, если верных нет)."""
    good = sorted(d for d, st in samples if st == VALID)
    return good[len(good) // 2] if good else None


class EdgeArray:
    def __init__(self, i2c, xshut_pins, names, addr0=0x30, budget_ms=20, margin_mm=25, make=VL53L4CD):
        self.names, self.margin = names, margin_mm
        self.sensors, self.missing = [], []
        for pin in xshut_pins:
            pin.value(0)
        sleep_ms(2)
        for i, (pin, name) in enumerate(zip(xshut_pins, names)):
            pin.value(1)
            sleep_ms(2)                                   # загрузка ≤ 1,2 мс
            try:
                s = make(i2c)
                s.set_address(addr0 + i)
                s.init(budget_ms)
                s.start()
                self.sensors.append(s)
            except OSError:
                pin.value(0)                              # молчащий датчик держим выключенным: он не мешает шине
                self.sensors.append(None)
                self.missing.append(name)
        self.base = [None] * len(names)
        self.last = [(0, 255)] * len(names)

    def read(self):
        """Свежие замеры (мм, статус) всех датчиков; у кого замер ещё не готов — прежний."""
        for i, s in enumerate(self.sensors):
            if s is not None and s.ready():
                self.last[i] = s.measure()
        return self.last

    def calibrate(self, rounds=10, wait_ms=25):
        """Запомнить расстояние до стола: робот стоит на столе, все датчики над ним."""
        samples = [[] for _ in self.names]
        for _ in range(rounds):
            sleep_ms(wait_ms)
            for i, m in enumerate(self.read()):
                samples[i].append(m)
        self.base = [baseline(s) for s in samples]
        return self.base

    def flags(self):
        return [is_edge(d, st, b, self.margin) for (d, st), b in zip(self.last, self.base)]
