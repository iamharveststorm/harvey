# Харви — ИК-маяк станции: два TSOP38238 (слева и справа) считают пачки 38 кГц.
# TSOP382 (документы/TSOP382 — даташит Vishay.pdf): выход 0, пока идёт пачка; непрерывную несущую он подавляет,
# поэтому маяк шлёт пачки (схемы/README.md, «Станция»: ~1,4 мс несущая, ~0,6 мс пауза, ~500 пачек в секунду).
# По разнице счёта слева и справа понятно, куда повернуть, чтобы встать лицом к станции.

try:
    from machine import Pin
except ImportError:                                   # ПК
    Pin = None

SEEN_MIN = 20                                         # пачек за окно, чтобы считать маяк видимым (окно 100 мс ≈ 50 пачек)
CENTER_BAND = 0.2                                     # разница счёта ≤ 20 % — маяк прямо впереди


def bearing(left, right, seen_min=SEEN_MIN, band=CENTER_BAND):
    """Куда маяк: «none» — не видно, «left» / «right» — повернуть туда, «ahead» — прямо."""
    total = left + right
    if max(left, right) < seen_min:
        return "none"
    diff = (left - right) / total
    if abs(diff) <= band:
        return "ahead"
    return "left" if diff > 0 else "right"


class Beacon:
    def __init__(self, left_pin, right_pin):
        self.counts = [0, 0]
        for i, p in enumerate((left_pin, right_pin)):
            p.irq(trigger=Pin.IRQ_FALLING, handler=self._counter(i))

    def _counter(self, i):
        def handler(_pin):
            self.counts[i] += 1
        return handler

    def take(self):
        """Счёт за прошедшее окно (и обнуление)."""
        left, right = self.counts
        self.counts = [0, 0]
        return left, right
