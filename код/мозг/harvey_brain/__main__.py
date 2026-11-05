"""python -m harvey_brain (--text | --mic) [--voice] [--models PATH] [--home PATH] [--model M] [--port 8765] [--no-head] [--head-audio] [--media-port 8766] [--vision head|webcam|off]"""
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
from .media_server import MediaServer
from .server import HeadServer
from .vision import FaceFinder, HeadFrames, Sight, Watcher, WebcamFrames
from .speech import (HalfDuplexSpeaker, MicListener, ModelsPathError, PiperSpeaker, RemoteMicListener, RemoteSpeaker,
                     resolve_models_dir)

DEFAULT_MODEL = "qwen3.6:35b"
VISION_MODEL = Path("vision") / "face_detection_yunet_2023mar.onnx"      # в папке моделей
VISION_FPS = 5
VISION_MODES = ("head", "webcam", "off")


class VisionError(Exception):
    pass


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
    p.add_argument("--head-audio", action="store_true", help="слушать микрофонами головы и говорить её динамиком (по Wi-Fi)")
    p.add_argument("--media-port", type=int, default=8766, help="порт звука и картинки головы (--head-audio)")
    p.add_argument("--vision", choices=VISION_MODES,
                   help="лица: head — камера головы (по умолчанию с --head-audio), webcam — камера ноутбука, off — без зрения")
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


def greeting(name: str | None) -> Reply:
    return Reply(f"Привет, {name}!" if name else "Привет!", "happy")


async def watch_faces(sight, watcher: Watcher, server, out, speaker, name_fn, clock, period_s: float) -> None:
    """Раз в period_s: взгляд (кадр -> лица) -> глазам `look`; человек появился после долгого отсутствия — «Привет!»."""
    loop = asyncio.get_running_loop()
    while True:
        faces, k, size = await loop.run_in_executor(None, sight.look)
        for msg in watcher.update(faces, clock(), k, size):
            server and server.send(msg)
        if watcher.take_greeting():
            await deliver(greeting(name_fn()), server, out, speaker)
        await asyncio.sleep(period_s)


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


async def start_media(media, out) -> None:
    await media.start()
    if not media.connected:
        out("Жду голову…")


def start_vision(args, sight, watcher, media, server, out, speaker, assistant, clock, period_s):
    """Зрение в фоне; с камерой головы — попросить её слать кадры."""
    if media and args.vision == "head":
        media.request_video(True, VISION_FPS)
    name_fn = lambda: assistant and assistant.memory.name      # noqa: E731
    return asyncio.ensure_future(watch_faces(sight, watcher, server, out, speaker, name_fn, clock, period_s))


async def shut_down(background, parts, servers) -> None:
    """Закрыть слушателя, говорящего и взгляд, остановить фоновые задачи и серверы."""
    for part in parts:
        part and part.close()
    for task in background:
        task.cancel()
    for server in servers:
        server and await server.stop()


async def run(args, input_fn, server, llm, out, listener=None, speaker=None, assistant=None,
              clock=time.time, poll_s=0.5, media=None, sight=None, vision_s=0.2) -> None:
    watcher = Watcher() if sight else None
    dialog = Dialog(llm, assistant, wall_fn=clock, watcher=watcher)
    if server:
        await server.start()
    if media:
        await start_media(media, out)
    background = start_background(dialog, assistant, server, out, speaker, clock, poll_s)
    if sight:
        background.append(start_vision(args, sight, watcher, media, server, out, speaker, assistant, clock, vision_s))
    try:
        if listener:
            await read_speech(dialog, listener, server, out, speaker)
        else:
            await read_lines(dialog, input_fn, server, out, speaker)
    finally:
        await shut_down(background, (listener, speaker, sight), (server, media))


def warm_up(llm, out) -> threading.Thread:
    out("Харви просыпается…")

    def work():
        out("Харви готов." if llm.warm() else "LLM недоступна — отвечаю только на команды.")

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    return thread


def wants_models(args, listener, speaker) -> bool:
    listening = args.mic or args.head_audio
    return bool((listening and not listener) or ((listening or args.voice) and not speaker))


def build_voice(args, listener, speaker, media=None):
    """(слушатель, говорящий): подставленные снаружи остаются как есть; настоящие грузятся из папки моделей.
    --head-audio: слушает и говорит голова (через media), иначе — микрофон и динамик этого ПК."""
    if not wants_models(args, listener, speaker):
        return listener, speaker
    models = resolve_models_dir(args.models, os.environ, Path.home())
    if args.head_audio:
        return (listener or RemoteMicListener(media, models),
                speaker or RemoteSpeaker(media, PiperSpeaker(models)))
    listener = listener or (MicListener(models) if args.mic else None)
    if speaker:
        return listener, speaker
    speaker = PiperSpeaker(models)
    return listener, HalfDuplexSpeaker(speaker, listener) if listener else speaker


def build_sight(args, media, sight, explicit: bool, out):
    """Взгляд: подставленный снаружи, настоящий (модель YuNet из папки моделей) или None. Нет модели: просили
    --vision сами — ошибка, иначе зрение просто выключается."""
    if args.vision == "off":
        return None
    if sight:
        return sight
    path = resolve_models_dir(args.models, os.environ, Path.home()) / VISION_MODEL
    if not path.exists():
        text = f"Нет модели зрения: {path} (YuNet face_detection_yunet_2023mar.onnx, см. README)"
        if explicit:
            raise VisionError(text)
        out(f"Зрение выключено. {text}")
        args.vision = "off"
        return None
    frames = HeadFrames(media) if args.vision == "head" else WebcamFrames()
    return Sight(frames, FaceFinder(path))


def pick_media(args, media):
    """Сервер звука и картинки нужен для --head-audio и для --vision head (подставленный снаружи остаётся)."""
    if not (args.head_audio or args.vision == "head"):
        return None
    return media or MediaServer(port=args.media_port)


def main(argv=None, input_fn=input, server=None, llm=None, out=print, listener=None, speaker=None,
         clock=time.time, poll_s=0.5, media=None, sight=None, vision_s=0.2) -> int:
    args = build_parser().parse_args(argv)
    explicit = args.vision is not None
    media = pick_media(args, media)
    args.vision = args.vision or ("head" if media else "off")
    try:
        listener, speaker = build_voice(args, listener, speaker, media)
        sight = build_sight(args, media, sight, explicit, out)
    except (ModelsPathError, VisionError) as e:
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
        asyncio.run(run(args, input_fn, server, llm, out, listener, speaker, Assistant(memory), clock, poll_s, media, sight, vision_s))
    except KeyboardInterrupt:
        pass
    warming.join(0.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
