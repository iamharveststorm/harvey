"""MediaServer с настоящим MediaLink головы (импорт по пути); arecord / aplay головы — подделки."""
import asyncio
import io
import json
import queue
import struct
import time

from harvey_brain.media_server import MediaServer
from harvey_brain.protocol import media
from harvey_head.media_link import MediaLink, SpeakerStream  # noqa: E402  (путь к голове добавляет harvey_brain.protocol)


async def until(cond, seconds=3.0):
    for _ in range(int(seconds / 0.01)):
        if cond():
            return True
        await asyncio.sleep(0.01)
    return False


async def connect(server, **kw):
    link, stop = MediaLink("127.0.0.1", server.port, pause_s=0.01, **kw), asyncio.Event()
    task = asyncio.ensure_future(link.run(stop))
    assert await until(lambda: link.connected and server.connected)
    return link, stop, task


async def disconnect(stop, task):
    stop.set()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def run_with_server(scenario):
    async def main():
        server = MediaServer("127.0.0.1", 0)
        await server.start()
        try:
            await scenario(server)
        finally:
            await server.stop()

    asyncio.run(main())


def test_no_head_means_not_connected_and_speech_refused():
    async def scenario(server):
        assert not server.connected and server.latest_frame() is None and not server.head_speaking
        assert server.send_speech(b"\0\0", 16000) is False

    run_with_server(scenario)


def test_audio_from_the_head_lands_in_the_queue():
    async def scenario(server):
        link, stop, task = await connect(server)
        link.offer_audio(b"\1" * 640)
        link.offer_audio(b"\2" * 640)
        assert await until(lambda: server.audio.qsize() == 2)
        assert [server.audio.get_nowait(), server.audio.get_nowait()] == [b"\1" * 640, b"\2" * 640]
        await disconnect(stop, task)

    run_with_server(scenario)


def test_audio_queue_is_bounded_and_drops_the_oldest():
    server = MediaServer("127.0.0.1", 0)
    for i in range(server.audio.maxsize + 10):
        server._on_frame(media.AUDIO_UP, i.to_bytes(4, "little"))
    assert server.audio.qsize() == server.audio.maxsize
    assert server.audio.get_nowait() == (10).to_bytes(4, "little")


def test_video_request_reaches_the_head_and_the_frame_comes_back():
    async def scenario(server):
        link, stop, task = await connect(server)
        assert not link.video_wanted
        server.request_video(True, 5)
        assert await until(lambda: link.video_wanted and link.video_fps == 5.0)
        before = time.time()
        link.offer_video(b"\xff\xd8jpeg")
        assert await until(lambda: server.latest_frame() is not None)
        stamp, jpeg = server.latest_frame()
        assert jpeg == b"\xff\xd8jpeg" and before <= stamp <= time.time()
        server.request_video(False)
        assert await until(lambda: not link.video_wanted)
        await disconnect(stop, task)

    run_with_server(scenario)


def test_video_request_made_before_the_head_connects_is_applied_on_connect():
    async def scenario(server):
        server.request_video(True, 2)
        link, stop, task = await connect(server)
        assert await until(lambda: link.video_wanted and link.video_fps == 2.0)
        await disconnect(stop, task)

    run_with_server(scenario)


class Sink(io.BytesIO):
    def close(self):
        pass


class FakeProc:
    def __init__(self):
        self.stdin = Sink()

    def wait(self, timeout=None):
        return 0


def test_speech_reaches_the_heads_aplay_with_the_same_bytes():
    async def scenario(server):
        link, stop, task = await connect(server)
        procs, cmds = [], []

        def popen(cmd, **kw):
            cmds.append(cmd)
            procs.append(FakeProc())
            return procs[-1]

        class Mic:
            muted = False

        speaker = SpeakerStream(link, Mic(), popen=popen, tail_s=0.0, sleep=lambda s: None)
        link.on_speech = speaker.play
        speaker.start()
        pcm = bytes(range(256)) * 400                         # 102 400 байт -> несколько кадров
        assert server.send_speech(pcm, 22050) is True
        assert await until(lambda: len(procs) == 1)
        speaker.close()
        assert procs[0].stdin.getvalue() == pcm and cmds[0][-2] == "22050"
        await disconnect(stop, task)

    run_with_server(scenario)


def test_send_speech_works_from_another_thread():
    async def scenario(server):
        link, stop, task = await connect(server)
        heard = []
        link.on_speech = lambda rate, pcm: heard.append((rate, pcm))
        ok = await asyncio.get_running_loop().run_in_executor(None, server.send_speech, b"\3\0" * 10, 16000)
        assert ok and await until(lambda: heard == [(16000, b"\3\0" * 10)])
        await disconnect(stop, task)

    run_with_server(scenario)


def test_head_speaking_follows_the_heads_control_messages():
    async def scenario(server):
        link, stop, task = await connect(server)
        link.send_control({"speaking": True})
        assert await until(lambda: server.head_speaking)
        link.send_control({"speaking": False})
        assert await until(lambda: not server.head_speaking)
        link.send_control({"speaking": True})
        assert await until(lambda: server.head_speaking)
        await disconnect(stop, task)
        assert await until(lambda: not server.connected and not server.head_speaking)

    run_with_server(scenario)


def test_garbage_from_the_head_drops_the_connection_but_the_server_lives():
    async def scenario(server):
        reader, writer = await asyncio.open_connection("127.0.0.1", server.port)
        assert await until(lambda: server.connected)
        writer.write(b"GARBAGE-GARBAGE-GARBAGE")
        await writer.drain()
        assert await until(lambda: not server.connected)
        assert await reader.read() == b""
        link, stop, task = await connect(server)               # и нормальная голова подключается
        await disconnect(stop, task)

    run_with_server(scenario)


def test_cut_in_the_middle_of_a_frame_is_just_a_disconnect():
    async def scenario(server):
        _, writer = await asyncio.open_connection("127.0.0.1", server.port)
        assert await until(lambda: server.connected)
        writer.write(media.pack(media.VIDEO_UP, 1, b"x" * 100)[:50])
        await writer.drain()
        writer.close()
        assert await until(lambda: not server.connected)
        assert server.latest_frame() is None

    run_with_server(scenario)


def test_a_new_head_replaces_the_old_one_and_bad_control_is_ignored():
    async def scenario(server):
        r1, w1 = await asyncio.open_connection("127.0.0.1", server.port)
        assert await until(lambda: server.connected)
        w1.write(media.pack(media.CONTROL, 1, b"{nope"))
        w1.write(media.pack(media.CONTROL, 2, json.dumps([1]).encode()))
        await w1.drain()
        r2, w2 = await asyncio.open_connection("127.0.0.1", server.port)
        assert await r1.read() == b""                          # старую закрыли
        assert await until(lambda: server.connected)
        w2.write(media.pack(media.CONTROL, 3, b'{"speaking": true}'))
        await w2.drain()
        assert await until(lambda: server.head_speaking)
        w2.close()

    run_with_server(scenario)


def test_queue_type():
    assert isinstance(MediaServer().audio, queue.Queue)
