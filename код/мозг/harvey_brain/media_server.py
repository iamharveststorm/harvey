"""TCP-сервер «медиа» для головы (порт 8766): звук с её микрофонов, кадры камеры, речь для её динамика.

Формат кадров — harvey_head/media.py (protocol.media). Команды (порт 8765, HeadServer) от этого не зависят.
start()/stop() — корутины в основном цикле; остальные методы можно звать из любого потока (микрофон и динамик
мозга работают в потоках).
"""
import asyncio
import json
import queue
import time

from .protocol import media

AUDIO_MAX = 500          # кадров по 20 мс = 10 с; потребитель отстал — старое выбрасывается


class MediaServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8766):
        self.host, self.port = host, port
        self.audio: queue.Queue = queue.Queue(maxsize=AUDIO_MAX)       # pcm int16 16 кГц, кадры по 20 мс
        self.head_speaking = False
        self._frame: tuple[float, bytes] | None = None
        self._want = (False, 5.0)
        self._writer, self._loop, self._server, self._seq = None, None, None, 0

    @property
    def connected(self) -> bool:
        writer = self._writer
        return writer is not None and not writer.is_closing()

    def latest_frame(self) -> tuple[float, bytes] | None:
        """(время приёма, JPEG) последнего кадра камеры или None."""
        return self._frame

    def request_video(self, on: bool, fps: float = 5) -> None:
        """Попросить голову слать кадры камеры (или перестать). Желание помнится и повторяется при новом подключении."""
        self._want = (on, fps)
        self._send_control()

    def send_speech(self, pcm16: bytes, rate: int) -> bool:
        """Фраза для динамика головы (PCM int16 LE моно). False — головы нет."""
        data = b"".join(self._pack(kind, body) for kind, body in media.speech_frames(pcm16, rate))
        return self._send(data)

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._server = await asyncio.start_server(self._serve, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self._writer:
            self._writer.close()
        self._writer = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def _pack(self, kind: int, body: bytes) -> bytes:
        self._seq += 1
        return media.pack(kind, self._seq, body)

    def _send_control(self) -> bool:
        on, fps = self._want
        return self._send(self._pack(media.CONTROL, json.dumps({"video": on, "fps": fps}).encode()))

    def _send(self, data: bytes) -> bool:
        if not self.connected or self._loop is None:
            return False
        self._loop.call_soon_threadsafe(self._write, data)
        return True

    def _write(self, data: bytes) -> None:
        writer = self._writer
        if writer is not None and not writer.is_closing():
            writer.write(data)

    async def _serve(self, reader, writer) -> None:
        if self._writer:
            self._writer.close()                       # голова одна: новая вытесняет старую
        self._writer, self.head_speaking = writer, False
        if self._want[0]:
            self._send_control()
        frames = media.FrameReader()
        try:
            while data := await reader.read(65536):
                for kind, _seq, payload in frames.feed(data):
                    self._on_frame(kind, payload)
        except (OSError, media.MediaError):
            pass                                       # обрыв или мусор: закрываем, сервер живёт
        finally:
            if self._writer is writer:
                self._writer, self.head_speaking = None, False
            writer.close()

    def _on_frame(self, kind: int, payload: bytes) -> None:
        if kind == media.AUDIO_UP:
            self._put_audio(payload)
        elif kind == media.VIDEO_UP:
            self._frame = (time.time(), payload)
        elif kind == media.CONTROL:
            self._on_control(payload)

    def _put_audio(self, pcm: bytes) -> None:
        while True:
            try:
                self.audio.put_nowait(pcm)
                return
            except queue.Full:
                try:
                    self.audio.get_nowait()
                except queue.Empty:
                    pass

    def _on_control(self, payload: bytes) -> None:
        try:
            msg = json.loads(payload)
        except ValueError:
            return
        if isinstance(msg, dict) and "speaking" in msg:
            self.head_speaking = bool(msg["speaking"])
