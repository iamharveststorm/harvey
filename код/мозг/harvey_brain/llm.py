"""LLM через локальную Ollama: ответ JSON по схеме, короткая история, при сбое — запасная фраза."""
import json
import urllib.request

from .persona import REPLY_SCHEMA, SYSTEM_PROMPT
from .reply import Reply, parse_reply


def post_json(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


class OllamaChat:
    FALLBACK = Reply("Ой, я задумался и потерял мысль.", "sad")

    def __init__(self, model: str, url: str = "http://127.0.0.1:11434", history_turns: int = 6,
                 timeout: float = 30.0, post=None):
        self.model, self.url, self.history_turns, self.timeout = model, url, history_turns, timeout
        self.post = post or post_json
        self.history: list[tuple[str, str]] = []

    def _payload(self, text: str) -> dict:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for user, said in self.history:
            messages += [{"role": "user", "content": user}, {"role": "assistant", "content": said}]
        messages.append({"role": "user", "content": text})
        return {"model": self.model, "messages": messages, "format": REPLY_SCHEMA, "stream": False,
                "think": False, "keep_alive": "30m", "options": {"temperature": 0.7}}

    def warm(self, timeout: float = 120.0) -> bool:
        """Прогреть модель одним коротким запросом; историю не трогает."""
        payload = self._payload("Привет.")
        payload["options"] = {"num_predict": 8}
        try:
            self.post(f"{self.url}/api/chat", payload, timeout)["message"]
        except (OSError, ValueError, KeyError, TypeError):
            return False
        return True

    def ask(self, text: str) -> Reply:
        try:
            resp = self.post(f"{self.url}/api/chat", self._payload(text), self.timeout)
            reply = parse_reply(resp["message"]["content"])
        except (OSError, ValueError, KeyError, TypeError):
            return self.FALLBACK
        self.history = (self.history + [(text, reply.say)])[-self.history_turns:]
        return reply
