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
