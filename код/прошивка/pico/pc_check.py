"""Проверка прошивки шины на ПК, без Pico и приводов: UART подменён имитацией трёх STS3032
(та же имитация, что у стенда, — код/стенд привода/harvey_bench/fake.py).

    python pc_check.py            # с эхом (адаптер возвращает свой пакет) и без эха
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "стенд привода"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from harvey_bench import sts                    # noqa: E402
from harvey_bench.fake import FakeBus            # noqa: E402

import bus_test                                  # noqa: E402
import sts_bus                                   # noqa: E402


class FakeUart:
    """Принимает пакеты как шина: отвечает за приводы имитации, по желанию добавляет эхо."""

    def __init__(self, echo: bool, speedup: float = 30.0):
        self.bus = FakeBus(ids=(1, 2, 3), speedup=speedup, profile=sts.PROFILES["sts3032"])
        self.echo, self.rx = echo, bytearray()

    def any(self) -> int:
        return len(self.rx)

    def read(self, n=None) -> bytes:
        n = len(self.rx) if n is None else n
        out, self.rx = bytes(self.rx[:n]), self.rx[n:]
        return out

    def write(self, pkt: bytes) -> int:
        if self.echo:
            self.rx += pkt
        sid, instr, params = pkt[2], pkt[4], pkt[5:-1]
        reply = None
        if instr == sts_bus.PING and sid in self.bus.servos:
            reply = b""
        elif instr == sts_bus.READ and sid in self.bus.servos:
            reply = self.bus.read(sid, (params[0], params[1]))
        elif instr == sts_bus.WRITE:
            addr, data = params[0], params[1:]
            val = data[0] if len(data) == 1 else data[0] | (data[1] << 8)
            self.bus.write(sid, (addr, len(data)), val)
            reply = b"" if sid != sts_bus.BROADCAST and sid in self.bus.servos else None
        elif instr == sts_bus.SYNC_WRITE:
            addr, n, rest = params[0], params[1], params[2:]
            for k in range(0, len(rest), n + 1):
                d = rest[k + 1:k + 1 + n]
                self.bus.write(rest[k], (addr, n), d[0] if n == 1 else d[0] | (d[1] << 8))
        if reply is not None:
            body = bytes([sid, len(reply) + 2, 0]) + reply
            self.rx += b"\xff\xff" + body + bytes([sts_bus.checksum(body)])
        return len(pkt)


def main() -> int:
    ok_all = True
    for echo in (True, False):
        print(f"\n=== имитация: {'адаптер возвращает эхо' if echo else 'без эха'} ===")
        u = FakeUart(echo)
        bus = sts_bus.Bus(uart=u)
        clock = u.bus.clock
        ok = bus_test.run(bus, minutes=0.5, sleep=lambda s: None, clock=lambda: clock())
        torque_off = all(s.mem[sts.TORQUE_ENABLE[0]] == 0 for s in u.bus.servos.values())
        print("Приводы отпущены в конце:", "да" if torque_off else "НЕТ")
        ok_all = ok_all and ok and torque_off
    print("\nПрошивка на имитации:", "ОК" if ok_all else "ОШИБКА")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
