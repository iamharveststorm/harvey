# Харви «Компакт мини» — запуск «спинного мозга» на RP2350-Zero (MicroPython выполняет main.py при включении).
# Собирает настоящие устройства по pins.py и крутит Spine. Чего нет на плате — пропускается и попадает в «missing».

import sys

import pins
from compat import sleep_ms


class UsbPort:
    """USB CDC (виртуальный COM-порт к Pi): неблокирующее чтение того, что пришло, и запись."""

    def __init__(self):
        import select
        self.poll = select.poll()
        self.poll.register(sys.stdin, select.POLLIN)
        self.inp, self.out = sys.stdin.buffer, sys.stdout.buffer

    def read(self, limit=512):
        data = bytearray()
        while len(data) < limit and self.poll.poll(0):
            data += self.inp.read(1)
        return bytes(data)

    def write(self, data):
        self.out.write(data)


def try_make(make):
    try:
        return make()
    except (OSError, ValueError):
        return None


def build():
    from machine import I2C, Pin

    import sts_bus
    from beacon import Beacon
    from bmi270 import BMI270
    from edge import EdgeArray
    from ina226 import INA226
    from pio_uart import PioUart

    i2c = I2C(pins.I2C_ID, sda=Pin(pins.SDA), scl=Pin(pins.SCL), freq=pins.I2C_HZ)
    buses = {"A": sts_bus.Bus(uart_id=pins.BUS_A["uart"], tx=pins.BUS_A["tx"], rx=pins.BUS_A["rx"], baud=pins.BUS_BAUD),
             "B": sts_bus.Bus(uart_id=pins.BUS_B["uart"], tx=pins.BUS_B["tx"], rx=pins.BUS_B["rx"], baud=pins.BUS_BAUD),
             "C": sts_bus.Bus(uart=PioUart(pins.BUS_C["pio"], pins.BUS_C["tx"], pins.BUS_C["rx"], pins.BUS_BAUD))}
    edge = EdgeArray(i2c, [Pin(p, Pin.OUT) for p in pins.EDGE_XSHUT], pins.EDGE_NAMES, pins.EDGE_ADDR0,
                     pins.EDGE_BUDGET_MS, pins.EDGE_MARGIN_MM)

    def imu():
        with open("bmi270_config.bin", "rb") as f:
            return BMI270(i2c, f.read())

    def ina():
        dev = INA226(i2c, shunt_ohm=pins.SHUNT_OHM, current_lsb_a=pins.CURRENT_LSB_A)
        dev.alert_below(pins.BAT_CRITICAL_V)
        return dev

    beacon = Beacon(Pin(pins.IR_LEFT, Pin.IN, Pin.PULL_UP), Pin(pins.IR_RIGHT, Pin.IN, Pin.PULL_UP))
    cfg = {"bat_low": pins.BAT_LOW_V, "bat_critical": pins.BAT_CRITICAL_V, "telemetry_ms": pins.TELEMETRY_MS,
           "edge_names": pins.EDGE_NAMES}
    return dict(buses=buses, edge=edge, imu=try_make(imu), ina=try_make(ina), beacon=beacon, cfg=cfg)


def run():
    from spine import Spine

    spine = Spine(UsbPort(), **build())
    spine.handle({"t": "hello"})
    while True:
        try:
            spine.step()
        except Exception as e:                    # ошибка одного прохода не должна ронять мозг: сообщить и дальше
            spine.send({"t": "err", "msg": repr(e)})
        sleep_ms(5)


if __name__ == "__main__":
    run()
