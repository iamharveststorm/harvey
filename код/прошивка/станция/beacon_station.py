# Станция «Компакт мини» — ИК-маяк на RP2350-Zero: два светодиода TSAL6200 по очереди шлют пачки 38 кГц.
# Левый — 0,6 мс, правый — 1,2 мс, после каждой пачки пауза 0,6 мс. Между светодиодами перегородка: оба видны
# только в узком клине вдоль оси станции, и Харви понимает, по какую сторону оси он стоит (код/прошивка/rp2350/beacon.py).
# TSOP382 (документы/TSOP382 — даташит Vishay.pdf): пачка ≥ 10 периодов, пауза ≥ 12 периодов, ≤ 1700 пачек в секунду.
# Светодиоды — через AO3400A (документы/AO3400A — даташит AOS.pdf: Vgs(th) ≤ 1,45 В, Rds(on) < 48 мОм при 2,5 В),
# 33 Ом от 5 В: (5 − 1,35) / 33 ≈ 110 мА в импульсе (TSAL6200: IFM 200 мА), в среднем ≤ 15 мА.
# ПРЕДВАРИТЕЛЬНО: выводы и номиналы — по схеме станции (схемы/README.md), проверить на стенде.

LED_PINS = {"L": 0, "R": 1}                 # GP0 / GP1 → затворы AO3400A (один срез ШИМ — одна частота)
CARRIER_HZ = 38000
DUTY = 65535 // 3                           # несущая 1/3: импульс ~9 мкс
SCHEDULE = (("L", 600, 600), ("R", 1200, 600))   # (светодиод, пачка мкс, пауза мкс)


def run(leds, sleep_us, cycles=None):
    """Крутить расписание; leds — {"L": ШИМ, "R": ШИМ} с duty_u16; cycles=None — вечно."""
    n = 0
    while cycles is None or n < cycles:
        for name, on, off in SCHEDULE:
            leds[name].duty_u16(DUTY)
            sleep_us(on)
            leds[name].duty_u16(0)
            sleep_us(off)
        n += 1


def main():
    import time

    from machine import PWM, Pin
    leds = {n: PWM(Pin(p), freq=CARRIER_HZ, duty_u16=0) for n, p in LED_PINS.items()}
    run(leds, time.sleep_us)
