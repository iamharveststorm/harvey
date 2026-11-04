"""python -m harvey_brain --text [--model M] [--port 8765] [--no-head]"""
import argparse
import asyncio
import threading
import time

from .dialog import Dialog
from .llm import OllamaChat
from .reply import Reply, to_head
from .server import HeadServer

DEFAULT_MODEL = "qwen3.6:35b"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harvey_brain", description="Большой мозг Харви")
    p.add_argument("--text", action="store_true", help="текстовый режим: фразы с клавиатуры")
    p.add_argument("--model", default=DEFAULT_MODEL, help="модель Ollama")
    p.add_argument("--port", type=int, default=8765, help="порт для головы")
    p.add_argument("--no-head", action="store_true", help="без сервера для головы")
    return p


def present(reply: Reply, server, out) -> None:
    tags = ", ".join([reply.emote] + ([reply.goal] if reply.goal else []))
    out(f"Харви: {reply.say} [{tags}]")
    if server:
        for msg in to_head(reply):
            server.send(msg)


async def watch_head(server, dialog: Dialog, out) -> None:
    while True:
        reply = dialog.on_head(await server.inbox.get(), time.monotonic())
        if reply:
            present(reply, server, out)


async def read_lines(dialog: Dialog, input_fn, server, out) -> None:
    """Строки с клавиатуры; пустая строка дважды подряд или Ctrl+C — конец."""
    loop, blanks = asyncio.get_running_loop(), 0
    while blanks < 2:
        try:
            line = (await loop.run_in_executor(None, input_fn)).strip()
        except (KeyboardInterrupt, EOFError, StopIteration):
            return
        blanks = blanks + 1 if not line else 0
        reply = line and await loop.run_in_executor(None, dialog.on_text, line, time.monotonic())
        if reply:
            present(reply, server, out)


async def run(args, input_fn, server, llm, out) -> None:
    dialog = Dialog(llm)
    if server:
        await server.start()
    watcher = asyncio.ensure_future(watch_head(server, dialog, out)) if server else None
    try:
        await read_lines(dialog, input_fn, server, out)
    finally:
        if watcher:
            watcher.cancel()
        if server:
            await server.stop()


def warm_up(llm, out) -> threading.Thread:
    out("Харви просыпается…")

    def work():
        out("Харви готов." if llm.warm() else "LLM недоступна — отвечаю только на команды.")

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread


def main(argv=None, input_fn=input, server=None, llm=None, out=print) -> int:
    args = build_parser().parse_args(argv)
    if not args.no_head:
        server = server or HeadServer(port=args.port)
    else:
        server = None
    llm = llm or OllamaChat(args.model)
    warming = warm_up(llm, out)
    try:
        asyncio.run(run(args, input_fn, server, llm, out))
    except KeyboardInterrupt:
        pass
    warming.join(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
