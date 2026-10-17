"""Проверки драйвера шины: пакеты, контрольная сумма, разбор ответа, эхо, знаки."""
import pytest

from harvey_bench import sts


def test_packet_ping_matches_reference():
    # PING привода 1 по протоколу Feetech: FF FF 01 02 01 FB
    assert sts.make_packet(1, sts.PING) == bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB])


def test_packet_read_position():
    pkt = sts.make_packet(1, sts.READ, bytes([56, 2]))
    assert pkt[:5] == bytes([0xFF, 0xFF, 1, 4, 2])
    assert pkt[-1] == (~(1 + 4 + 2 + 56 + 2)) & 0xFF


def test_packet_rejects_bad_id():
    with pytest.raises(ValueError):
        sts.make_packet(300, sts.PING)


def _status(sid, err, data):
    body = bytes([sid, len(data) + 2, err]) + data
    return b"\xff\xff" + body + bytes([sts.checksum(body)])


def test_parse_status_finds_reply_after_garbage():
    buf = b"\x00\x13" + _status(1, 0, b"\x00\x08")
    err, data, start, end = sts.parse_status(buf, 1)
    assert (err, data, start, end) == (0, b"\x00\x08", 2, len(buf))


def test_parse_status_waits_for_incomplete_packet():
    full = _status(1, 0, b"\x34\x12")
    assert sts.parse_status(full[:-2], 1) is None


def test_parse_status_skips_wrong_checksum_and_other_id():
    bad = bytearray(_status(1, 0, b"\x01\x02"))
    bad[-1] ^= 0xFF
    other = _status(2, 0, b"\x05")
    good = _status(1, 0, b"\x07")
    err, data, _, _ = sts.parse_status(bytes(bad) + other + good, 1)
    assert data == b"\x07"


def test_echo_is_recognisable():
    pkt = sts.make_packet(1, sts.READ, bytes([56, 2]))
    reply = _status(1, 0, b"\x00\x08")
    res = sts.parse_status(pkt + reply, 1)
    assert pkt == (pkt + reply)[res[2]:res[3]]          # первым находится эхо — драйвер его отбросит
    res2 = sts.parse_status(reply, 1)
    assert res2[1] == b"\x00\x08"


@pytest.mark.parametrize("raw,bit,val", [(0x0005, 15, 5), (0x8005, 15, -5), (0x0405, 10, -5), (0x0005, 10, 5)])
def test_sign_magnitude(raw, bit, val):
    assert sts.to_signed(raw, bit) == val


def test_fake_bus_set_id_and_move():
    from harvey_bench.fake import FakeBus

    bus = FakeBus(ids=(1,), speedup=50.0)
    s = sts.Servo(bus, 1)
    assert s.model() == sts.MODEL_STS3215
    s.set_id(5)
    assert bus.ping(5) and not bus.ping(1)
    s.torque(True)
    s.move(3000)
    import time
    time.sleep(0.05)
    assert abs(s.pos() - 3000) < 5
    bus.write(sts.BROADCAST, sts.TORQUE_ENABLE, 0)
    assert bus.servos[5].mem[sts.TORQUE_ENABLE[0]] == 0


def test_state_block_read_matches_single_registers():
    from harvey_bench.fake import FakeBus

    bus = FakeBus(ids=(1,), speedup=50.0)
    s = sts.Servo(bus, 1)                                      # момент выключен — привод стоит
    st = s.state()
    assert abs(st.pos - s.pos()) <= 2
    assert st.volt == pytest.approx(12.0, abs=0.2)
    assert st.current_a > 0


def test_profiles_have_sane_norms():
    p = sts.PROFILES["sts3032"]
    assert p.vmin < p.volt < p.vmax <= 7.4                     # защита STS3032 выше 7,4 В
    assert p.stall_nm == pytest.approx(0.44, abs=0.01)
    assert not p.current_sensor


def test_set_middle_makes_position_2048():
    from harvey_bench.fake import FakeBus

    bus = FakeBus(ids=(1,), speedup=50.0, profile=sts.PROFILES["sts3032"])
    s = sts.Servo(bus, 1)
    s.set_middle()
    assert abs(s.pos() - sts.MIDDLE) <= 1


def test_leg_ik_fk_roundtrip_and_stance():
    import math
    from harvey_bench.leg import GEOM, STANCE

    r0, h0 = GEOM.stance_target()
    assert h0 == pytest.approx(-GEOM.zj, abs=1e-6)              # в стойке стопа на столе
    for dh in (-5.0, 0.0, 8.0, 15.0):
        qf, qk = GEOM.ik(r0, h0 + dh)
        r, h = GEOM.foot(math.radians(qf), math.radians(qk))
        assert (r, h) == pytest.approx((r0, h0 + dh), abs=1e-3)
    assert GEOM.ik(r0, h0) == pytest.approx(STANCE[1:], abs=1e-6)


def test_leg_calibration_mapping():
    from harvey_bench.leg import LegCal

    cal = LegCal(sign={"coxa": 1, "femur": -1, "knee": 1}, offset={"coxa": 0, "femur": 12, "knee": 0})
    for j, deg in (("coxa", 15.0), ("femur", 20.0), ("knee", -110.0)):
        assert cal.to_deg(j, cal.to_pos(j, deg)) == pytest.approx(deg, abs=sts.DEG_PER_STEP)
    assert cal.to_pos("knee", -90.0) == sts.MIDDLE                # поза «Г» — середина
