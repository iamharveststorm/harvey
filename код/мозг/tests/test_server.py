import asyncio
import sys
from pathlib import Path


def _head_dir() -> Path:
    here = Path(__file__)
    for base in (here.absolute(), here.resolve()):
        candidate = base.parents[2] / "голова"
        if (candidate / "harvey_head" / "links.py").exists():
            return candidate
    raise ImportError("не найден код/голова")


sys.path.append(str(_head_dir()))

from harvey_head.links import BrainLink  # noqa: E402

from harvey_brain.server import HeadServer  # noqa: E402


async def until(cond, seconds=3.0):
    for _ in range(int(seconds / 0.01)):
        if cond():
            return True
        await asyncio.sleep(0.01)
    return False


async def connect(server):
    link, stop = BrainLink("127.0.0.1", server.port), asyncio.Event()
    task = asyncio.ensure_future(link.run(stop))
    assert await until(lambda: link.connected and server.heads >= 1)
    return link, stop, task


async def disconnect(link, stop, task):
    stop.set()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


def run_with_server(scenario):
    async def main():
        server = HeadServer("127.0.0.1", 0)
        await server.start()
        try:
            await scenario(server)
        finally:
            await server.stop()

    asyncio.run(main())


def test_send_without_heads():
    run_with_server(_send_without_heads)


async def _send_without_heads(server):
    assert server.heads == 0
    assert server.send({"t": "emote", "name": "happy", "s": 2}) == 0


def test_both_directions():
    run_with_server(_both_directions)


async def _both_directions(server):
    link, stop, task = await connect(server)
    assert server.heads == 1
    assert server.send({"t": "emote", "name": "happy", "s": 2}) == 1
    msgs = []
    assert await until(lambda: link.inbox.qsize() >= 2)
    while not link.inbox.empty():
        msgs.append(link.inbox.get_nowait())
    assert {"t": "emote", "name": "happy", "s": 2} in msgs
    link.offer({"t": "ev", "ev": "lifted"})
    assert await asyncio.wait_for(server.inbox.get(), 3) == {"t": "ev", "ev": "lifted"}
    await disconnect(link, stop, task)


def test_reconnect_many_times():
    run_with_server(_reconnect)


async def _reconnect(server):
    for _ in range(5):
        parts = await connect(server)
        await disconnect(*parts)
        assert await until(lambda: server.heads == 0)
    assert server.send({"t": "x"}) == 0
    parts = await connect(server)
    assert server.heads == 1
    await disconnect(*parts)
