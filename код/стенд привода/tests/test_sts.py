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
