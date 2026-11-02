"""Голова целиком на имитации и связь: события спинного мозга → глаза, касания, команды ПК, переподключение."""
import asyncio

import pytest

from harvey_head.head import Head
from harvey_head.links import BrainLink, SpineLink, backoff
from harvey_head.protocol import encode


class Spine:
    def __init__(self):
        self.queue, self.sent = [], []

    def poll(self, now):
        out, self.queue = self.queue, []
        return out

    def send(self, msg):
        self.sent.append(msg)
        return True


class Brain:
    def __init__(self):
        self.out = []

    def offer(self, msg):
        self.out.append(msg)


class Display:
    def __init__(self):
        self.frames = 0

    def show(self, data):
        assert len(data) == 51200
        self.frames += 1


def head():
    sp, br = Spine(), Brain()
    h = Head(sp, {"left": Display(), "right": Display()}, br, now=0.0, seed=1)
    return h, sp, br


def test_lifted_by_spine_makes_surprised_eyes_and_tells_brain():
    h, sp, br = head()
    sp.queue = [{"t": "ev", "ev": "lifted"}]
    assert h.tick(0.1)["expression"] == "surprised"
    assert br.out == [{"t": "ev", "ev": "lifted", "info": None, "from": "spine"}]
    assert h.eyes["left"].frames == 1 and h.eyes["right"].frames == 1


def test_stroke_on_lid_makes_happy():
    h, _, br = head()
    for pad, t in ((0, 0.0), (1, 0.2), (2, 0.4)):
        h.on_touch(pad, True, t)
    assert h.tick(0.5)["expression"] == "happy" and {"t": "ev", "ev": "pet", "from": "touch"} in br.out


def test_hold_from_touch_tick():
    h, _, _ = head()
    h.on_touch(1, True, 0.0)
    assert h.tick(1.6)["expression"] == "love"


def test_telemetry_to_brain_is_throttled_and_undock_on_discharge():
    h, sp, br = head()
    h.mood.event("docked", 0)
    for k in range(10):
        sp.queue = [{"t": "tel", "bat": [7.9, -1.2]}]
        h.tick(0.05 * (k + 1))
    assert len([m for m in br.out if m["t"] == "tel"]) == 2 and h.mood.docked   # 5 раз в секунду
    sp.queue = [{"t": "tel", "bat": [7.9, 0.4]}]
    h.tick(1.0)
    assert not h.mood.docked


def test_brain_commands():
    h, sp, _ = head()
    h.on_brain({"t": "emote", "name": "love", "s": 1}, 0.0)
    assert h.tick(0.5)["expression"] == "love"
    h.on_brain({"t": "look", "x": 0.5, "y": 0}, 0.6)
    h.on_brain({"t": "j", "v": [0, 0, 0], "q": {"11": 2048}}, 0.6)
    h.on_brain({"t": "relax"}, 0.6)
    assert sp.sent == [{"t": "j", "v": [0, 0, 0], "q": {"11": 2048}}, {"t": "relax"}]
    assert h.anim.gaze == (0.5, 0.0)


def test_play_needs_audio():
    played = []
    h = Head(Spine(), {}, None, audio=type("A", (), {"play": lambda s, p: played.append(p)})(), seed=1)
    h.on_brain({"t": "play", "path": "/tmp/hi.wav"}, 0)
    assert played == ["/tmp/hi.wav"]
    Head(Spine(), {}, None, seed=1).on_brain({"t": "play", "path": "x"}, 0)    # без звука — молча


# ---------- связь с RP2350 ----------
class Port:
    def __init__(self, data=b"", fail_read=False):
        self.data, self.written, self.fail_read = data, b"", fail_read

    @property
    def in_waiting(self):
        return len(self.data)

    def read(self, n):
        if self.fail_read:
            raise OSError("USB отключён")
        out, self.data = self.data[:n], self.data[n:]
        return out

    def write(self, b):
        self.written += b


def test_spine_link_opens_says_hello_and_reads_lines():
    port = Port(encode({"t": "tel", "bat": [7.4, 0.5]}))
    link = SpineLink(lambda: port)
    assert link.poll(0) == [{"t": "tel", "bat": [7.4, 0.5]}]
    assert port.written == encode({"t": "hello"})


def test_spine_link_retries_with_backoff_and_reports_loss():
    attempts = []

    def opener():
        attempts.append(1)
        raise OSError("нет порта")

    link = SpineLink(opener)
    link.poll(0.0), link.poll(0.5), link.poll(1.0), link.poll(2.9), link.poll(3.0)
    assert len(attempts) == 3                                         # 0 с, через 1 с, ещё через 2 с
    assert not link.send({"t": "relax"})
    bad = SpineLink(lambda: Port(fail_read=True))
    assert bad.poll(0) == [{"t": "link", "spine": "lost"}] and bad.port is None


def test_backoff_caps_at_30_seconds():
    assert [backoff(i) for i in range(7)] == [1, 2, 4, 8, 16, 30, 30]


# ---------- связь с ПК ----------
def test_brain_link_talks_both_ways_and_reconnects():
    async def scenario():
        got, sessions = [], []

        async def serve(reader, writer):
            sessions.append(1)
            writer.write(encode({"t": "emote", "name": "happy"}))
            await writer.drain()
            got.append(await reader.readline())
            writer.close()

        server = await asyncio.start_server(serve, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        link = BrainLink("127.0.0.1", port)
        stop = asyncio.Event()
        task = asyncio.ensure_future(link.run(stop))
        assert await asyncio.wait_for(link.inbox.get(), 2) == {"t": "link", "brain": "up"}
        assert await asyncio.wait_for(link.inbox.get(), 2) == {"t": "emote", "name": "happy"}
        link.offer({"t": "ev", "ev": "pet"})
        assert await asyncio.wait_for(link.inbox.get(), 3) == {"t": "link", "brain": "down"}
        assert await asyncio.wait_for(link.inbox.get(), 3) == {"t": "link", "brain": "up"}   # переподключился через 1 с
        stop.set()
        task.cancel()
        server.close()
        return got, sessions

    got, sessions = asyncio.run(scenario())
    assert got[0] == encode({"t": "ev", "ev": "pet"}) and len(sessions) >= 2


def test_brain_outbox_drops_oldest_when_full():
    link = BrainLink("x", 1)
    for i in range(105):
        link.offer({"t": "tel", "n": i})
    assert link.outbox.qsize() == 100 and link.outbox.get_nowait()["n"] == 5
