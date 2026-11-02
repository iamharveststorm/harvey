# Харви — рефлексы «спинного мозга»: решения, которые нельзя ждать от Pi или ПК. Чистые функции.
# Край стола — не пускать корпус в сторону, где под датчиками пусто; подняли или падает — отпустить приводы
# (не бороться с рукой человека и не ломать шестерни); батарея на нуле — сесть.

# какие датчики смотрят в какую сторону движения: индексы в pins.EDGE_NAMES = FL, FR, BL, BR, L, R
FRONT, BACK, LEFT, RIGHT = (0, 1), (2, 3), (4,), (5,)
DEADBAND = 5.0                                         # мм/с и °/с: медленнее — считаем, что стоим


def bus_of(sid):
    """Шина привода по номеру (ID = 10 × конечность + сустав): A — левые ноги, B — правые, C — клешни и глаза."""
    if 11 <= sid <= 33:
        return "A"
    if 41 <= sid <= 63:
        return "B"
    if 71 <= sid <= 92:
        return "C"
    return None


def blocked(v, far):
    """Движение v = (vx вперёд, vy влево, wz) ведёт к краю? Поворот на месте у края тоже запрещён:
    задние или боковые ноги могут сойти со стола."""
    vx, vy, wz = v
    sides = []
    if vx > DEADBAND:
        sides.append(FRONT)
    if vx < -DEADBAND:
        sides.append(BACK)
    if vy > DEADBAND:
        sides.append(LEFT)
    if vy < -DEADBAND:
        sides.append(RIGHT)
    if abs(wz) > DEADBAND:
        sides += [FRONT, BACK, LEFT, RIGHT]
    return any(far[i] for s in sides for i in s)


def lifted(far):
    """Все шесть датчиков не видят стол — робота держат в руке (или он уже упал со стола)."""
    return all(far)


def battery_level(volts, low_v, critical_v):
    if volts <= 0.5:                                    # нет INA226 или батареи — не решаем ничего
        return "unknown"
    if volts < critical_v:
        return "critical"
    if volts < low_v:
        return "low"
    return "ok"


def decide(v, far, imu_new, bat):
    """Что делать с очередной командой движения: «go» — передать приводам, «stop» — держать позу,
    «relax» — отпустить приводы, «sit» — сесть (батарея на нуле)."""
    if "fall" in imu_new or lifted(far):
        return "relax"
    if bat == "critical":
        return "sit"
    if blocked(v, far):
        return "stop"
    return "go"
