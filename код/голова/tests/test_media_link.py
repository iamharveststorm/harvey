"""Медиа-связь головы с поддельным ПК (настоящий asyncio-сервер на localhost); arecord / aplay / камера — подделки."""
import asyncio
import io
import json
import struct
import threading

from harvey_head import media
from harvey_head.media import FrameReader, pack
from harvey_head.media_link import MediaLink, MicStream, SpeakerStream, VideoPump, build_media, play_cmd, record_cmd


async def until(cond, seconds=3.0):
    for _ in range(int(seconds / 0.01)):
        if cond():
            return True
        await asyncio.sleep(0.01)
    return False


class FakePC:
    """ПК: принимает соединения головы, собирает кадры, умеет слать кадры и рвать связь."""

    def __init__(self):
        self.frames, self.writers, self.connections = [], [], 0

    async def start(self):
        self._server = await asyncio.start_server(self._serve, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def _serve(self, reader, writer):
        self.connections += 1
        self.writers.append(writer)
        frames = FrameReader()
        while data := await reader.read(65536):
            self.frames += frames.feed(data)

    def of(self, kind):
        return [p for k, _, p in self.frames if k == kind]

    def controls(self):
        return [json.loads(p) for p in self.of(media.CONTROL)]

    def send(self, data):
        self.writers[-1].write(data)

    def control(self, msg):
        self.send(pack(media.CONTROL, 0, json.dumps(msg).encode()))

    async def stop(self):
        for w in self.writers:
            w.close()
        self._server.close()


def with_link(scenario):
    async def main():
        pc = FakePC()
        await pc.start()
        link, stop = MediaLink("127.0.0.1", pc.port, pause_s=0.01), asyncio.Event()
        task = asyncio.ensure_future(link.run(stop))
        try:
            assert await until(lambda: link.connected)
            await scenario(pc, link)
        finally:
            stop.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await pc.stop()

    asyncio.run(main())


class Sink(io.BytesIO):
    """stdin поддельного aplay: байты остаются доступны после close()."""
    def close(self):
        pass


class FakeProc:
    def __init__(self, log, stdout=b"", gate=None):
        self.log, self.stdin, self.stdout, self.gate = log, Sink(), io.BytesIO(stdout), gate
        self.terminated = False

    def wait(self, timeout=None):
        if self.gate:
            self.gate.wait(3)
        self.log.append("end")
        return 0

    def terminate(self):
        self.terminated = True


def fake_popen(log, stdout=b"", gate=None):
    procs = []

    def popen(cmd, **kw):
        log.append("start")
        procs.append(FakeProc(log, stdout, gate))
        procs[-1].cmd = cmd
        return procs[-1]

    popen.procs = procs
    return popen


def test_commands():
    assert play_cmd("hw:1", 22050) == ["aplay", "-q", "-D", "hw:1", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", "22050", "-"]
    cmd = record_cmd("hw:1")
    assert cmd[:2] == ["arecord", "-q"] and "S32_LE" in cmd and cmd[cmd.index("-c") + 1] == "2" and "hw:1" in cmd


# --- аудио вверх -------------------------------------------------------------------------------------------------

def test_mic_audio_arrives_in_640_byte_frames():
    chunks = [struct.pack("<ii", (i + 1) << 16, 0) * 320 for i in range(3)]      # три блока по 20 мс стерео-32

    async def scenario(pc, link):
        mic = MicStream(link, popen=fake_popen([], b"".join(chunks)))
        mic.start()
        assert await until(lambda: len(pc.of(media.AUDIO_UP)) == 3)
        assert [len(p) for p in pc.of(media.AUDIO_UP)] == [640] * 3
        assert pc.of(media.AUDIO_UP)[2] == struct.pack("<h", 3) * 320
        mic.close()

    with_link(scenario)


def test_muted_mic_sends_nothing_but_keeps_reading():
    async def scenario(pc, link):
        popen = fake_popen([], struct.pack("<ii", 65536, 0) * 640)
        mic = MicStream(link, popen=popen)
        mic.muted = True
        mic.start()
        assert await until(lambda: popen.procs and popen.procs[0].stdout.tell() == 5120)
        await asyncio.sleep(0.1)
        assert pc.of(media.AUDIO_UP) == []

    with_link(scenario)


def test_audio_queue_keeps_only_the_last_50_frames():
    link = MediaLink("127.0.0.1", 1)
    for i in range(80):
        link.offer_audio(bytes([i]) * 640)
    queued = list(link._audio)
    assert len(queued) == 50 and queued[0][0] == 30 and queued[-1][0] == 79


def test_video_queue_keeps_only_the_last_2_frames():
    link = MediaLink("127.0.0.1", 1)
    for i in range(5):
        link.offer_video(bytes([i]))
    assert list(link._video) == [b"\x03", b"\x04"]


# --- видео ------------------------------------------------------------------------------------------------------

def test_video_is_off_until_the_pc_asks_and_then_follows_fps():
    async def scenario(pc, link):
        assert not link.video_wanted
        frames, now = [object(), object(), object(), object(), object()], [0.0]
        pump = VideoPump(link, get_frame=lambda: frames.pop(0), encode=lambda f: b"jpeg", clock=lambda: now[0])
        pump.tick()
        await asyncio.sleep(0.05)
        assert pc.of(media.VIDEO_UP) == []                      # ПК не просил — не шлёт
        pc.control({"video": True, "fps": 5})
        assert await until(lambda: link.video_wanted)
        assert link.video_fps == 5.0
        for now[0] in (1.0, 1.05, 1.1, 1.21):                   # 5 кадров/с: шлётся 1.0 и 1.21
            pump.tick()
        assert await until(lambda: len(pc.of(media.VIDEO_UP)) == 2)
        assert pc.of(media.VIDEO_UP) == [b"jpeg", b"jpeg"]

    with_link(scenario)


def test_video_pump_skips_a_repeated_or_missing_frame():
    link, sent, now = MediaLink("h", 1), [], [0.0]
    link.video_wanted = True
    frame = object()
    seq = iter([None, frame, frame])
    pump = VideoPump(link, get_frame=lambda: next(seq), encode=lambda f: b"j", clock=lambda: now[0])
    link.offer_video = sent.append
    for now[0] in (0.0, 1.0, 2.0):
        pump.tick()
    assert sent == [b"j"]


def test_video_off_again_clears_the_flag():
    async def scenario(pc, link):
        pc.control({"video": True, "fps": 5})
        assert await until(lambda: link.video_wanted)
        pc.control({"video": False})
        assert await until(lambda: not link.video_wanted)

    with_link(scenario)


def test_bad_control_values_are_ignored():
    async def scenario(pc, link):
        pc.control({"video": True, "fps": -3})
        assert await until(lambda: link.video_wanted)
        assert link.video_fps == 5.0
        pc.send(pack(media.CONTROL, 0, b"{not json"))
        pc.control({"video": True, "fps": 2})
        assert await until(lambda: link.video_fps == 2.0)

    with_link(scenario)


# --- речь вниз --------------------------------------------------------------------------------------------------

def pcm(n, fill):
    return bytes([fill]) * n


def test_two_phrases_play_one_after_the_other_with_same_bytes():
    async def scenario(pc, link):
        log, mic = [], MicStream(link, popen=fake_popen([]))
        popen = fake_popen(log)
        speaker = SpeakerStream(link, mic, popen=popen, tail_s=0.0, sleep=lambda s: None)
        link.on_speech = speaker.play
        speaker.start()
        for fill, rate in ((1, 22050), (2, 16000)):
            for kind, body in media.speech_frames(pcm(70000, fill), rate):
                pc.send(pack(kind, 0, body))
        assert await until(lambda: len(popen.procs) == 2 and log.count("end") == 2)
        assert log == ["start", "end", "start", "end"]
        assert [p.stdin.getvalue() for p in popen.procs] == [pcm(70000, 1), pcm(70000, 2)]
        assert popen.procs[0].cmd[-2] == "22050" and popen.procs[1].cmd[-2] == "16000"
        speaker.close()

    with_link(scenario)


def test_mic_is_muted_while_speaking_and_pc_is_told():
    async def scenario(pc, link):
        gate, log = threading.Event(), []
        mic = MicStream(link, popen=fake_popen([]))
        popen, slept = fake_popen(log, gate=gate), []
        speaker = SpeakerStream(link, mic, popen=popen, tail_s=0.3, sleep=slept.append)
        speaker.start()
        speaker.play(16000, pcm(640, 1))
        assert await until(lambda: mic.muted)
        assert await until(lambda: {"speaking": True} in pc.controls())
        gate.set()
        assert await until(lambda: not mic.muted)
        assert slept == [0.3]
        assert await until(lambda: pc.controls()[-1] == {"speaking": False})
        speaker.close()

    with_link(scenario)


def test_queued_phrases_keep_the_mic_muted_between_them():
    async def scenario(pc, link):
        mic, log = MicStream(link, popen=fake_popen([])), []
        states = []
        popen = fake_popen(log)
        speaker = SpeakerStream(link, mic, popen=popen, tail_s=0.3, sleep=lambda s: states.append(mic.muted))
        speaker.play(16000, b"\1\0")
        speaker.play(16000, b"\2\0")
        speaker.start()
        assert await until(lambda: len(popen.procs) == 2 and not mic.muted)
        assert states == [True]                                  # пауза-хвост только после последней фразы
        speaker.close()

    with_link(scenario)


def test_failed_aplay_does_not_leave_the_mic_muted():
    async def scenario(pc, link):
        mic, calls = MicStream(link, popen=fake_popen([])), []

        def broken(cmd, **kw):
            calls.append(cmd)
            raise OSError("нет aplay")

        speaker = SpeakerStream(link, mic, popen=broken, tail_s=0.0, sleep=lambda s: None)
        speaker.start()
        speaker.play(16000, b"\1\0")
        assert await until(lambda: len(calls) == 1 and not mic.muted)
        speaker.play(16000, b"\1\0")
        assert await until(lambda: len(calls) == 2)
        speaker.close()

    with_link(scenario)


def test_speech_without_start_is_ignored_and_new_start_drops_the_unfinished_phrase():
    link, heard = MediaLink("h", 1), []
    link.on_speech = lambda rate, data: heard.append((rate, data))
    link._on_frame(media.SPEECH_MORE, b"zz")
    link._on_frame(media.SPEECH_END, b"")
    link._on_frame(media.SPEECH_DOWN, struct.pack("<I", 8000) + b"\1\0")
    link._on_frame(media.SPEECH_DOWN, struct.pack("<I", 16000) + b"\2\0")
    link._on_frame(media.SPEECH_MORE, b"\3\0")
    link._on_frame(media.SPEECH_END, b"")
    assert heard == [(16000, b"\2\0\3\0")]


# --- обрывы и мусор ---------------------------------------------------------------------------------------------

def test_cut_in_the_middle_of_a_frame_reconnects():
    async def scenario(pc, link):
        pc.send(pack(media.CONTROL, 0, b'{"video": true}')[:7])
        pc.writers[-1].close()
        assert await until(lambda: pc.connections == 2 and link.connected)
        assert not link.video_wanted
        link.offer_audio(b"a" * 640)
        assert await until(lambda: pc.of(media.AUDIO_UP) == [b"a" * 640])

    with_link(scenario)


def test_garbage_closes_the_connection_and_it_comes_back():
    async def scenario(pc, link):
        pc.send(b"GARBAGE-GARBAGE")
        assert await until(lambda: pc.connections == 2 and link.connected)

    with_link(scenario)


def test_video_wish_does_not_survive_a_reconnect():
    async def scenario(pc, link):
        pc.control({"video": True, "fps": 5})
        assert await until(lambda: link.video_wanted)
        pc.writers[-1].close()
        assert await until(lambda: pc.connections == 2 and link.connected)
        assert not link.video_wanted

    with_link(scenario)


# --- сборка -----------------------------------------------------------------------------------------------------

class Cfg:
    ALSA_DEVICE, BRAIN_HOST, MEDIA_PORT = "hw:9", "127.0.0.1", 1


def test_build_media_wires_mic_speaker_and_pump_and_closes():
    log = []
    popen = fake_popen(log, struct.pack("<ii", 65536, 0) * 320)
    amp_calls = []

    class Amp:
        def on(self):
            amp_calls.append("on")

        def off(self):
            amp_calls.append("off")

    class Cam:
        frame = "frame"

    m = build_media(Cfg, Cam(), Amp(), popen=popen, encode=lambda f: b"jpg")
    assert m.link.port == 1 and m.link.host == "127.0.0.1"
    m.start()
    assert popen.procs[0].cmd[:2] == ["arecord", "-q"] and "hw:9" in popen.procs[0].cmd
    m.link.video_wanted, m.link.video_fps = True, 5.0
    m.tick(10.0)
    assert list(m.link._video) == [b"jpg"]
    m.speaker.play(16000, b"\1\0")
    for _ in range(300):
        if "end" in log:
            break
        threading.Event().wait(0.01)
    assert amp_calls[:1] == ["on"] and "end" in log
    m.close()
    assert popen.procs[0].terminated


# --- перезапуск arecord -------------------------------------------------------------------------------------------

class MicRig:
    """MicStream с подставными popen, sleep, clock и журналом: каждый запуск arecord сразу даёт EOF."""

    def __init__(self, fails_with_oserror=0):
        self.popens, self.delays, self.logs, self.now = [], [], [], [0.0]
        self.mic, self.done, self.oserrors = None, threading.Event(), fails_with_oserror

    def popen(self, cmd, **kw):
        if self.oserrors:
            self.oserrors -= 1
            self.popens.append(None)
            raise OSError("нет arecord")
        proc = FakeProc([])
        proc.returncode = 3
        proc.poll = lambda: 3
        self.popens.append(proc)
        return proc

    def sleep(self, seconds):
        self.delays.append(seconds)
        self.now[0] += seconds
        if len(self.delays) >= self.stop_after:
            self.mic.close()
            self.done.set()

    def run(self, stop_after, **kw):
        self.stop_after = stop_after
        self.mic = MicStream(MediaLink("h", 1), popen=self.popen, sleep=self.sleep, clock=lambda: self.now[0],
                             log=self.logs.append, **kw)
        self.mic.start()
        assert self.done.wait(3)
        self.mic._thread.join(1)
        return self


def test_mic_restarts_arecord_after_eof_with_growing_backoff():
    rig = MicRig().run(stop_after=4)
    assert rig.delays == [1, 2, 5, 5]
    assert len([p for p in rig.popens]) == 4                    # closed during the 4th backoff: no 5th Popen
    assert len(rig.logs) == 4 and rig.logs[0] == "микрофон: arecord завершился (код 3), перезапуск через 1 с"
    assert rig.logs[2].endswith("через 5 с")


def test_mic_close_during_backoff_starts_no_new_arecord():
    rig = MicRig().run(stop_after=1)
    assert rig.delays == [1] and len(rig.popens) == 1


def test_mic_backoff_resets_after_30_seconds_of_healthy_capture():
    rig = MicRig()
    base = rig.popen

    def popen(cmd, **kw):
        proc = base(cmd, **kw)
        if len(rig.popens) == 3:                                # третий запуск проработал 31 с
            rig.now[0] += 31
        return proc

    rig.popen = popen
    rig.run(stop_after=4)
    assert rig.delays == [1, 2, 1, 2]


def test_mic_popen_failure_is_retried_with_backoff():
    rig = MicRig(fails_with_oserror=2)
    rig.stop_after = 3
    rig.mic = MicStream(MediaLink("h", 1), popen=rig.popen, sleep=rig.sleep, clock=lambda: rig.now[0], log=rig.logs.append)
    try:
        rig.mic.start()
    except OSError:
        raise AssertionError("start() не должен падать, если arecord не запустился")
    assert rig.done.wait(3)
    rig.mic._thread.join(1)
    assert rig.delays == [1, 2, 5] and "нет arecord" in rig.logs[0]
