"""Слово пробуждения — по распознанному тексту."""
import re

WAKE = ("харви", "харвей", "харвий", "harvey", "wake up harvey", "вейк ап харви")
_PUNCT = re.compile(r"[^\w\s]|_", re.UNICODE)


def normalize(text: str) -> str:
    text = _PUNCT.sub(" ", text.lower().replace("ё", "е"))
    return " ".join(text.split())


def split_wake(text: str) -> tuple[bool, str]:
    """(найдено ли слово, нормализованный остаток без него). Фраза ищется целыми словами, длинные — первыми."""
    padded = f" {normalize(text)} "
    for phrase in sorted(WAKE, key=len, reverse=True):
        needle = f" {phrase} "
        if needle in padded:
            return True, " ".join(padded.replace(needle, " ", 1).split())
    return False, padded.strip()
