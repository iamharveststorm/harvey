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
