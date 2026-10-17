# Харви — замер 12 стенда: шина приводов от Pico 2.
# Три привода на одной шине, 10 минут: общая команда всем (одним пакетом) и опрос состояния каждого.
# Норма из протокола стенда: обмен с приводом ≤ 1 мс, ни одной ошибки.
#
# Запуск: Thonny → открыть этот файл на Pico → Run (F5). Остановить — Stop/Ctrl+C: приводы отпустятся.
# Перед запуском: блок питания 6,0 В / 3 А в клеммник адаптера, перемычки адаптера — на внешний UART (см. README).

import math
import time

import sts_bus as sb

IDS = (1, 2, 3)            # нога: поворот, бедро, колено
MINUTES = 10
MOVE = True                # качать суставы ±AMP° вокруг текущей позы (нагрузка на шину как при ходьбе)
AMP = 5.0                  # градусов — нога остаётся почти неподвижной, ничего не задевает
PERIOD = 2.0               # с
TORQUE_PCT = 50            # предел момента на время проверки
REPORT_S = 10


def now_s():
    return time.ticks_ms() / 1000 if hasattr(time, "ticks_ms") else time.monotonic()


def run(bus=None, minutes=MINUTES, sleep=time.sleep, clock=now_s):
    bus = bus or sb.Bus()
    print("Харви — шина от Pico 2. Ищу приводы", IDS)
    alive = []
    for i in IDS:
        if bus.ping(i):
            pos, load, volt, temp = bus.state(i)
            print("  №%d: модель %d, позиция %d, %.1f В, %d °C" % (i, bus.model(i), pos, volt, temp))
            alive.append(i)
        else:
            print("  №%d: не отвечает" % i)
    if not alive:
        print("Никого. Проверь: 6 В на клеммнике, перемычки адаптера на UART, GP0 → RX, GP1 ← TX, общая земля.")
        return False
    for v in alive:
        if bus.state(v)[2] > 7.0:
            print("СТОП: напряжение выше 7 В — STS3032 рассчитан на 6 В.")
            return False

    start = {i: bus.state(i)[0] for i in alive}
    amp_steps = int(AMP / sb.DEG_PER_STEP)
    if MOVE:
        for i in alive:
            bus.write(i, sb.TORQUE_LIMIT, TORQUE_PCT * 10)
            bus.write(i, sb.GOAL_POS, start[i])
            bus.torque(i, True)

    errors, cycles, reads = 0, 0, 0
    sum_us, max_us = 0, 0
    last = {i: (0, 0.0, 0.0, 0) for i in alive}
    t0 = clock()
    t_rep = t0
    try:
        while clock() - t0 < minutes * 60:
            t = clock() - t0
            if MOVE:
                k = math.sin(2 * math.pi * t / PERIOD)
                bus.sync_write(sb.GOAL_POS, {i: start[i] + int(amp_steps * k) for i in alive})
            for i in alive:
                try:
                    last[i] = bus.state(i)
                    us = bus.last_us
                    reads += 1
                    sum_us += us
                    max_us = max(max_us, us)
                except sb.BusError as e:
                    errors += 1
                    print("  ошибка:", e)
            cycles += 1
            if clock() - t_rep >= REPORT_S:
                t_rep = clock()
                temps = "/".join("%d" % last[i][3] for i in alive)
                volts = min(last[i][2] for i in alive)
                print("%5.1f мин: циклов %d, ошибок %d, обмен ср. %d мкс, макс. %d мкс, %.1f В, темп. %s °C"
                      % (t / 60, cycles, errors, sum_us // max(reads, 1), max_us, volts, temps))
                if max(last[i][3] for i in alive) >= 65:
                    print("СТОП: привод нагрелся до 65 °C")
                    break
            sleep(0.01)
    finally:
        bus.release_all()
    ok = errors == 0 and max_us <= 1000 and reads > 0
    print("\nИтог: %d приводов, %d циклов, %d чтений, ошибок %d, обмен ср. %d мкс, макс. %d мкс — %s"
          % (len(alive), cycles, reads, errors, sum_us // max(reads, 1), max_us,
             "ОК (норма ≤ 1000 мкс, 0 ошибок)" if ok else "НЕ ОК (норма ≤ 1000 мкс, 0 ошибок)"))
    return ok


if __name__ == "__main__":
    run()
