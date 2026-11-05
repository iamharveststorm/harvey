"""ThreadedBrain: связь головы мини-симуляции с настоящим «большим мозгом» (HeadServer) из отдельного потока."""
import asyncio
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import mini_brain as mb  # noqa: E402

sys.path.insert(0, str(mb.brain_dir()))
from harvey_brain.server import HeadServer  # noqa: E402


class ServerThread:
    """Настоящий HeadServer в своём потоке и цикле, на свободном порту."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.server = HeadServer("127.0.0.1", 0)
        ready = threading.Event()

        def run():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.server.start())
            ready.set()
            self.loop.run_forever()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        assert ready.wait(5)
        self.port = self.server.port

    def send(self, msg):
        self.loop.call_soon_threadsafe(self.server.send, msg)

    def inbox(self):
        return list(self.server.inbox._queue)

    def stop(self):
        asyncio.run_coroutine_threadsafe(self.server.stop(), self.loop).result(5)
        self.loop.call_soon_threadsafe(self.loop.stop)


def wait_for(cond, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def pair():
    srv = ServerThread()
    brain = mb.ThreadedBrain("127.0.0.1", srv.port)
    brain.start()
    yield srv, brain
    brain.close()
    srv.stop()


def collect(brain, seen):
    seen.extend(brain.poll())
    return seen


def test_connects_and_reports_link_up(pair):
    _, brain = pair
    seen = []
    assert wait_for(lambda: {"t": "link", "brain": "up"} in collect(brain, seen))
    assert brain.connected


def test_goal_from_brain_arrives_in_poll(pair):
    srv, brain = pair
    seen = []
    assert wait_for(lambda: brain.connected)
    srv.send({"t": "goal", "goal": "home"})
    assert wait_for(lambda: {"t": "goal", "goal": "home"} in collect(brain, seen))


def test_offer_reaches_server_inbox(pair):
    srv, brain = pair
    assert wait_for(lambda: brain.connected)
    brain.offer({"t": "ev", "ev": "lifted"})
    assert wait_for(lambda: {"t": "ev", "ev": "lifted"} in srv.inbox())


def test_without_server_is_quiet_and_closes_fast():
    brain = mb.ThreadedBrain("127.0.0.1", 1)          # порт 1: никто не слушает
    brain.start()
    brain.offer({"t": "ev", "ev": "lifted"})            # не падает и не копится
    assert brain.poll() == [] and brain.connected is False
    t0 = time.monotonic()
    brain.close()
    assert time.monotonic() - t0 <= 2.0


def test_retry_pause_is_capped_at_five_seconds(monkeypatch):
    waited = []

    async def fake_wait(stop, seconds):
        waited.append(seconds)

    monkeypatch.setattr(mb.BrainLink, "_wait", staticmethod(fake_wait))
    asyncio.run(mb.RetryLink("127.0.0.1", 1)._wait(asyncio.Event(), 30.0))
    assert waited == [5.0] and mb.RETRY_MAX_S == 5.0
