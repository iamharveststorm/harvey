import asyncio
import json
import time
from datetime import datetime

import pytest

from harvey_brain.__main__ import build_parser, main
from harvey_brain.reply import Reply


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    """Память Харви в тестах — только во временной папке, не в настоящем ~/.harvey."""
    monkeypatch.setenv("HARVEY_HOME", str(tmp_path / "harvey-home"))
    monkeypatch.setenv("HARVEY_MODELS", str(tmp_path / "models"))      # пусто: настоящая модель зрения в тестах не грузится
    return tmp_path / "harvey-home"


class FakeServer:
    def __init__(self):
        self.inbox, self.sent, self.started, self.stopped = asyncio.Queue(), [], False, False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    def send(self, msg):
        self.sent.append(msg)
        return 1


class FakeLLM:
    warmed = True

    def warm(self):
        return self.warmed

    def ask(self, text):
        return Reply("Я краб.", "happy")


def run(lines, server=None, extra=()):
    feed, out = iter(lines), []
    code = main(["--text", *extra], input_fn=lambda: next(feed), server=server, llm=FakeLLM(), out=out.append)
    return code, [line for line in out if not line.startswith(("Харви просыпается", "Харви готов", "LLM недоступна"))]


def test_quick_command_prints_and_sends():
    server = FakeServer()
    code, out = run(["Харви, посмотри на меня", "", ""], server)
    assert code == 0
    assert out[0] == "Харви: Смотрю! [curious, look]"
    assert {"t": "goal", "goal": "look"} in server.sent
    assert server.started and server.stopped


def test_llm_answer_and_no_head():
    code, out = run(["Харви, кто ты?", "", ""], None, ["--no-head"])
    assert out[0] == "Харви: Я краб. [happy]"


def test_sleeping_prints_nothing():
    _, out = run(["привет", "", ""], FakeServer())
    assert out == []


def test_ctrl_c_ends():
    def boom():
        raise KeyboardInterrupt

    out = []
    assert main(["--text", "--no-head"], input_fn=boom, llm=FakeLLM(), out=out.append) == 0


def test_head_event_is_spoken():
    server = FakeServer()
    server.inbox.put_nowait({"t": "ev", "ev": "lifted"})
    feed = iter(["", ""])

    def slow_input():
        import time
        time.sleep(0.2)
        return next(feed)

    out = []
    main(["--text"], input_fn=slow_input, server=server, llm=FakeLLM(), out=out.append)
    assert any("Поставь меня" in line for line in out)


def test_parser_defaults():
    a = build_parser().parse_args(["--text"])
    assert a.port == 8765 and a.model == "qwen3.6:35b" and not a.no_head


def test_warm_messages():
    out, feed = [], iter(["", ""])
    main(["--text", "--no-head"], input_fn=lambda: next(feed), llm=FakeLLM(), out=out.append)
    assert out == ["Харви просыпается…", "Харви готов."]


def test_warm_failed_message():
    llm = FakeLLM()
    llm.warmed = False
    out, feed = [], iter(["", ""])
    main(["--text", "--no-head"], input_fn=lambda: next(feed), llm=llm, out=out.append)
    assert out == ["Харви просыпается…", "LLM недоступна — отвечаю только на команды."]


def run_voice(argv, listener, speaker, server=None):
    out = []
    code = main(argv, server=server, llm=FakeLLM(), out=out.append, listener=listener, speaker=speaker)
    return code, [line for line in out if not line.startswith(("Харви просыпается", "Харви готов", "LLM недоступна"))]


def test_mic_mode_listens_prints_and_speaks():
    from harvey_brain.speech import ListListener
    said = []

    class Spk:
        def say(self, text):
            said.append(text)

        def close(self):
            said.append("closed")

    server = FakeServer()
    code, out = run_voice(["--mic"], ListListener(["шум", "Харви, посмотри на меня"]), Spk(), server)
    assert code == 0
    assert "Слышу: Харви, посмотри на меня" in out and "Харви: Смотрю! [curious, look]" in out
    assert said == ["Смотрю!", "closed"] and {"t": "goal", "goal": "look"} in server.sent


def test_voice_flag_speaks_in_text_mode():
    said, feed = [], iter(["Харви, кто ты?", "", ""])

    class Spk:
        def say(self, text):
            said.append(text)

        def close(self):
            pass

    out = []
    main(["--text", "--voice", "--no-head"], input_fn=lambda: next(feed), llm=FakeLLM(), out=out.append, speaker=Spk())
    assert said == ["Я краб."]


def test_non_ascii_models_path_exits_with_message():
    out = []
    code = main(["--mic", "--no-head", "--models", "C:/Харви/models"], llm=FakeLLM(), out=out.append)
    assert code == 2 and any("espeak" in line for line in out)


def test_models_option_parsed():
    a = build_parser().parse_args(["--mic", "--voice", "--models", "C:/m"])
    assert a.mic and a.voice and a.models == "C:/m"


def test_build_voice_mic_wraps_speaker_half_duplex(monkeypatch):
    from harvey_brain import __main__ as m
    monkeypatch.setattr(m, "MicListener", lambda models: ("mic", models))
    monkeypatch.setattr(m, "PiperSpeaker", lambda models: ("piper", models))
    monkeypatch.setattr(m, "HalfDuplexSpeaker", lambda spk, lis: ("half", spk, lis))
    args = build_parser().parse_args(["--mic", "--models", "C:/m"])
    listener, speaker = m.build_voice(args, None, None)
    assert listener[0] == "mic" and speaker == ("half", ("piper", m.Path("C:/m")), listener)


def test_build_voice_voice_only_has_plain_speaker(monkeypatch):
    from harvey_brain import __main__ as m
    monkeypatch.setattr(m, "PiperSpeaker", lambda models: "piper")
    args = build_parser().parse_args(["--text", "--voice", "--models", "C:/m"])
    assert m.build_voice(args, None, None) == (None, "piper")


def test_build_voice_text_only_loads_nothing():
    from harvey_brain import __main__ as m
    assert m.build_voice(build_parser().parse_args(["--text"]), None, None) == (None, None)


class Clock:
    def __init__(self, hour=10, minute=0):
        self.now = datetime(2026, 11, 5, hour, minute).timestamp()

    def __call__(self):
        return self.now

    def advance(self, seconds):
        def step():
            self.now += seconds
        return step


def run_clocked(items, clock, extra=("--no-head",)):
    """items: строки с клавиатуры или функции (часы идут вперёд; даём мозгу время заметить)."""
    feed, out = iter(items), []

    def input_fn():
        item = next(feed)
        if callable(item):
            item()
            time.sleep(0.2)
            return ""
        return item

    main(["--text", *extra], input_fn=input_fn, llm=FakeLLM(), out=out.append, clock=clock, poll_s=0.01)
    return [line for line in out if line.startswith("Харви:")]


def test_home_option_and_env(home, tmp_path):
    assert build_parser().parse_args(["--text", "--home", "C:/h"]).home == "C:/h"
    run_clocked(["Харви, меня зовут Аня", "", ""], Clock())
    assert json.loads((home / "memory.json").read_text("utf-8"))["name"] == "Аня"
    run_clocked(["Харви, меня зовут Боря", "", ""], Clock(), ("--no-head", "--home", str(tmp_path / "other")))
    assert (tmp_path / "other" / "memory.json").exists()


def test_clock_question_does_not_use_llm():
    assert run_clocked(["Харви, который час", "", ""], Clock(14, 5)) == ["Харви: Сейчас 14:05. [neutral]"]


def test_timer_fires_by_itself_and_dialog_stays_awake():
    clock = Clock()
    out = run_clocked(["Харви, таймер на одну минуту", clock.advance(61), "отмени таймер", "", ""], clock)
    assert out == ["Харви: Ставлю таймер на 1 минуту. [happy]", "Харви: Динь! Прошла 1 минута. [surprised]",
                   "Харви: Таймеров нет. [neutral]"]


def test_overdue_reminder_spoken_at_start_once():
    clock = Clock()
    run_clocked(["Харви, напомни через пять минут позвонить маме", "", ""], clock)
    clock.now += 3600
    assert run_clocked(["", ""], clock) == ["Харви: Пока меня не было: позвонить маме. [curious]"]
    assert run_clocked(["", ""], clock) == []


def test_memory_survives_restart_and_feeds_llm(home):
    run_clocked(["Харви, запомни что я люблю чай", "Харви, меня зовут Аня", "", ""], Clock())
    out = run_clocked(["Харви, что ты обо мне знаешь", "", ""], Clock())
    assert "Аня" in out[0] and "я люблю чай" in out[0]


def test_reminder_and_voice_go_to_head_and_speaker():
    clock, said, server = Clock(), [], FakeServer()

    class Spk:
        def say(self, text):
            said.append(text)

        def close(self):
            pass

    feed = iter(["Харви, таймер на одну минуту", clock.advance(61), "", ""])

    def input_fn():
        item = next(feed)
        if callable(item):
            item()
            time.sleep(0.2)
            return ""
        return item

    main(["--text"], input_fn=input_fn, server=server, llm=FakeLLM(), out=lambda s: None, speaker=Spk(),
         clock=clock, poll_s=0.01)
    assert said == ["Ставлю таймер на 1 минуту.", "Динь! Прошла 1 минута."]
    assert {"t": "emote", "name": "surprised", "s": 3.0} in server.sent


def test_llm_gets_memory_about(monkeypatch):
    from harvey_brain import __main__ as m
    seen = []

    def fake_chat(model, about):
        seen.append(about)
        return FakeLLM()
    monkeypatch.setattr(m, "OllamaChat", fake_chat)
    run_clocked(["Харви, меня зовут Аня", "", ""], Clock())
    feed = iter(["", ""])
    m.main(["--text", "--no-head"], input_fn=lambda: next(feed), out=lambda s: None)
    assert "Аня" in seen[0]()


# --- --head-audio ----------------------------------------------------------------------------------------------

class FakeMediaServer:
    def __init__(self, connected=False):
        self.connected, self.started, self.stopped, self.video = connected, False, False, []

    def request_video(self, on, fps=5):
        self.video.append((on, fps))

    def latest_frame(self):
        return None

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


class Spk:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)

    def close(self):
        pass


def test_head_audio_options_parsed():
    a = build_parser().parse_args(["--head-audio"])
    assert a.head_audio and a.media_port == 8766
    assert build_parser().parse_args(["--head-audio", "--media-port", "9001"]).media_port == 9001
    assert not build_parser().parse_args(["--text"]).head_audio


def test_head_audio_waits_for_the_head_and_says_so_once():
    from harvey_brain.speech import ListListener
    media, spk, out = FakeMediaServer(), Spk(), []
    code = main(["--head-audio", "--no-head"], llm=FakeLLM(), out=out.append, media=media,
                listener=ListListener(["Харви, посмотри на меня"]), speaker=spk)
    assert code == 0 and out.count("Жду голову…") == 1
    assert media.started and media.stopped and spk.said == ["Смотрю!"]


def test_head_audio_with_the_head_already_connected_does_not_wait():
    from harvey_brain.speech import ListListener
    media, out = FakeMediaServer(connected=True), []
    main(["--head-audio", "--no-head"], llm=FakeLLM(), out=out.append, media=media, listener=ListListener([]),
         speaker=Spk())
    assert "Жду голову…" not in out and media.started


def test_without_head_audio_no_media_server_is_started():
    code, out = run(["", ""], None, ["--no-head"])
    assert "Жду голову…" not in out


def test_build_voice_head_audio_uses_remote_listener_and_speaker(monkeypatch):
    from harvey_brain import __main__ as m
    monkeypatch.setattr(m, "RemoteMicListener", lambda media, models: ("remote-mic", media, models))
    monkeypatch.setattr(m, "PiperSpeaker", lambda models: ("piper", models))
    monkeypatch.setattr(m, "RemoteSpeaker", lambda media, piper: ("remote-spk", media, piper))
    args = build_parser().parse_args(["--head-audio", "--models", "C:/m"])
    listener, speaker = m.build_voice(args, None, None, media="M")
    assert listener == ("remote-mic", "M", m.Path("C:/m")) and speaker == ("remote-spk", "M", ("piper", m.Path("C:/m")))


def test_head_audio_keeps_injected_parts():
    from harvey_brain import __main__ as m
    args = build_parser().parse_args(["--head-audio"])
    assert m.build_voice(args, "L", "S", media="M") == ("L", "S")


# --- зрение --------------------------------------------------------------------------------------------------------
from harvey_brain.vision import Face, HeadFrames, Sight  # noqa: E402

LEFT_FACE = Face(100, 260, 200, 200, 0.95)           # левая часть кадра 1280 × 720: азимут > 0
RIGHT_FACE = Face(980, 260, 200, 200, 0.95)


class FakeSight:
    """Сценарий взглядов: список наборов лиц по одному на вызов, последний повторяется."""

    def __init__(self, *looks):
        from harvey_head.dock_tag import camera_matrix
        self.looks, self.k, self.closed = list(looks), camera_matrix(1280, 720), False

    def look(self):
        faces = self.looks.pop(0) if len(self.looks) > 1 else self.looks[0]
        return faces, self.k, (1280, 720)

    def close(self):
        self.closed = True


class SlowListener:
    """Голос, который приходит не сразу: зрению есть время поработать."""

    def __init__(self, *texts):
        self.texts = texts

    def utterances(self):
        time.sleep(0.3)
        yield from self.texts

    def close(self):
        pass


def run_vision(argv, sight, items=(), server=None, media=None, speaker=None, out=None, listener=None):
    feed = iter([*items, "", ""])

    def input_fn():
        item = next(feed)
        if callable(item):
            item()
            return ""
        return item

    out = [] if out is None else out
    code = main(argv, input_fn=input_fn, server=server, llm=FakeLLM(), out=out.append, media=media, speaker=speaker,
                sight=sight, vision_s=0.005, listener=listener)
    return code, out


def settle():
    time.sleep(0.3)


def test_vision_option_parsed():
    assert build_parser().parse_args(["--text"]).vision is None
    assert build_parser().parse_args(["--vision", "webcam"]).vision == "webcam"
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--vision", "radar"])


def test_head_audio_turns_vision_on_by_default_and_asks_the_head_for_video():
    media, server = FakeMediaServer(connected=True), FakeServer()
    run_vision(["--head-audio", "--no-head"], FakeSight([]), media=media, speaker=Spk(), listener=SlowListener())
    assert media.video == [(True, 5)]


def test_vision_head_alone_also_starts_the_media_server():
    media = FakeMediaServer(connected=True)
    run_vision(["--text", "--vision", "head"], FakeSight([]), media=media, items=[settle])
    assert media.started and media.video == [(True, 5)]


def test_vision_off_and_no_media_means_no_looking():
    media, server = FakeMediaServer(connected=True), FakeServer()
    run_vision(["--head-audio", "--vision", "off"], FakeSight([LEFT_FACE]), media=media, speaker=Spk(),
               listener=SlowListener(), server=server)
    assert media.video == [] and server.sent == []
    server2 = FakeServer()
    run_vision(["--text"], FakeSight([LEFT_FACE]), items=[settle], server=server2)
    assert server2.sent == []


def test_eyes_follow_the_face_and_greeting_is_spoken_once():
    server, spk = FakeServer(), Spk()
    run_vision(["--text", "--vision", "webcam"], FakeSight([LEFT_FACE]), items=[settle, settle], server=server, speaker=spk)
    assert spk.said == ["Привет!"]
    looks = [m for m in server.sent if m["t"] == "look"]
    assert looks and looks[0]["x"] < 0
    assert {"t": "emote", "name": "happy", "s": 3.0} in server.sent


def test_greeting_uses_the_name_from_memory(home):
    home.mkdir(parents=True)
    (home / "memory.json").write_text(json.dumps({"name": "Аня", "facts": [], "timers": []}, ensure_ascii=False), "utf-8")
    spk = Spk()
    run_vision(["--text", "--vision", "webcam", "--no-head"], FakeSight([RIGHT_FACE]), items=[settle], speaker=spk)
    assert spk.said == ["Привет, Аня!"]


def test_no_greeting_without_a_face():
    spk = Spk()
    run_vision(["--text", "--vision", "webcam", "--no-head"], FakeSight([]), items=[settle], speaker=spk)
    assert spk.said == []


def test_look_at_me_with_a_visible_face_sends_turn_with_the_bearing():
    server = FakeServer()
    run_vision(["--text", "--vision", "webcam"], FakeSight([LEFT_FACE]), server=server,
               items=[settle, "Харви, посмотри на меня"])
    turns = [m for m in server.sent if m["t"] == "turn"]
    assert len(turns) == 1 and turns[0]["deg"] > 10
    assert {"t": "goal", "goal": "look"} not in server.sent


def test_look_at_me_with_the_face_on_the_right_turns_right():
    server = FakeServer()
    run_vision(["--text", "--vision", "webcam"], FakeSight([RIGHT_FACE]), server=server,
               items=[settle, "Харви, посмотри на меня"])
    assert [m["deg"] for m in server.sent if m["t"] == "turn"][0] < -10


def test_look_at_me_without_a_face_looks_around_as_before():
    server, out = FakeServer(), []
    run_vision(["--text", "--vision", "webcam"], FakeSight([]), server=server, items=[settle, "Харви, посмотри на меня"],
               out=out)
    assert {"t": "goal", "goal": "look"} in server.sent and not [m for m in server.sent if m["t"] == "turn"]
    assert "Харви: Смотрю! [curious, look]" in out


def test_stale_head_frame_is_not_a_face_right_now():
    class Media(FakeMediaServer):
        def latest_frame(self):
            return (time.time() - 5.0, JPEG)             # голова отключилась 5 с назад

    import cv2
    import numpy as np
    JPEG = cv2.imencode(".jpg", np.zeros((72, 128), np.uint8))[1].tobytes()
    media, server, spk = Media(connected=True), FakeServer(), Spk()
    finder = type("F", (), {"find": lambda self, img: [LEFT_FACE]})()
    sight = Sight(HeadFrames(media), finder)
    run_vision(["--head-audio"], sight, media=media, speaker=spk, server=server,
               listener=SlowListener("Харви, посмотри на меня"))
    assert spk.said == ["Смотрю!"] and not [m for m in server.sent if m["t"] in ("look", "turn")]


def test_without_the_model_default_vision_is_switched_off_with_a_message():
    media, out = FakeMediaServer(connected=True), []
    code = main(["--head-audio", "--no-head"], llm=FakeLLM(), out=out.append, media=media, listener=__import__(
        "harvey_brain.speech", fromlist=["ListListener"]).ListListener([]), speaker=Spk())
    assert code == 0 and media.video == [] and any("Зрение выключено" in line for line in out)


def test_explicit_vision_without_the_model_stops_with_exit_code_2():
    out = []
    assert main(["--text", "--vision", "webcam", "--no-head"], llm=FakeLLM(), out=out.append) == 2
    assert any("face_detection_yunet_2023mar.onnx" in line for line in out)


def test_sight_is_closed_at_the_end():
    sight = FakeSight([])
    run_vision(["--text", "--vision", "webcam", "--no-head"], sight)
    assert sight.closed
