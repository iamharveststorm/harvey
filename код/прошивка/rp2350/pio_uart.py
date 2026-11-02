# Харви — третий UART на PIO для шины C (клешни и глаза): аппаратных UART у RP2350 два, шины три.
# 8N1, каждый бит — 8 тактов автомата (частота автомата = 8 × скорость). Программы — по примерам MicroPython rp2
# (examples/rp2/pio_uart_tx.py, pio_uart_rx.py). Направление полудуплекса переключает интерфейс шины на плате
# (схемы/bus_buffer.svg), поэтому здесь обычные TX и RX. ПРЕДВАРИТЕЛЬНО: проверить на стенде на 1 Мбит/с.
# Интерфейс как у machine.UART — write / any / read, — чтобы шину вёл тот же sts_bus.Bus.

import rp2
from machine import Pin


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_HIGH, out_init=rp2.PIO.OUT_HIGH, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def _tx():
    pull()
    set(x, 7).side(0)[7]                    # старт-бит
    label("bit")
    out(pins, 1)[6]
    jmp(x_dec, "bit")
    nop().side(1)[6]                        # стоп-бит


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT)
def _rx():
    label("start")
    wait(0, pin, 0)                         # ждать старт-бит
    set(x, 7)[10]                           # середина первого бита данных
    label("bit")
    in_(pins, 1)
    jmp(x_dec, "bit")[6]
    jmp(pin, "stop")
    irq(block, 4)                           # нет стоп-бита — ошибка кадра, ждём покоя линии
    wait(1, pin, 0)
    jmp("start")
    label("stop")
    push(block)


class PioUart:
    def __init__(self, pio=0, tx=8, rx=9, baud=1000000):
        base = pio * 4
        self.tx = rp2.StateMachine(base, _tx, freq=8 * baud, sideset_base=Pin(tx), out_base=Pin(tx))
        self.rx = rp2.StateMachine(base + 1, _rx, freq=8 * baud, in_base=Pin(rx, Pin.IN, Pin.PULL_UP), jmp_pin=Pin(rx))
        self.tx.active(1)
        self.rx.active(1)

    def write(self, data):
        for b in data:
            self.tx.put(b)
        return len(data)

    def any(self):
        return self.rx.rx_fifo()

    def read(self, n=None):
        out = bytearray()
        while self.rx.rx_fifo() and (n is None or len(out) < n):
            out.append(self.rx.get() >> 24)
        return bytes(out)
