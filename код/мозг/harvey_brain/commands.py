"""Быстрые команды без LLM: целые слова нормализованного текста → готовый ответ."""
import re

from .reply import Reply

_COMMANDS = (
    (("домой", "на зарядку", "заряжаться", "на базу"), Reply("Иду домой.", "happy", "home")),
    (("посмотри на меня", "смотри на меня"), Reply("Смотрю!", "curious", "look")),
    (("иди ко мне", "иди сюда", "к руке"), Reply("Иду к тебе.", "happy", "hand")),
    (("стоп", "стой", "отдыхай", "хватит"), Reply("Хорошо, отдыхаю.", "neutral", "idle")),
)


def quick_reply(text: str) -> Reply | None:
    for phrases, reply in _COMMANDS:
        if any(_has(text, p) for p in phrases):
            return Reply(reply.say, reply.emote, reply.goal)
    return None

_ACTION_CUES = ("иди", "пойди", "подойди", "сходи", "вернись", "посмотри", "смотри", "взгляни", "повернись",
                "отдохни", "отдыхай", "ляг", "остановись", "стой", "домой", "зарядк*", "сюда", "ко мне")     # * — начало слова


def wants_action(text: str) -> bool:
    """Просил ли человек что-то сделать (текст — нормализованный)."""
    return any(_has(text, cue) for cue in _ACTION_CUES)


def _has(text: str, phrase: str) -> bool:
    """Фраза целыми словами; с * на конце — по началу слова («зарядк*» — зарядку, зарядке)."""
    stem = phrase.rstrip("*")
    tail = "" if phrase.endswith("*") else r"(?!\w)"
    return re.search(r"(?<!\w)" + re.escape(stem) + tail, text) is not None
