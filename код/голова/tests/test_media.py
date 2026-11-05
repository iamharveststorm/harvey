import struct

import pytest

from harvey_head import media
from harvey_head.media import FrameReader, MediaError, pack


def test_pack_feed_roundtrip():
    frames = FrameReader().feed(pack(media.AUDIO_UP, 7, b"abc"))
    assert frames == [(media.AUDIO_UP, 7, b"abc")]


def test_frame_cut_into_single_bytes():
    reader, got = FrameReader(), []
    for b in pack(media.VIDEO_UP, 1, b"jpeg-bytes"):
        got += reader.feed(bytes([b]))
    assert got == [(media.VIDEO_UP, 1, b"jpeg-bytes")]


def test_two_frames_in_one_chunk_and_empty_payload():
    data = pack(media.SPEECH_MORE, 1, b"xy") + pack(media.SPEECH_END, 2, b"")
    assert FrameReader().feed(data) == [(media.SPEECH_MORE, 1, b"xy"), (media.SPEECH_END, 2, b"")]


def test_bad_magic_raises():
    with pytest.raises(MediaError):
        FrameReader().feed(b"XX" + b"\0" * 9)


def test_too_long_payload_raises_before_reading_it():
    header = struct.pack("<2sBII", media.MAGIC, media.AUDIO_UP, 0, media.MAX_PAYLOAD + 1)
    with pytest.raises(MediaError):
        FrameReader().feed(header)


def test_max_payload_is_accepted():
    payload = b"\0" * media.MAX_PAYLOAD
    assert FrameReader().feed(pack(media.VIDEO_UP, 0, payload))[0][2] == payload


def test_speech_frames_split_and_join():
    pcm = bytes(range(256)) * 274  # 70 144 байта
    frames = media.speech_frames(pcm, 22050)
    assert [k for k, _ in frames] == [media.SPEECH_DOWN, media.SPEECH_MORE, media.SPEECH_MORE, media.SPEECH_END]
    assert struct.unpack("<I", frames[0][1][:4])[0] == 22050
    assert frames[0][1][4:] + frames[1][1] + frames[2][1] == pcm
    assert frames[3][1] == b""


def test_speech_frames_short_phrase_is_two_frames():
    frames = media.speech_frames(b"\1\0\2\0", 16000)
    assert [k for k, _ in frames] == [media.SPEECH_DOWN, media.SPEECH_END]


def test_stereo32_to_mono16_takes_left_channel_shifted():
    left, right = [0x12340000, -0x00010000, 0x7FFF0000], [0x55550000, 0x11110000, 0x22220000]
    raw = b"".join(struct.pack("<ii", l, r) for l, r in zip(left, right))
    assert struct.unpack("<3h", media.stereo32_to_mono16(raw)) == (0x1234, -1, 0x7FFF)


def test_stereo32_to_mono16_drops_incomplete_frame():
    raw = struct.pack("<ii", 65536, 0) + b"\1\2\3"
    assert media.stereo32_to_mono16(raw) == struct.pack("<h", 1)
