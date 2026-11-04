import asyncio

from harvey_brain.__main__ import build_parser, main
from harvey_brain.reply import Reply


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
