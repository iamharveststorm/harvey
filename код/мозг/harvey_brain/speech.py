"""Голос: микрофон -> Silero VAD -> GigaAM v2 CTC -> текст; текст -> Piper -> динамик.

Тяжёлые библиотеки (sherpa-onnx, sounddevice) импортируются внутри классов: заглушки работают и без них.
"""
import os
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

RATE = 16000
BLOCK = 512  # окно Silero VAD
TAIL_S = 0.4  # пауза после речи Харви, прежде чем слушать снова
_ASR_DIR = "sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19"
_TTS_DIR = "vits-piper-ru_RU-dmitri-medium"


class ModelsPathError(Exception):
    pass


@dataclass(frozen=True)
class ModelPaths:
    vad: Path
    asr_model: Path
    asr_tokens: Path
    tts_model: Path
    tts_tokens: Path
    espeak_data: Path


def model_paths(models_dir) -> ModelPaths:
    models_dir = Path(models_dir)
    asr, tts = models_dir / _ASR_DIR, models_dir / _TTS_DIR
    return ModelPaths(models_dir / "silero_vad.onnx", asr / "model.int8.onnx", asr / "tokens.txt",
                      tts / "ru_RU-dmitri-medium.onnx", tts / "tokens.txt", tts / "espeak-ng-data")


def resolve_models_dir(arg, env, home) -> Path:
    """--models, иначе HARVEY_MODELS, иначе ~/.harvey/models. Путь только ASCII: espeak-ng не открывает кириллицу в Windows."""
    path = Path(arg or env.get("HARVEY_MODELS") or Path(home) / ".harvey" / "models")
    if not str(path).isascii():
        raise ModelsPathError(f"Путь к моделям «{path}» содержит не-ASCII символы, а espeak-ng в Windows не "
                              "открывает такие пути. Положи модели в путь латиницей: --models C:/Users/<имя>/.harvey/models")
    return path


def resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Линейная передискретизация (для речи 16 кГц достаточно)."""
    if src_rate == dst_rate:
        return samples
    n = int(round(len(samples) * dst_rate / src_rate))
    x_new = np.arange(n) * (src_rate / dst_rate)
    return np.interp(x_new, np.arange(len(samples)), samples).astype(np.float32)


def rechunk(blocks, size: int):
    """Режет поток блоков на куски ровно по size; None (метка сброса) пропускает как есть; хвост короче size отбрасывается."""
    buf = np.zeros(0, np.float32)
    for block in blocks:
        if block is None:
            buf = buf[:0]
            yield None
            continue
        buf = np.concatenate([buf, block])
        while len(buf) >= size:
            yield buf[:size]
            buf = buf[size:]


def segments(blocks, vad):
    """Цикл VAD: блоки (None — сбросить буфер) -> законченные куски речи (float32, 16 кГц)."""
    for block in blocks:
        if block is None:
            vad.reset()
            continue
        vad.accept_waveform(block)
        while not vad.empty():
            yield np.asarray(vad.front.samples, dtype=np.float32)
            vad.pop()


def make_vad(models_dir):
    import sherpa_onnx as so
    silero = so.SileroVadModelConfig(model=str(model_paths(models_dir).vad), threshold=0.5, min_silence_duration=0.5,
                                     min_speech_duration=0.25, window_size=BLOCK, max_speech_duration=10)
    return so.VoiceActivityDetector(so.VadModelConfig(silero_vad=silero, sample_rate=RATE), buffer_size_in_seconds=30)


class Transcriber:
    def __init__(self, models_dir):
        import sherpa_onnx as so
        p = model_paths(models_dir)
        self._rec = so.OfflineRecognizer.from_nemo_ctc(model=str(p.asr_model), tokens=str(p.asr_tokens), num_threads=2)

    def transcribe(self, samples: np.ndarray, rate: int = RATE) -> str:
        stream = self._rec.create_stream()
        stream.accept_waveform(RATE, resample(np.asarray(samples, dtype=np.float32), rate, RATE))
        self._rec.decode_stream(stream)
        return stream.result.text.strip()


def input_rate(sd, device) -> int:
    """16 кГц, если устройство умеет; иначе его собственная частота."""
    try:
        sd.check_input_settings(device=device, channels=1, dtype="float32", samplerate=RATE)
        return RATE
    except Exception:
        return int(sd.query_devices(device, "input")["default_samplerate"])


def queue_blocks(q, stop, rate):
    """Блоки из очереди (None — метка сброса) в 16 кГц, пока не поднят stop."""
    while not stop.is_set():
        try:
            block = q.get(timeout=0.2)
        except queue.Empty:
            continue
        yield block if block is None else resample(block, rate, RATE)


def texts(blocks, vad, asr):
    """Блоки 16 кГц (None — сброс) -> VAD -> распознавание -> непустые фразы."""
    for seg in segments(blocks, vad):
        text = asr.transcribe(seg, RATE)
        if text:
            yield text


class MicListener:
    """Микрофон -> VAD -> распознавание. utterances() блокирует; pause()/resume() — для полудуплекса."""

    def __init__(self, models_dir, device=None, vad=None, asr=None):
        self.device = device
        self._vad, self._asr = vad or make_vad(models_dir), asr or Transcriber(models_dir)
        self._q: queue.Queue = queue.Queue()
        self._paused, self._stop = False, threading.Event()

    def pause(self):
        self._paused = True

    def resume(self):
        self._q.put(None)  # метка: сбросить VAD до новых блоков
        self._paused = False

    def close(self):
        self._stop.set()

    def _callback(self, indata, frames, time_info, status):
        if not self._paused:
            self._q.put(indata[:, 0].copy())

    def utterances(self, sd=None):
        if sd is None:
            import sounddevice as sd
        rate = input_rate(sd, self.device)
        with sd.InputStream(samplerate=rate, device=self.device, channels=1, dtype="float32",
                            blocksize=int(round(BLOCK * rate / RATE)), callback=self._callback):
            yield from texts(rechunk(queue_blocks(self._q, self._stop, rate), BLOCK), self._vad, self._asr)


class RemoteMicListener:
    """Микрофоны головы -> VAD -> распознавание: блоки берутся из MediaServer.audio (int16 16 кГц, кадры по 20 мс).
    Пока голова говорит, её звук отбрасывается; когда замолчала — VAD сбрасывается (метка None)."""

    def __init__(self, media, models_dir, vad=None, asr=None):
        self._media = media
        self._vad, self._asr = vad or make_vad(models_dir), asr or Transcriber(models_dir)
        self._stop = threading.Event()

    def close(self):
        self._stop.set()

    def _blocks(self):
        was_speaking = False
        while not self._stop.is_set():
            try:
                pcm = self._media.audio.get(timeout=0.2)
            except queue.Empty:
                pcm = None
            if self._media.head_speaking:
                was_speaking = True
                continue
            if was_speaking:
                was_speaking = False
                yield None
            if pcm:
                yield np.frombuffer(pcm, "<i2").astype(np.float32) / 32768.0

    def utterances(self):
        yield from texts(rechunk(self._blocks(), BLOCK), self._vad, self._asr)


class PiperSpeaker:
    def __init__(self, models_dir, noise_scale: float = 0.667, noise_scale_w: float = 0.8):
        import sherpa_onnx as so
        p = model_paths(models_dir)
        os.environ["ESPEAK_DATA_PATH"] = str(p.espeak_data)
        vits = so.OfflineTtsVitsModelConfig(model=str(p.tts_model), tokens=str(p.tts_tokens), data_dir=str(p.espeak_data),
                                         noise_scale=noise_scale, noise_scale_w=noise_scale_w)
        self._tts = so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(vits=vits, num_threads=2)))

    def synth(self, text: str):
        audio = self._tts.generate(text, sid=0, speed=1.0)
        return np.asarray(audio.samples, dtype=np.float32), audio.sample_rate

    def say(self, text: str) -> None:
        import sounddevice as sd
        samples, rate = self.synth(text)
        sd.play(samples, rate)
        sd.wait()

    def close(self):
        import sounddevice as sd
        sd.stop()


class RemoteSpeaker:
    """Голос Piper -> динамик головы (MediaServer.send_speech). Полудуплекс делает сама голова."""

    def __init__(self, media, piper):
        self._media, self._piper = media, piper

    def say(self, text: str) -> None:
        samples, rate = self._piper.synth(text)
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        self._media.send_speech(pcm, rate)

    def close(self):
        pass


class HalfDuplexSpeaker:
    """Пока Харви говорит, слушатель на паузе; после речи ещё tail_s, затем VAD сбрасывается и слух возвращается."""

    def __init__(self, speaker, listener, tail_s: float = TAIL_S, sleep=time.sleep):
        self.speaker, self.listener, self.tail_s, self._sleep = speaker, listener, tail_s, sleep

    def say(self, text: str) -> None:
        self.listener.pause()
        try:
            self.speaker.say(text)
            self._sleep(self.tail_s)
        finally:
            self.listener.resume()

    def close(self):
        getattr(self.speaker, "close", lambda: None)()


class ListListener:
    def __init__(self, lines):
        self._lines = list(lines)

    def utterances(self):
        yield from self._lines

    def pause(self):
        pass

    def resume(self):
        pass

    def close(self):
        pass


class PrintSpeaker:
    def __init__(self, out=print):
        self._out = out

    def say(self, text: str) -> None:
        self._out(text)

    def close(self):
        pass
