# Харви — что значит показание IMU для робота: наклон, падение, удар. Чистые функции, без железа.
# Пороги — оценки (ПРЕДВАРИТЕЛЬНО, уточнить на стенде и в симуляции): свободное падение — сумма ускорений < 0,35 g
# дольше 30 мс, удар — > 2,5 g или вращение > 300 °/с, опрокидывание — наклон > 35°.

import math

FREEFALL_G, FREEFALL_MS = 0.35, 30
SHOCK_G, SHOCK_DPS = 2.5, 300.0
TIP_DEG = 35.0


def magnitude(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def tilt(acc):
    """(крен, тангаж) в градусах по направлению силы тяжести; оси: x — вперёд, y — влево, z — вверх."""
    ax, ay, az = acc
    roll = math.degrees(math.atan2(ay, az))
    pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
    return roll, pitch


class ImuEvents:
    """Следит за потоком замеров и выдаёт события: «fall», «shock», «tip» — каждое один раз при наступлении."""

    def __init__(self):
        self.fall_ms, self.active = 0, set()

    def update(self, acc, gyr, dt_ms):
        g = magnitude(acc)
        self.fall_ms = self.fall_ms + dt_ms if g < FREEFALL_G else 0
        roll, pitch = tilt(acc)
        now = set()
        if self.fall_ms >= FREEFALL_MS:
            now.add("fall")
        if g > SHOCK_G or magnitude(gyr) > SHOCK_DPS:
            now.add("shock")
        if abs(roll) > TIP_DEG or abs(pitch) > TIP_DEG:
            now.add("tip")
        new = sorted(now - self.active)
        self.active = now
        return new, (roll, pitch)
