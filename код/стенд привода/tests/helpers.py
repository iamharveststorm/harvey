"""Помощники тестов стенда: ответы человека и поиск замера в отчёте."""
from harvey_bench.bench import Bench


def answer(bench: Bench, replies: dict) -> list[str]:
    """Человек у стенда: на вопрос, где есть ключ из replies, отвечает значением; иначе — ответ по умолчанию.
    Возвращает список заданных вопросов."""
    asked = []

    def ask(text: str, default: str = "") -> str:
        asked.append(text)
        for key, value in replies.items():
            if key in text:
                return value
        return default

    bench.ask = ask
    return asked


def result(bench: Bench, n: str) -> dict:
    found = [r for r in bench.results if r["n"] == n]
    assert len(found) == 1, f"замер {n}: {bench.results}"
    return found[0]
