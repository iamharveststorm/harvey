"""python -m harvey_brain (--text | --mic) [--voice] [--models PATH] [--home PATH] [--model M] [--port 8765] [--no-head]"""
import argparse
import asyncio
import os
import threading
import time
from pathlib import Path

from .assistant import Assistant
from .dialog import Dialog
from .llm import OllamaChat
from .memory import Memory, resolve_home
from .reply import Reply, to_head
from .server import HeadServer
from .speech import HalfDuplexSpeaker, MicListener, ModelsPathError, PiperSpeaker, resolve_models_dir

DEFAULT_MODEL = "qwen3.6:35b"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="harvey_brain", description="Большой мозг Харви")
    p.add_argument("--text", action="store_true", help="текстовый режим: фразы с клавиатуры")
    p.add_argument("--mic", action="store_true", help="голос: микрофон -> распознавание, ответ вслух")
    p.add_argument("--voice", action="store_true", help="в --text ещё и говорить вслух (Piper)")
    p.add_argument("--models", help="папка моделей речи (иначе HARVEY_MODELS, иначе ~/.harvey/models; только ASCII-путь)")
    p.add_argument("--home", help="папка памяти Харви (иначе HARVEY_HOME, иначе ~/.harvey): memory.json")
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


async def deliver(reply: Reply, server, out, speaker) -> None:
    present(reply, server, out)
    if speaker:
        await asyncio.get_running_loop().run_in_executor(None, speaker.say, reply.say)


async def watch_head(server, dialog: Dialog, out, speaker=None) -> None:
    while True:
        reply = dialog.on_head(await server.inbox.get(), time.monotonic())
        if reply:
            await deliver(reply, server, out, speaker)


async def watch_due(assistant: Assistant, dialog: Dialog, server, out, speaker, clock, poll_s: float) -> None:
    """Сработавшие таймеры и напоминания — обычный ответ; после него Харви ещё слушает без «Харви»."""
    while True:
        for reply in assistant.due(clock()):
            dialog.stay_awake(time.monotonic())
            await deliver(reply, server, out, speaker)
        await asyncio.sleep(poll_s)


async def read_lines(dialog: Dialog, input_fn, server, out, speaker=None) -> None:
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
            await deliver(reply, server, out, speaker)


async def read_speech(dialog: Dialog, listener, server, out, speaker=None) -> None:
    """Фразы из микрофона (блокирующий итератор в потоке) до конца потока или Ctrl+C."""
    loop, heard = asyncio.get_running_loop(), iter(listener.utterances())
    while (text := await loop.run_in_executor(None, next, heard, None)) is not None:
        out(f"Слышу: {text}")
        reply = await loop.run_in_executor(None, dialog.on_text, text, time.monotonic())
        if reply:
            await deliver(reply, server, out, speaker)


def start_background(dialog, assistant, server, out, speaker, clock, poll_s) -> list:
    """Фоновые задачи: события головы (если есть голова) и срабатывание таймеров."""
    jobs = [watch_head(server, dialog, out, speaker)] if server else []
    jobs += [watch_due(assistant, dialog, server, out, speaker, clock, poll_s)] if assistant else []
    return [asyncio.ensure_future(job) for job in jobs]


async def run(args, input_fn, server, llm, out, listener=None, speaker=None, assistant=None,
              clock=time.time, poll_s=0.5) -> None:
    dialog = Dialog(llm, assistant, wall_fn=clock)
    if server:
        await server.start()
    background = start_background(dialog, assistant, server, out, speaker, clock, poll_s)
    try:
        if listener:
            await read_speech(dialog, listener, server, out, speaker)
        else:
            await read_lines(dialog, input_fn, server, out, speaker)
    finally:
        for part in (listener, speaker):
            part and part.close()
        for task in background:
            task.cancel()
        if server:
            await server.stop()


def warm_up(llm, out) -> threading.Thread:
    out("Харви просыпается…")

    def work():
        out("Харви готов." if llm.warm() else "LLM недоступна — отвечаю только на команды.")

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread


def wants_models(args, listener, speaker) -> bool:
    return bool((args.mic and not listener) or ((args.mic or args.voice) and not speaker))


def build_voice(args, listener, speaker):
    """(слушатель, говорящий): подставленные снаружи остаются как есть; настоящие грузятся из папки моделей."""
    if not wants_models(args, listener, speaker):
        return listener, speaker
    models = resolve_models_dir(args.models, os.environ, Path.home())
    listener = listener or (MicListener(models) if args.mic else None)
    if speaker:
        return listener, speaker
    speaker = PiperSpeaker(models)
    return listener, HalfDuplexSpeaker(speaker, listener) if listener else speaker


def main(argv=None, input_fn=input, server=None, llm=None, out=print, listener=None, speaker=None,
         clock=time.time, poll_s=0.5) -> int:
    args = build_parser().parse_args(argv)
    try:
        listener, speaker = build_voice(args, listener, speaker)
    except ModelsPathError as e:
        out(str(e))
        return 2
    if not args.no_head:
        server = server or HeadServer(port=args.port)
    else:
        server = None
    memory = Memory(resolve_home(args.home, os.environ, Path.home()) / "memory.json")
    memory.load()
    llm = llm or OllamaChat(args.model, about=memory.about)
    warming = warm_up(llm, out)
    try:
        asyncio.run(run(args, input_fn, server, llm, out, listener, speaker, Assistant(memory), clock, poll_s))
    except KeyboardInterrupt:
        pass
    warming.join(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
