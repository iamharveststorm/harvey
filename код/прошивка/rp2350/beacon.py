# Харви — ИК-маяк станции: два светодиода (левый и правый, между ними перегородка) шлют по очереди пачки 38 кГц
# разной длины: левый — 0,6 мс, правый — 1,2 мс (код/прошивка/станция). Три TSOP38238 на передней стенке: слева,
# по центру, справа. TSOP382 (документы/TSOP382 — даташит Vishay.pdf, стр. 3): выход 0, пока идёт пачка, и длина
# импульса на выходе tpo = tpi ± 5/f0 (±132 мкс) — по ней видно, чья пачка.
# Боковые приёмники — куда повернуть к станции (как раньше). Центральный — по какую сторону оси станции корпус:
# из-за перегородки оба светодиода видны только в узком клине вдоль оси; видно только левый — корпус левее оси.

try:
    from machine import Pin
except ImportError:                                   # ПК
    Pin = None
from compat import ticks_diff, ticks_us

SEEN_MIN = 20                                         # пачек за окно на боковом приёмнике (окно 100 мс ≈ 66 пачек)
CENTER_BAND = 0.2                                     # разница счёта ≤ 20 % — маяк прямо впереди
CODE_SPLIT_US, CODE_MIN_US, CODE_MAX_US = 900, 300, 2000   # короче — левый (600), длиннее — правый (1200); вне — помеха
SEEN_CODE = 10                                        # пачек одного светодиода за окно на центральном (≈ 33)


def bearing(left, right, seen_min=SEEN_MIN, band=CENTER_BAND):
    """Куда маяк: «none» — не видно, «left» / «right» — повернуть туда, «ahead» — прямо."""
    total = left + right
    if max(left, right) < seen_min:
        return "none"
    diff = (left - right) / total
    if abs(diff) <= band:
        return "ahead"
    return "left" if diff > 0 else "right"


def code_of(width_us):
    """Чья пачка по длине импульса TSOP: «L», «R» или None (помеха)."""
    if not CODE_MIN_US <= width_us <= CODE_MAX_US:
        return None
    return "L" if width_us < CODE_SPLIT_US else "R"


def axis_side(left_code, right_code, seen=SEEN_CODE):
    """Где корпус относительно оси станции по центральному приёмнику: «on», «left», «right» или «none»."""
    l, r = left_code >= seen, right_code >= seen
    if l and r:
        return "on"
    if l:
        return "left"
    return "right" if r else "none"


class Beacon:
    """Три приёмника (слева, по центру, справа): счёт пачек левого и правого светодиода за окно."""

    def __init__(self, left_pin, center_pin, right_pin, clock_us=ticks_us):
        self.clock = clock_us
        self.counts = [[0, 0], [0, 0], [0, 0]]
        self.start = [None, None, None]
        for i, p in enumerate((left_pin, center_pin, right_pin)):
            p.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self._edge(i))

    def _edge(self, i):
        def handler(pin):
            now = self.clock()
            if pin.value() == 0:                      # пачка началась
                self.start[i] = now
                return
            if self.start[i] is not None:
                code = code_of(ticks_diff(now, self.start[i]))
                if code is not None:
                    self.counts[i][0 if code == "L" else 1] += 1
            self.start[i] = None
        return handler

    def take(self):
        """Счёт за прошедшее окно ((слева L, R), (центр L, R), (справа L, R)) и обнуление."""
        out = tuple(tuple(c) for c in self.counts)
        self.counts = [[0, 0], [0, 0], [0, 0]]
        return out
