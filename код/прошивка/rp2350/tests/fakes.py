"""Имитация железа «спинного мозга» для тестов на ПК: шина I2C, выводы и датчики — по их даташитам."""
import struct

import bmi270
import vl53l4cd


class FakePin:
    IN, OUT, PULL_UP, IRQ_FALLING, IRQ_RISING = 0, 1, 2, 4, 8

    def __init__(self, level=0):
        self.level, self.handler = level, None

    def value(self, v=None):
        if v is None:
            return self.level
        self.level = int(v)

    def irq(self, trigger=None, handler=None):
        self.handler = handler

    def pulse(self, n=1):
        for _ in range(n):
            self.handler(self)

    def burst(self, clock, width_us, gap_us=600):
        """Выход TSOP: 0 на время пачки, потом 1 (прерывание на оба фронта)."""
        self.level = 0
        self.handler(self)
        clock[0] += width_us
        self.level = 1
        self.handler(self)
        clock[0] += gap_us


class FakeI2C:
    """Шина: устройство отвечает, если на его адресе и (для VL53L4CD) поднят его XSHUT."""

    def __init__(self, *devices):
        self.devices = list(devices)

    def _dev(self, addr):
        live = [d for d in self.devices if d.addr == addr and d.awake()]
        if len(live) != 1:
            raise OSError("ENODEV" if not live else "два устройства на 0x%02X" % addr)
        return live[0]

    def readfrom_mem(self, addr, reg, n):
        return self._dev(addr).read8(reg, n)

    def writeto_mem(self, addr, reg, data):
        self._dev(addr).write8(reg, bytes(data))

    def writeto(self, addr, data):
        self._dev(addr).write16(bytes(data))

    def readfrom(self, addr, n):
        return self._dev(addr).read16(n)


class FakeINA226:
    """INA226 по табл. 7-1: ток = шунт × CAL / 2048, мощность = ток × шина / 20000 (разд. 6.5)."""

    def __init__(self, volts=7.4, amps=1.0, shunt_ohm=0.010, addr=0x40):
        self.addr, self.volts, self.amps_real, self.r = addr, volts, amps, shunt_ohm
        self.regs = {0x00: 0x4127, 0x05: 0, 0x06: 0, 0x07: 0, 0xFE: 0x5449, 0xFF: 0x2260}
        self.writes, self.alert = [], False

    def awake(self):
        return True

    def _value(self, reg):
        shunt = int(round(self.amps_real * self.r / 2.5e-6)) & 0xFFFF
        if reg == 0x01:
            return shunt
        if reg == 0x02:
            return int(round(self.volts / 0.00125))
        signed = shunt - 0x10000 if shunt & 0x8000 else shunt
        current = int(signed * self.regs[0x05] / 2048)
        if reg == 0x04:
            return current & 0xFFFF
        if reg == 0x03:
            return abs(current) * self._value(0x02) // 20000
        if reg == 0x06:
            v = self.regs[0x06] | (0x10 if self.alert else 0)
            self.alert = False if self.regs[0x06] & 1 else self.alert
            return v
        return self.regs.get(reg, 0)

    def read8(self, reg, n):
        v = self._value(reg)
        return bytes([v >> 8 & 0xFF, v & 0xFF])

    def write8(self, reg, data):
        v = (data[0] << 8) | data[1]
        self.writes.append((reg, v))
        if reg == 0x00 and v & 0x8000:
            self.regs[0x00] = 0x4127
            return
        self.regs[reg] = v


class FakeBMI270:
    """BMI270: принимает файл конфигурации частями по INIT_ADDR (слова), статус 1 — только если файл верный."""

    def __init__(self, config, addr=0x68):
        self.addr, self.expected = addr, bytes(config)
        self.regs = {0x00: 0x24, 0x21: 0x00, 0x41: 0x02, 0x43: 0x00}
        self.loaded = bytearray(len(config))
        self.raw = (0, 0, 0, 0, 0, 0)

    def awake(self):
        return True

    def read8(self, reg, n):
        if reg == 0x0C:
            return struct.pack("<6h", *self.raw)
        return bytes([self.regs.get(reg, 0)])

    def write8(self, reg, data):
        if reg == bmi270.INIT_DATA:
            off = ((self.regs.get(0x5C, 0) << 4) | (self.regs.get(0x5B, 0) & 0x0F)) * 2
            self.loaded[off:off + len(data)] = data
            return
        self.regs[reg] = data[0]
        if reg == bmi270.INIT_CTRL and data[0] == 1:
            ok = self.regs.get(0x7C) == 0 and bytes(self.loaded) == self.expected
            self.regs[0x21] = 0x01 if ok else 0x02

    def set_motion(self, acc_g, gyr_dps):
        acc_lsb = bmi270.ACC_LSB_PER_G[self.regs[0x41]]
        gyr_lsb = bmi270.GYR_LSB_PER_DPS[self.regs[0x43]]
        self.raw = tuple(int(round(a * acc_lsb)) for a in acc_g) + tuple(int(round(g * gyr_lsb)) for g in gyr_dps)


class FakeVL53L4CD:
    """VL53L4CD: адрес 0x29 после включения, отвечает, только пока XSHUT поднят; замер готов после старта,
    флаг сбрасывается записью 0x01 в 0x0086 и снова поднимается к следующему чтению (непрерывный режим)."""

    def __init__(self, xshut, dist=80, status_raw=9):
        self.xshut, self.addr, self.dist, self.status_raw = xshut, 0x29, dist, status_raw
        self.mem = {0x010F: 0xEB, 0x0110: 0xAA, 0x00E5: 0x03, 0x0006: 0x00, 0x0007: 0x64, 0x00DE: 0x00, 0x00DF: 0xC8}
        self.ptr, self.ranging, self.pending, self.writes = 0, False, False, []
        self.was_on = False

    def awake(self):
        on = bool(self.xshut.value())
        if on and not self.was_on:
            self.addr = 0x29                                         # после XSHUT — снова адрес по умолчанию
        self.was_on = on
        return on

    def write16(self, data):
        self.ptr = (data[0] << 8) | data[1]
        payload = data[2:]
        if not payload:
            return
        self.writes.append((self.ptr, bytes(payload)))
        for i, b in enumerate(payload):
            self.mem[self.ptr + i] = b
        if self.ptr == vl53l4cd.I2C_ADDRESS:
            self.addr = payload[0]
        if self.ptr == vl53l4cd.SYSTEM_START:
            self.ranging = payload[0] in (0x21, 0x40)
            self.pending = self.ranging
        if self.ptr == vl53l4cd.INTERRUPT_CLEAR and self.ranging:
            self.pending = True                                      # следующий замер — к следующему опросу

    def read16(self, n):
        if self.ptr == vl53l4cd.GPIO_TIO_HV_STATUS:
            ready = self.ranging and self.pending
            active_low = self.mem.get(vl53l4cd.GPIO_HV_MUX_CTRL, 0) & 0x10
            return bytes([(0 if ready else 1) if active_low else (1 if ready else 0)])
        if self.ptr == vl53l4cd.RESULT_RANGE_STATUS:
            return bytes([self.status_raw])
        if self.ptr == vl53l4cd.RESULT_DISTANCE:
            self.pending = False
            return struct.pack(">H", self.dist)
        return bytes(self.mem.get(self.ptr + i, 0) for i in range(n))


class FakeBus:
    """Шина приводов для Spine: запоминает пакеты целей и отпускания."""

    def __init__(self, fail=False):
        self.sync, self.released, self.fail = [], 0, fail

    def sync_write(self, reg, values):
        self.sync.append((reg, dict(values)))

    def release_all(self):
        if self.fail:
            raise OSError("шина молчит")
        self.released += 1


class FakePort:
    def __init__(self):
        self.inbox, self.sent = b"", []

    def push(self, *msgs):
        import link
        self.inbox += b"".join(link.encode(m) for m in msgs)

    def read(self):
        data, self.inbox = self.inbox, b""
        return data

    def write(self, data):
        import link
        self.sent += link.LineReader().feed(data)

    def of(self, t, ev=None):
        return [m for m in self.sent if m["t"] == t and (ev is None or m.get("ev") == ev)]
