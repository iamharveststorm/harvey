"""Звук и картинка между головой и ПК: второе TCP-соединение (media.py), клиент с переподключением.

Вверх: звук двух INMP441 (arecord -> моно int16 16 кГц, кадры по 20 мс) и JPEG камеры (только когда ПК попросил).
Вниз: речь для динамика (aplay), фразы по очереди. Пока играет речь и 0,3 с после — микрофон молчит (полудуплекс).
Железо (arecord, aplay, камера, кодировщик JPEG) подменяется: тесты ничего настоящего не запускают.
ПРЕДВАРИТЕЛЬНО: имя устройства ALSA, живой канал INMP441 и уровни — проверить на стенде.
"""
from __future__ import annotations

import asyncio
import json
import queue
import struct
import subprocess
import threading
import time
from collections import deque

from . import media
from .links import BrainLink, backoff

AUDIO_QUEUE = 50          # кадров по 20 мс = 1 с: Wi-Fi не успевает — старое выбрасывается
VIDEO_QUEUE = 2
CONTROL_QUEUE = 20
DEFAULT_FPS = 5.0
TAIL_S = 0.3
RESTART_DELAYS = (1, 2, 5)    # пауза перед перезапуском arecord, с; дальше — последняя
HEALTHY_S = 30.0               # столько записи без сбоя — и паузы начинаются с начала
READ_BYTES = media.AUDIO_FRAME_SAMPLES * 8      # 20 мс стерео 32 бита


def play_cmd(device: str, rate: int) -> list[str]:
    return ["aplay", "-q", "-D", device, "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", str(rate), "-"]


def record_cmd(device: str, rate: int = 16000) -> list[str]:
    """Сырой поток в stdout: стерео, 32 бита — так INMP441 отдаёт данные (как audio.record_cmd)."""
    return ["arecord", "-q", "-D", device, "-t", "raw", "-c", "2", "-r", str(rate), "-f", "S32_LE"]


def jpeg_encode(frame) -> bytes:
    import cv2
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok:
        raise ValueError("не удалось закодировать кадр")
    return buf.tobytes()


class MediaLink:
    """ПК: TCP-клиент. offer_* можно звать из любого потока; речь приходит в on_speech(rate, pcm)."""

    def __init__(self, host: str, port: int, pause_s: float = 0.2):
        self.host, self.port, self.pause_s = host, port, pause_s
        self.connected, self.video_wanted, self.video_fps = False, False, DEFAULT_FPS
        self.on_speech = None
        self._audio, self._video = deque(maxlen=AUDIO_QUEUE), deque(maxlen=VIDEO_QUEUE)
        self._control = deque(maxlen=CONTROL_QUEUE)
        self._phrase: list | None = None             # [частота, bytearray PCM]
        self._seq, self._loop, self._wake = 0, None, None

    def offer_audio(self, pcm16: bytes) -> None:
        self._audio.append(pcm16)
        self._wake_up()

    def offer_video(self, jpeg: bytes) -> None:
        self._video.append(jpeg)
        self._wake_up()

    def send_control(self, msg: dict) -> None:
        self._control.append(json.dumps(msg).encode())
        self._wake_up()

    def _wake_up(self) -> None:
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._wake.set)
            except RuntimeError:        # цикл уже закрыт
                pass

    async def run(self, stop: asyncio.Event) -> None:
        self._loop, self._wake = asyncio.get_running_loop(), asyncio.Event()
        attempt = 0
        while not stop.is_set():
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
            except OSError:
                await self._sleep(stop, backoff(attempt))
                attempt += 1
                continue
            attempt = 0
            self._reset()
            self.connected = True
            try:
                await self._session(reader, writer, stop)
            finally:
                self.connected = False
                self.video_wanted = False
                writer.close()
            await self._sleep(stop, self.pause_s)

    def _reset(self) -> None:
        """Новое соединение — чистый лист: старый звук и желания ПК не нужны."""
        for q in (self._audio, self._video, self._control):
            q.clear()
        self._phrase, self.video_wanted = None, False

    async def _session(self, reader, writer, stop) -> None:
        frames = media.FrameReader()

        async def pump_out():
            while True:
                await self._wake.wait()
                self._wake.clear()
                while (data := self._next_frame()) is not None:
                    writer.write(data)
                    await writer.drain()

        sender = asyncio.ensure_future(pump_out())
        try:
            while not stop.is_set():
                data = await reader.read(65536)
                if not data:
                    return
                for kind, _seq, payload in frames.feed(data):
                    self._on_frame(kind, payload)
        except (OSError, media.MediaError):
            return                      # обрыв или мусор: закрыть и переподключиться
        finally:
            sender.cancel()

    def _next_frame(self) -> bytes | None:
        for queue_, kind in ((self._control, media.CONTROL), (self._audio, media.AUDIO_UP), (self._video, media.VIDEO_UP)):
            if queue_:
                self._seq += 1
                return media.pack(kind, self._seq, queue_.popleft())
        return None

    def _on_frame(self, kind: int, payload: bytes) -> None:
        if kind == media.CONTROL:
            self._on_control(payload)
        elif kind == media.SPEECH_DOWN and len(payload) >= 4:
            self._phrase = [struct.unpack_from("<I", payload)[0], bytearray(payload[4:])]
        elif kind == media.SPEECH_MORE and self._phrase:
            self._phrase[1] += payload
        elif kind == media.SPEECH_END and self._phrase:
            rate, data = self._phrase
            self._phrase = None
            if self.on_speech:
                self.on_speech(rate, bytes(data[:len(data) // 2 * 2]))

    def _on_control(self, payload: bytes) -> None:
        try:
            msg = json.loads(payload)
        except ValueError:
            return
        if not isinstance(msg, dict):
            return
        if "video" in msg:
            self.video_wanted = bool(msg["video"])
        fps = msg.get("fps")
        if isinstance(fps, (int, float)) and not isinstance(fps, bool):
            self.video_fps = float(fps) if fps > 0 else DEFAULT_FPS

    _sleep = staticmethod(BrainLink._wait)          # пауза, которую прерывает stop


class MicStream:
    """arecord -> моно 16 кГц -> link.offer_audio. muted — микрофон читается, но не отправляется.
    arecord завершился, а поток не закрыт — перезапуск с паузой 1, 2, 5, 5 … с (после 30 с исправной записи — снова 1 с)."""

    def __init__(self, link: MediaLink, popen=subprocess.Popen, device: str = "default", sleep=time.sleep,
                 clock=time.monotonic, log=print):
        self.link, self.popen, self.device = link, popen, device
        self._sleep, self._clock, self._log = sleep, clock, log
        self.muted, self._proc, self._stop = False, None, threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._t0 = self._clock()
        self._proc = self._launch()
        self._thread.start()

    def _launch(self):
        try:
            return self.popen(record_cmd(self.device), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except OSError as e:
            self._last_error = str(e)
            return None

    def _run(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            if self._proc is not None:
                self._read(self._proc)
                reason = f"завершился (код {self._exit_code(self._proc)})"
            else:
                reason = f"не запустился ({self._last_error})"
            if self._stop.is_set():
                return
            attempt = 0 if self._clock() - self._t0 >= HEALTHY_S else attempt
            delay = RESTART_DELAYS[min(attempt, len(RESTART_DELAYS) - 1)]
            attempt += 1
            self._log(f"микрофон: arecord {reason}, перезапуск через {delay} с")
            self._sleep(delay)
            if self._stop.is_set():
                return
            self._t0 = self._clock()
            self._proc = self._launch()

    @staticmethod
    def _exit_code(proc):
        poll = getattr(proc, "poll", None)
        code = poll() if poll else getattr(proc, "returncode", None)
        return "?" if code is None else code

    def _read(self, proc) -> None:
        while not self._stop.is_set():
            raw = proc.stdout.read(READ_BYTES)
            if len(raw) < READ_BYTES:
                return
            if not self.muted:
                self.link.offer_audio(media.stereo32_to_mono16(raw))

    def close(self) -> None:
        self._stop.set()
        if self._proc:
            self._proc.terminate()


class SpeakerStream:
    """Фразы от ПК по очереди: каждая — свой aplay. Пока говорит (и tail_s после последней) микрофон молчит."""

    def __init__(self, link: MediaLink, mic: MicStream, popen=subprocess.Popen, device: str = "default", amp=None,
                 tail_s: float = TAIL_S, sleep=time.sleep):
        self.link, self.mic, self.popen, self.device, self.amp = link, mic, popen, device, amp
        self.tail_s, self._sleep, self._q = tail_s, sleep, queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def play(self, rate: int, pcm: bytes) -> None:
        self._q.put((rate, pcm))

    def close(self) -> None:
        self._q.put(None)
        if self._thread.is_alive():
            self._thread.join(1.0)

    def _run(self) -> None:
        speaking = False
        while (job := self._q.get()) is not None:
            if not speaking:
                speaking = self._set_speaking(True)
            self._play(*job)
            if self._q.empty():
                self._sleep(self.tail_s)
                if self._q.empty():
                    speaking = self._set_speaking(False)
        if speaking:
            self._set_speaking(False)

    def _set_speaking(self, on: bool) -> bool:
        self.mic.muted = on
        if self.amp is not None:
            (self.amp.on if on else self.amp.off)()
        self.link.send_control({"speaking": on})
        return on

    def _play(self, rate: int, pcm: bytes) -> None:
        try:
            proc = self.popen(play_cmd(self.device, rate), stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            proc.stdin.write(pcm)
            proc.stdin.close()
            proc.wait()
        except OSError:
            pass                        # нет aplay или динамик отвалился: фраза пропадает, микрофон не залипает


class VideoPump:
    """Кадры камеры -> JPEG -> link.offer_video: только если ПК просил и не чаще его fps."""

    def __init__(self, link: MediaLink, get_frame, encode=jpeg_encode, clock=time.monotonic):
        self.link, self.get_frame, self.encode, self.clock = link, get_frame, encode, clock
        self._t_last: float | None = None
        self._last_frame = None

    def tick(self, now: float | None = None) -> None:
        now = self.clock() if now is None else now
        if not self.link.video_wanted:
            return
        if self._t_last is not None and now - self._t_last < 1.0 / self.link.video_fps - 1e-9:
            return
        frame = self.get_frame()
        if frame is None or frame is self._last_frame:
            return
        self._t_last, self._last_frame = now, frame
        self.link.offer_video(self.encode(frame))


class Media:
    """Всё медиа головы одним объектом: link.run(stop) — в цикле asyncio, tick(now) — из главного цикла."""

    def __init__(self, link: MediaLink, mic: MicStream, speaker: SpeakerStream, pump: VideoPump):
        self.link, self.mic, self.speaker, self.pump = link, mic, speaker, pump

    def start(self) -> None:
        self.speaker.start()
        self.mic.start()

    def tick(self, now: float) -> None:
        self.pump.tick(now)

    def close(self) -> None:
        self.mic.close()
        self.speaker.close()


def build_media(cfg, camera=None, amp=None, popen=subprocess.Popen, encode=jpeg_encode) -> Media:
    link = MediaLink(cfg.BRAIN_HOST, cfg.MEDIA_PORT)
    mic = MicStream(link, popen, cfg.ALSA_DEVICE)
    speaker = SpeakerStream(link, mic, popen, cfg.ALSA_DEVICE, amp)
    link.on_speech = speaker.play
    pump = VideoPump(link, lambda: camera.frame if camera else None, encode)
    return Media(link, mic, speaker, pump)
