"""Связь головы: с «спинным мозгом» (USB, RP2350) и с «большим мозгом» (ПК по Wi-Fi, TCP).

Оба канала — строки JSON (protocol.py). Обрыв — не ошибка: голова живёт без ПК и ждёт RP2350, переподключаясь
с паузой 1, 2, 4 … 30 с.
"""
from __future__ import annotations

import asyncio

from .protocol import LineReader, encode

BACKOFF_MAX_S = 30.0


def backoff(attempt: int) -> float:
    return min(BACKOFF_MAX_S, 2.0 ** attempt)


class SpineLink:
    """RP2350 по виртуальному COM-порту. open_port — фабрика порта (pyserial на Pi, имитация в тестах)."""

    def __init__(self, open_port):
        self.open_port, self.port, self.reader = open_port, None, LineReader()
        self.attempt, self.retry_at = 0, 0.0

    def poll(self, now: float) -> list[dict]:
        if self.port is None:
            if now < self.retry_at:
                return []
            try:
                self.port = self.open_port()
                self.attempt = 0
                self.send({"t": "hello"})
            except OSError:
                self.retry_at = now + backoff(self.attempt)
                self.attempt += 1
                return []
        try:
            return self.reader.feed(self.port.read(self.port.in_waiting or 1))
        except OSError:
            self.port = None
            return [{"t": "link", "spine": "lost"}]

    def send(self, msg: dict) -> bool:
        if self.port is None:
            return False
        try:
            self.port.write(encode(msg))
            return True
        except OSError:
            self.port = None
            return False


class BrainLink:
    """ПК: TCP-клиент. inbox — команды от ПК, outbox — телеметрия и события от головы."""

    def __init__(self, host: str, port: int):
        self.host, self.port = host, port
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.outbox: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.connected = False

    def offer(self, msg: dict) -> None:
        """Положить в очередь на отправку; если ПК не успевает — старое выбрасывается, а не копится."""
        if self.outbox.full():
            self.outbox.get_nowait()
        self.outbox.put_nowait(msg)

    async def run(self, stop: asyncio.Event) -> None:
        attempt = 0
        while not stop.is_set():
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
            except OSError:
                await self._wait(stop, backoff(attempt))
                attempt += 1
                continue
            attempt, self.connected = 0, True
            await self.inbox.put({"t": "link", "brain": "up"})
            try:
                await self._session(reader, writer, stop)
            finally:
                self.connected = False
                writer.close()
                await self.inbox.put({"t": "link", "brain": "down"})

    async def _session(self, reader, writer, stop) -> None:
        lines = LineReader()

        async def pump_out():
            while True:
                writer.write(encode(await self.outbox.get()))
                await writer.drain()

        sender = asyncio.ensure_future(pump_out())
        try:
            while not stop.is_set():
                data = await reader.read(4096)
                if not data:
                    return
                for msg in lines.feed(data):
                    await self.inbox.put(msg)
        except (OSError, asyncio.IncompleteReadError):
            return
        finally:
            sender.cancel()

    @staticmethod
    async def _wait(stop: asyncio.Event, seconds: float) -> None:
        try:
            await asyncio.wait_for(stop.wait(), seconds)
        except asyncio.TimeoutError:
            pass
