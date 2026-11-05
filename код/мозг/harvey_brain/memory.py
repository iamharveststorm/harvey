"""Память Харви: имя, факты о человеке и таймеры — один JSON-файл вне репозитория."""
import json
import os
from pathlib import Path

ABOUT_FACTS = 20


def resolve_home(arg, env, home) -> Path:
    """--home, иначе HARVEY_HOME, иначе ~/.harvey."""
    return Path(arg or env.get("HARVEY_HOME") or Path(home) / ".harvey")


def _is_timer(t) -> bool:
    return (isinstance(t, dict) and isinstance(t.get("id"), int) and isinstance(t.get("due"), (int, float))
            and isinstance(t.get("text"), (str, type(None))) and isinstance(t.get("seconds"), (int, float, type(None))))


def _valid(data) -> bool:
    return (isinstance(data, dict) and isinstance(data.get("name"), (str, type(None)))
            and isinstance(data.get("facts"), list) and all(isinstance(f, str) for f in data["facts"])
            and isinstance(data.get("timers"), list) and all(_is_timer(t) for t in data["timers"]))


class Memory:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.name: str | None = None
        self.facts: list[str] = []
        self.timers: list[dict] = []

    def load(self) -> None:
        """Прочитать файл; нет файла — пустая память; битый — откладывается в .broken, память пустая."""
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            data = None
        if not _valid(data):
            self._set_aside()
            return
        self.name, self.facts, self.timers = data["name"], data["facts"], data["timers"]

    def _set_aside(self) -> None:
        self.name, self.facts, self.timers = None, [], []
        try:
            os.replace(self.path, self.path.with_name(self.path.name + ".broken"))
        except OSError:
            pass

    def save(self) -> None:
        """Атомарно: во временный файл рядом, потом os.replace."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps({"name": self.name, "facts": self.facts, "timers": self.timers},
                                  ensure_ascii=False, indent=1), "utf-8")
        try:
            os.replace(tmp, self.path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def add_timer(self, due: float, text: str | None, seconds: float | None) -> dict:
        timer = {"id": max((t["id"] for t in self.timers), default=0) + 1,
                 "due": due, "text": text, "seconds": seconds}
        self.timers.append(timer)
        return timer

    def about(self) -> str:
        """Строка о человеке для LLM; пусто, если ничего не известно."""
        parts = [f"Собеседника зовут {self.name}."] if self.name else []
        if self.facts:
            parts.append(f"Тебя просили запомнить, дословно: {quoted(self.facts[-ABOUT_FACTS:])}.")
        return " ".join(parts)


def quoted(facts: list[str]) -> str:
    """Слова человека как есть, в кавычках: «я люблю чай»; «у меня есть кот»."""
    return "; ".join(f"«{f}»" for f in facts)
