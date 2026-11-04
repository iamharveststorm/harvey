import urllib.error

import pytest

from harvey_brain.llm import OllamaChat
from harvey_brain.persona import REPLY_SCHEMA, SYSTEM_PROMPT
from harvey_brain.reply import Reply

ANSWER = {"message": {"content": '{"say":"Привет!","emote":"happy","goal":"none"}'}}


class Fake:
    def __init__(self, response=ANSWER):
        self.response, self.calls = response, []

    def __call__(self, url, payload, timeout):
        self.calls.append((url, payload, timeout))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_payload_and_reply():
    fake = Fake()
    chat = OllamaChat("m", post=fake)
    assert chat.ask("привет") == Reply("Привет!", "happy", None)
    url, p, _ = fake.calls[0]
    assert url.endswith("/api/chat")
    assert p["model"] == "m" and p["stream"] is False and p["think"] is False
    assert p["format"] == REPLY_SCHEMA and p["keep_alive"] == "30m"
    assert p["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert p["messages"][-1] == {"role": "user", "content": "привет"}


def test_history_limited():
    fake = Fake()
    chat = OllamaChat("m", post=fake)
    for i in range(8):
        chat.ask(f"q{i}")
    msgs = fake.calls[-1][1]["messages"]
    assert len(msgs) == 1 + 6 * 2 + 1
    assert msgs[1]["content"] == "q1"
    assert msgs[2] == {"role": "assistant", "content": "Привет!"}


@pytest.mark.parametrize("bad", [urllib.error.URLError("x"), TimeoutError(), {}, ConnectionResetError()])
def test_fallback(bad):
    chat = OllamaChat("m", post=Fake(bad))
    assert chat.ask("привет") == OllamaChat.FALLBACK
    assert chat.history == []


def test_warm_ok_keeps_history():
    fake = Fake()
    chat = OllamaChat("m", post=fake)
    chat.history = [("a", "b")]
    assert chat.warm() is True
    p = fake.calls[0][1]
    assert p["messages"][0]["role"] == "system" and p["messages"][-1]["role"] == "user"
    assert p["keep_alive"] == "30m" and p["think"] is False and p["model"] == "m"
    assert fake.calls[0][2] == 120.0
    assert chat.history == [("a", "b")]


@pytest.mark.parametrize("bad", [urllib.error.URLError("x"), TimeoutError(), {}])
def test_warm_fails(bad):
    assert OllamaChat("m", post=Fake(bad)).warm() is False
