"""Слово пробуждения — по распознанному тексту, по звучанию: ASR слышит «Харви» как карви/корве/харбе…"""
import re

_PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)
_CLASS = {**dict.fromkeys("хкгф", "K"), **dict.fromkeys("вб", "V"), "р": "R",
          **dict.fromkeys("ао", "A"), **dict.fromkeys("иейыэ", "I")}
NAME_KEY = "KARVI"
_PREFIXES = (("wake", "up"), ("вейк", "ап"))


def normalize(text: str) -> str:
    text = _PUNCT.sub(" ", text.lower().replace("ё", "е"))
    return " ".join(text.split())


def sound_key(word: str) -> str:
    """Грубый звуковой ключ: похожие согласные и гласные в один класс, подряд идущие одинаковые сливаются."""
    key = ""
    for ch in word.lower().replace("ё", "е"):
        if ch in "ьъ":
            continue
        cls = _CLASS.get(ch, ch)
        if not key or key[-1] != cls:
            key += cls
    return key


def _is_name(word: str) -> bool:
    return word == "harvey" or sound_key(word) == NAME_KEY


def split_wake(text: str) -> tuple[bool, str]:
    """(найдено ли имя, нормализованный остаток без него и без «wake up» / «вейк ап» перед ним)."""
    words = normalize(text).split()
    for i, word in enumerate(words):
        if _is_name(word):
            start = i - 2 if tuple(words[max(i - 2, 0):i]) in _PREFIXES else i
            return True, " ".join(words[:start] + words[i + 1:])
    return False, " ".join(words)
