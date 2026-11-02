"""Драйверы датчиков против имитаций по даташитам: INA226, BMI270, VL53L4CD."""
import pytest

import bmi270
import ina226
import vl53l4cd
from fakes import FakeBMI270, FakeI2C, FakeINA226, FakePin, FakeVL53L4CD


# ---------- INA226 ----------
def test_ina226_calibration_matches_datasheet_example():
    assert ina226.calibration(0.001, 0.002) == 2560                  # разд. 6.5.1: 1 мА/разряд, 2 мОм → 2560
    assert ina226.calibration(0.00025, 0.010) == 2048                # Харви: 0,25 мА/разряд, 10 мОм


def test_ina226_configures_and_reads_battery():
    dev = FakeINA226(volts=7.4, amps=1.5)
    ina = ina226.INA226(FakeI2C(dev))
    assert (0x00, 0x8000) in dev.writes                              # сброс
    assert dev.regs[0x00] == 0b0000_0101_0010_0111                   # 16 усреднений, 1,1 мс + 1,1 мс, непрерывно
    assert dev.regs[0x05] == 2048
    assert ina.volts() == pytest.approx(7.4, abs=0.00125)
    assert ina.amps() == pytest.approx(1.5, abs=0.001)
    assert ina.shunt_volts() == pytest.approx(0.015, abs=3e-6)
    assert ina.watts() == pytest.approx(7.4 * 1.5, rel=0.01)


def test_ina226_negative_current_while_charging():
    ina = ina226.INA226(FakeI2C(FakeINA226(amps=-1.2)))
    assert ina.amps() == pytest.approx(-1.2, abs=0.001)


def test_ina226_low_battery_alert():
    dev = FakeINA226()
    ina = ina226.INA226(FakeI2C(dev))
    ina.alert_below(6.4)
    assert dev.regs[0x07] == 5120 and dev.regs[0x06] == (1 << 12) | 1      # 6,4 В / 1,25 мВ; BUL + LEN
    assert not ina.alert_fired()
    dev.alert = True
    assert ina.alert_fired()


def test_ina226_missing_raises():
    with pytest.raises(OSError):
        ina226.INA226(FakeI2C())
    other = FakeINA226()
    other.regs[0xFE] = 0x1234
    with pytest.raises(OSError):
        ina226.INA226(FakeI2C(other))


def test_signed16():
    assert ina226.signed16(0x8300) == -32000                         # разд. 7.1.2: −80 мВ = 8300h
    assert ina226.signed16(0x7FFF) == 32767


# ---------- BMI270 ----------
def test_bmi270_config_file_is_bosch_8_kb(config):
    assert len(config) == 8192 and config[:4] == bytes([0xC8, 0x2E, 0x00, 0x2E])


def test_init_chunks_address_in_words():
    chunks = list(bmi270.init_chunks(bytes(1024), 256))
    assert [(a0, a1) for a0, a1, _ in chunks] == [(0, 0), (0, 8), (0, 16), (0, 24)]   # 256 байт = 128 слов = 0x80
    assert list(bmi270.init_chunks(bytes(64), 34))[1][:2] == (17 & 0x0F, 17 >> 4)


@pytest.mark.parametrize("chunk", [256, 64, 8192])
def test_bmi270_loads_config_and_starts(config, chunk):
    dev = FakeBMI270(config)
    imu = bmi270.BMI270(FakeI2C(dev), config, chunk=chunk)
    assert dev.regs[0x21] == 0x01
    assert (dev.regs[0x7D], dev.regs[0x40], dev.regs[0x42], dev.regs[0x7C]) == (0x0E, 0xA8, 0xA9, 0x02)
    assert (dev.regs[0x53], dev.regs[0x58]) == (0x0A, 0x04)
    assert (imu.acc_lsb, imu.gyr_lsb) == (8192, 32.8)


def test_bmi270_reads_g_and_dps(config):
    dev = FakeBMI270(config)
    imu = bmi270.BMI270(FakeI2C(dev), config)
    dev.set_motion((0.1, -0.2, 1.0), (10.0, 0.0, -250.0))
    acc, gyr = imu.read()
    assert acc == pytest.approx((0.1, -0.2, 1.0), abs=1 / 8192)
    assert gyr == pytest.approx((10.0, 0.0, -250.0), abs=1 / 32.8)


def test_bmi270_rejects_wrong_config(config):
    bad = bytearray(config)
    bad[100] ^= 0xFF
    with pytest.raises(OSError):
        bmi270.BMI270(FakeI2C(FakeBMI270(config)), bytes(bad))
    with pytest.raises(ValueError):
        bmi270.BMI270(FakeI2C(FakeBMI270(config)), config[:100])


def test_bmi270_missing_raises(config):
    with pytest.raises(OSError):
        bmi270.BMI270(FakeI2C(), config)


# ---------- VL53L4CD ----------
def test_default_config_covers_0x2d_to_0x87():
    assert len(vl53l4cd.DEFAULT_CONFIG) == 0x87 - 0x2D + 1
    assert vl53l4cd.DEFAULT_CONFIG[0x30 - 0x2D] == 0x11             # прерывание активным 0
    assert vl53l4cd.DEFAULT_CONFIG[0x46 - 0x2D] == 0x20             # «новый замер готов»


@pytest.mark.parametrize("raw, status", [(9, 0), (0x29, 0), (23, 12), (3, 5), (4, 2), (24, 255), (12, 9)])
def test_range_status_map(raw, status):
    assert vl53l4cd.range_status(raw) == status


def test_range_config_grows_with_budget_and_checks_limits():
    a20, b20 = vl53l4cd.range_config(20, 0x64)
    a50, b50 = vl53l4cd.range_config(50, 0x64)
    decode = lambda v: (v & 0xFF) << (v >> 8)                         # младший байт × 2^старший
    assert decode(a50) > decode(a20) and decode(b50) > decode(b20)
    with pytest.raises(ValueError):
        vl53l4cd.range_config(5, 0x64)
    with pytest.raises(ValueError):
        vl53l4cd.range_config(201, 0x64)


def test_vl53l4cd_init_measure_and_new_address():
    pin = FakePin(1)
    dev = FakeVL53L4CD(pin, dist=83, status_raw=9)
    s = vl53l4cd.VL53L4CD(FakeI2C(dev))
    s.set_address(0x31)
    s.init(20)
    assert dev.addr == 0x31
    assert (0x002D, vl53l4cd.DEFAULT_CONFIG) in dev.writes
    starts = [p for reg, p in dev.writes if reg == vl53l4cd.SYSTEM_START]
    assert starts == [b"\x40", b"\x00"]                               # калибровка VHV, затем стоп
    s.start()
    assert s.ready()
    assert s.measure() == (83, 0)


def test_vl53l4cd_wrong_model_raises():
    dev = FakeVL53L4CD(FakePin(1))
    dev.mem[0x010F] = 0x00
    with pytest.raises(OSError):
        vl53l4cd.VL53L4CD(FakeI2C(dev))
