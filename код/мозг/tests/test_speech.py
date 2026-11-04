import os
from pathlib import Path

import numpy as np
import pytest

from harvey_brain.commands import quick_reply
from harvey_brain.dialog import Dialog
from harvey_brain.reply import Reply
from harvey_brain.speech import (
    HalfDuplexSpeaker, ListListener, ModelsPathError, PrintSpeaker, model_paths, rechunk,
    resample, resolve_models_dir, segments, input_rate,
)
from harvey_brain.wake import split_wake


class NoLLM:
    def ask(self, text):
        return Reply("Я краб.", "happy")


def test_list_listener_and_print_speaker_through_dialog():
    dialog, speaker = Dialog(NoLLM()), PrintSpeaker(out=lambda s: spoken.append(s))
    spoken = []
    for i, text in enumerate(ListListener(["привет", "Харви, кто ты?"]).utterances()):
        reply = dialog.on_text(text, float(i))
        if reply:
            speaker.say(reply.say)
    assert spoken == ["Я краб."]


def test_resample_length_and_endpoints():
    x = np.linspace(0, 1, 441, dtype=np.float32)
    y = resample(x, 44100, 16000)
    assert y.dtype == np.float32 and len(y) == 160
    assert y[0] == pytest.approx(0.0) and y[-1] == pytest.approx(x[int(159 * 441 / 160)], abs=0.01)


def test_resample_same_rate_is_identity():
    x = np.arange(5, dtype=np.float32)
    assert resample(x, 16000, 16000) is x


def test_rechunk_exact_sizes_and_remainder_dropped():
    blocks = [np.arange(300, dtype=np.float32), np.arange(300, 700, dtype=np.float32)]
    out = list(rechunk(blocks, 512))
    assert [len(c) for c in out] == [512] and out[0][-1] == 511


def test_rechunk_passes_markers():
    marker = object()
    out = list(rechunk([np.zeros(600, np.float32), None, np.zeros(10, np.float32)], 512))
    assert out[0].shape == (512,) and out[1] is None and len(out) == 2


def test_resolve_models_dir_priority(tmp_path):
    assert resolve_models_dir("C:/x", {"HARVEY_MODELS": "C:/y"}, tmp_path) == Path("C:/x")
    assert resolve_models_dir(None, {"HARVEY_MODELS": "C:/y"}, tmp_path) == Path("C:/y")
    assert resolve_models_dir(None, {}, tmp_path) == tmp_path / ".harvey" / "models"


def test_non_ascii_models_dir_is_refused():
    with pytest.raises(ModelsPathError, match="espeak"):
        resolve_models_dir("C:/Users/Харви/models", {}, Path("."))


def test_model_paths_layout():
    p = model_paths(Path("M"))
    assert p.vad == Path("M/silero_vad.onnx")
    assert p.asr_model.name == "model.int8.onnx" and p.asr_tokens.name == "tokens.txt"
    assert p.tts_model.name == "ru_RU-dmitri-medium.onnx"
    assert p.espeak_data == Path("M/vits-piper-ru_RU-dmitri-medium/espeak-ng-data")


class FakeSD:
    def __init__(self, ok_16k, default=48000):
        self.ok_16k, self.default = ok_16k, default

    def check_input_settings(self, device=None, channels=None, dtype=None, samplerate=None):
        if samplerate == 16000 and not self.ok_16k:
            raise ValueError("unsupported")

    def query_devices(self, device=None, kind=None):
        return {"default_samplerate": self.default}


def test_input_rate_prefers_16k_else_device_default():
    assert input_rate(FakeSD(True), None) == 16000
    assert input_rate(FakeSD(False, 44100.0), None) == 44100


class FakeVAD:
    def __init__(self):
        self.fed, self.resets, self.queue = [], 0, []

    def accept_waveform(self, block):
        self.fed.append(len(block))
        if len(self.fed) == 3:
            self.queue.append(np.ones(3, np.float32))

    def empty(self):
        return not self.queue

    @property
    def front(self):
        return type("S", (), {"samples": self.queue[0]})()

    def pop(self):
        self.queue.pop(0)

    def reset(self):
        self.resets += 1


def test_segments_resets_on_marker_and_yields_finished():
    vad = FakeVAD()
    blocks = [np.zeros(512, np.float32)] * 2 + [None] + [np.zeros(512, np.float32)] * 2
    out = list(segments(blocks, vad))
    assert vad.resets == 1 and len(out) == 1 and out[0].tolist() == [1, 1, 1]


class Log:
    def __init__(self):
        self.events = []

    def pause(self):
        self.events.append("pause")

    def resume(self):
        self.events.append("resume")


class Voice:
    def __init__(self, log):
        self.log = log

    def say(self, text):
        self.log.events.append(f"say:{text}")


def test_half_duplex_pauses_waits_tail_then_resumes():
    log, naps = Log(), []
    spk = HalfDuplexSpeaker(Voice(log), log, tail_s=0.4, sleep=naps.append)
    spk.say("привет")
    assert log.events == ["pause", "say:привет", "resume"] and naps == [0.4]


def test_half_duplex_resumes_even_if_playback_fails():
    log = Log()

    class Broken:
        def say(self, text):
            raise RuntimeError("no device")

    spk = HalfDuplexSpeaker(Broken(), log, tail_s=0, sleep=lambda s: None)
    with pytest.raises(RuntimeError):
        spk.say("x")
    assert log.events == ["pause", "resume"]


MODELS = resolve_models_dir(None, os.environ, Path.home())
needs_models = pytest.mark.skipif(not (MODELS / "silero_vad.onnx").exists(), reason="нет моделей речи")


@pytest.fixture(scope="module")
def phrase():
    from harvey_brain.speech import PiperSpeaker
    return PiperSpeaker(MODELS, noise_scale=0.0, noise_scale_w=0.0).synth("Харви, иди домой")


@pytest.fixture(scope="module")
def transcriber():
    from harvey_brain.speech import Transcriber
    return Transcriber(MODELS)


@needs_models
def test_synth_then_transcribe_gives_home_command(phrase, transcriber):
    samples, rate = phrase
    assert samples.dtype == np.float32 and rate > 0
    text = transcriber.transcribe(samples, rate)
    woke, rest = split_wake(text)
    assert woke and quick_reply(rest).goal == "home"


@needs_models
def test_vad_path_gives_exactly_one_utterance(phrase, transcriber):
    from harvey_brain.speech import make_vad
    samples, rate = phrase
    s16 = resample(samples, rate, 16000)
    silence = np.zeros(16000, np.float32)
    stream = np.concatenate([silence, s16, silence])
    blocks = (stream[i:i + 512] for i in range(0, len(stream) - 511, 512))
    found = list(segments(blocks, make_vad(MODELS)))
    assert len(found) == 1
    woke, rest = split_wake(transcriber.transcribe(found[0], 16000))
    assert woke and quick_reply(rest).goal == "home"


@needs_models
def test_deterministic_synth_with_zero_noise():
    from harvey_brain.speech import PiperSpeaker
    spk = PiperSpeaker(MODELS, noise_scale=0.0, noise_scale_w=0.0)
    a, _ = spk.synth("Харви, иди домой")
    b, _ = spk.synth("Харви, иди домой")
    assert np.array_equal(a, b)


def test_queue_blocks_passes_marker_resamples_and_stops():
    import queue
    import threading
    from harvey_brain.speech import queue_blocks
    q, stop = queue.Queue(), threading.Event()
    q.put(np.zeros(64, np.float32))
    q.put(None)
    gen = queue_blocks(q, stop, 32000)
    assert len(next(gen)) == 32 and next(gen) is None
    stop.set()
    assert list(gen) == []


class FakeStream:
    def __init__(self, callback, blocks):
        self.callback, self.blocks = callback, blocks

    def __enter__(self):
        for b in self.blocks:
            self.callback(b.reshape(-1, 1), len(b), None, None)
        return self

    def __exit__(self, *a):
        return False


class FakeMicSD(FakeSD):
    def __init__(self, blocks, **kw):
        super().__init__(True, **kw)
        self.blocks, self.opened = blocks, None

    def InputStream(self, **kw):
        self.opened = kw
        return FakeStream(kw["callback"], self.blocks)


class FakeASR:
    def transcribe(self, samples, rate):
        return "текст"


def test_mic_listener_yields_text_for_vad_segment_and_stops_on_close():
    from harvey_brain.speech import MicListener
    sd = FakeMicSD([np.zeros(512, np.float32)] * 3)
    mic = MicListener("ignored", vad=FakeVAD(), asr=FakeASR())
    it = mic.utterances(sd=sd)
    assert next(it) == "текст"
    assert sd.opened["samplerate"] == 16000 and sd.opened["blocksize"] == 512 and sd.opened["channels"] == 1
    mic.close()
    assert list(it) == []


def test_mic_listener_drops_blocks_while_paused_and_marks_resume():
    from harvey_brain.speech import MicListener
    mic = MicListener("ignored", vad=FakeVAD(), asr=FakeASR())
    mic.pause()
    mic._callback(np.zeros((512, 1), np.float32), 512, None, None)
    assert mic._q.empty()
    mic.resume()
    assert mic._q.get_nowait() is None
    mic._callback(np.zeros((512, 1), np.float32), 512, None, None)
    assert not mic._q.empty()


def test_mic_listener_skips_empty_text():
    from harvey_brain.speech import MicListener

    class Silent:
        def transcribe(self, samples, rate):
            return ""

    sd = FakeMicSD([np.zeros(512, np.float32)] * 3)
    mic = MicListener("ignored", vad=FakeVAD(), asr=Silent())
    it = mic.utterances(sd=sd)
    import threading
    threading.Timer(0.5, mic.close).start()
    assert list(it) == []
