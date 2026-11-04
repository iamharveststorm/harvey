"""TCP-сервер для головы: одна строка — одно JSON-сообщение."""
import asyncio

from .protocol import LineReader, encode


class HeadServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host, self.port = host, port
        self.inbox: asyncio.Queue = asyncio.Queue()
        self._writers: set = set()
        self._server = None

    @property
    def heads(self) -> int:
        return len(self._writers)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._serve, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        for writer in list(self._writers):
            writer.close()
        self._writers.clear()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    def send(self, msg: dict) -> int:
        """Разослать всем головам без ожидания; закрытые отбрасываются. Возвращает, скольким ушло."""
        data, sent = encode(msg), 0
        for writer in list(self._writers):
            if writer.is_closing():
                self._writers.discard(writer)
                continue
            writer.write(data)
            sent += 1
        return sent

    async def _serve(self, reader, writer) -> None:
        self._writers.add(writer)
        lines = LineReader()
        try:
            while data := await reader.read(4096):
                for msg in lines.feed(data):
                    await self.inbox.put(msg)
        except OSError:
            pass
        finally:
            self._writers.discard(writer)
            writer.close()
