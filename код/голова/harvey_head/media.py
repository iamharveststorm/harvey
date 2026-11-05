"""Формат кадров «медиа»-соединения голова <-> ПК (TCP :8766): звук с микрофонов, кадры камеры, речь для динамика.

Кадр: заголовок "<2sBII" (магия b"HV", вид, номер, длина) и `длина` байт. Только stdlib: файл общий для головы и
мозга (мозг подключает его по пути). Подробности — docs/superpowers/plans/2026-11-05-media-link.md.
"""
from __future__ import annotations

import struct

MAGIC = b"HV"
_HEADER = struct.Struct("<2sBII")
MAX_PAYLOAD = 512 * 1024          # больше — это мусор, не кадр: соединение рвём

AUDIO_UP = 1       # голова -> ПК: PCM int16 LE моно 16 кГц (20 мс = 640 байт)
VIDEO_UP = 2       # голова -> ПК: JPEG кадра камеры
SPEECH_DOWN = 3    # ПК -> голова: начало фразы: "<I" частота + PCM int16 LE моно
SPEECH_MORE = 4    # ПК -> голова: продолжение фразы (только PCM)
SPEECH_END = 5     # ПК -> голова: конец фразы (пусто)
CONTROL = 6        # JSON UTF-8 в обе стороны: {"video": true, "fps": 5} / {"speaking": true}

AUDIO_FRAME_SAMPLES = 320          # 20 мс при 16 кГц
SPEECH_CHUNK = 32000               # байт PCM в одном кадре речи


class MediaError(Exception):
    pass


def pack(kind: int, seq: int, payload: bytes) -> bytes:
    return _HEADER.pack(MAGIC, kind, seq, len(payload)) + payload


class FrameReader:
    """Склеивает поток байт в кадры. Мусор (магия, длина) — MediaError: читатель не ждёт гигабайты."""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, int, bytes]]:
        self._buf += data
        frames = []
        while len(self._buf) >= _HEADER.size:
            magic, kind, seq, length = _HEADER.unpack_from(self._buf)
            if magic != MAGIC:
                raise MediaError("не кадр: неверная магия")
            if length > MAX_PAYLOAD:
                raise MediaError(f"кадр слишком большой: {length} байт")
            end = _HEADER.size + length
            if len(self._buf) < end:
                break
            frames.append((kind, seq, bytes(self._buf[_HEADER.size:end])))
            del self._buf[:end]
        return frames


def speech_frames(pcm: bytes, rate: int, chunk: int = SPEECH_CHUNK) -> list[tuple[int, bytes]]:
    """Фраза -> [(SPEECH_DOWN, частота + начало), (SPEECH_MORE, …)…, (SPEECH_END, b"")]."""
    pieces = [pcm[i:i + chunk] for i in range(0, len(pcm), chunk)] or [b""]
    frames = [(SPEECH_DOWN, struct.pack("<I", rate) + pieces[0])]
    frames += [(SPEECH_MORE, piece) for piece in pieces[1:]]
    return frames + [(SPEECH_END, b"")]


def stereo32_to_mono16(raw: bytes) -> bytes:
    """arecord -c 2 -f S32_LE -> моно int16: левый канал, >> 16. Неполный отсчёт в конце отбрасывается.
    ПРЕДВАРИТЕЛЬНО: какой канал INMP441 живой и какой уровень — проверить на стенде."""
    n = len(raw) // 8
    words = struct.unpack(f"<{2 * n}i", raw[:8 * n])
    return struct.pack(f"<{n}h", *(w >> 16 for w in words[0::2]))
