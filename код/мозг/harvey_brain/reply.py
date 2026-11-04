"""Разбор ответа LLM: что сказать, какие глаза, какая цель. Всё, что пришло не по схеме, смягчается, а не падает."""
import json
import re
from dataclasses import dataclass

from .persona import EMOTES, GOALS

_THINK = re.compile(r"<think>.*?</think>", re.S)
_SENTENCE = re.compile(r"[^.!?]*[.!?]+|[^.!?]+$")


@dataclass
class Reply:
    say: str
    emote: str = "neutral"
    goal: str | None = None


def trim_say(text: str, sentences: int = 2, limit: int = 300) -> str:
    text = text.strip()
    parts = [p.strip() for p in _SENTENCE.findall(text) if p.strip()]
    text = " ".join(parts[:sentences]) if parts else text
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _json_object(text: str):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_reply(raw: str) -> Reply:
    text = _THINK.sub("", raw or "").strip()
    obj = _json_object(text)
    if obj is None:
        return Reply(trim_say(text))
    say = obj.get("say")
    emote, goal = obj.get("emote"), obj.get("goal")
    return Reply(
        trim_say(say) if isinstance(say, str) else "",
        emote if emote in EMOTES else "neutral",
        goal if goal in GOALS else None,
    )


def to_head(r: Reply, seconds: float = 3.0) -> list[dict]:
    msgs = [{"t": "emote", "name": r.emote, "s": seconds}]
    if r.goal:
        msgs.append({"t": "goal", "goal": r.goal})
    return msgs
