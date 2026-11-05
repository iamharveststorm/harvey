"""Помощник без LLM: время, дата, таймеры, напоминания, имя и факты о человеке. Вход — нормализованный текст после «Харви»."""
import math
import re
import threading
from datetime import datetime

from .memory import Memory, quoted
from .numbers import say_duration, split_clock, split_duration, with_verb
from .reply import Reply

ASK_WINDOW_S = 30.0
LATE_S = 60.0
KNOW_FACTS = 5
_WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября",
           "ноября", "декабря")
_LEFT_VERBS = ("Остался", "Осталась", "Осталось")
_PASSED_VERBS = ("Прошёл", "Прошла", "Прошло")
_LEADING_FILLER = ("мне", "что", "чтобы")
_ANSWER_FILLER = {"на", "через", "ну"}
_NOTHING_KNOWN = "Я пока ничего о тебе не знаю."
_NO_TIMERS = "Таймеров нет."


def _re(pattern: str):
    return re.compile(r"(?<!\w)(?:" + pattern + r")(?!\w)")


_CLOCK = _re(r"который (?:сейчас )?час|сколько (?:сейчас )?времени")
_DATE = _re(r"(?:какое|какой|какая)(?: сегодня)? (?:число|день|дата)")
_TIMER = _re(r"таймер\w*|засеки")
_REMIND = _re(r"напомни")
_LEFT = _re(r"сколько (?:еще )?(?:времени )?осталось")
_CANCEL = _re(r"отмени\w*")
_CANCELLABLE = _re(r"таймер\w*|напоминани\w*")
_WHO_AM_I = _re(r"как меня зовут")
_MY_NAME = _re(r"меня зовут (\w+)")
_REMEMBER = re.compile(r"^запомни(?: что)? (.+)$")
_KNOW = _re(r"что ты (?:обо мне|про меня) знаешь|что ты знаешь (?:обо мне|про меня)")
_FORGET = _re(r"забудь (?:все|всё) (?:обо мне|про меня)|забудь меня")


def _clock_text(epoch: float) -> str:
    moment = datetime.fromtimestamp(epoch)
    return f"{moment.hour}:{moment.minute:02d}"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _after_span(words: list[str], wall: float):
    """«через 20 минут …» -> (срок, секунды, остальные слова, «через 20 минут»); иначе None."""
    if "через" not in words:
        return None
    rest = [w for w in words if w != "через"]
    span = split_duration(rest)
    return span and (wall + span[0], span[0], span[1], f"через {say_duration(span[0], acc=True)}")


def _at_span(words: list[str], wall: float):
    """«в 18 30 …» -> (срок, None, остальные слова, «в 18:30»); иначе None."""
    span = split_clock(words, wall)
    return span and (span[0], None, span[1], f"в {_clock_text(span[0])}")


def _is_timer(t: dict) -> bool:
    return bool(t["seconds"]) and not t["text"]


class Assistant:
    def __init__(self, memory: Memory):
        self.memory = memory
        self._ask_until: float | None = None
        self._lock = threading.RLock()     # handle() идёт из потока ввода, due() — из цикла событий
        self._handlers = (self._cancel, self._left, self._remind, self._timer, self._clock, self._date,
                          self._who_am_i, self._my_name, self._remember, self._know, self._forget)

    def handle(self, text: str, wall: float) -> Reply | None:
        with self._lock:
            return self._handle(text, wall)

    def _handle(self, text: str, wall: float) -> Reply | None:
        pending, self._ask_until = self._ask_until, None
        if pending is not None and wall <= pending:
            answer = self._answer_duration(text, wall)
            if answer:
                return answer
        for handler in self._handlers:
            reply = handler(text, wall)
            if reply:
                return reply
        return None

    def due(self, wall: float) -> list[Reply]:
        """Сработавшие таймеры и напоминания (по порядку срока); убираются из памяти до того, как их произнесут."""
        with self._lock:
            fired = self._pop_due(wall)
        return [self._fire(t, wall) for t in fired]

    def _pop_due(self, wall: float) -> list[dict]:
        fired = sorted((t for t in self.memory.timers if t["due"] <= wall), key=lambda t: t["due"])
        if fired:
            self.memory.timers[:] = [t for t in self.memory.timers if t["due"] > wall]
            self.memory.save()
        return fired

    @staticmethod
    def _fire(t: dict, wall: float) -> Reply:
        text, seconds = t["text"], t["seconds"]
        emote = "curious" if text else "surprised"
        body = text or (with_verb(seconds, _PASSED_VERBS) if seconds else "Время пришло")
        if wall - t["due"] > LATE_S:
            return Reply(f"Пока меня не было: {_lower_first(body)}.", emote)
        return Reply(f"Напоминаю: {body}." if text else f"Динь! {body}.", emote)

    def _nearest(self) -> dict | None:
        return min(self.memory.timers, key=lambda t: t["due"], default=None)

    def _clock(self, text: str, wall: float) -> Reply | None:
        return Reply(f"Сейчас {_clock_text(wall)}.", "neutral") if _CLOCK.search(text) else None

    def _date(self, text: str, wall: float) -> Reply | None:
        if not _DATE.search(text):
            return None
        d = datetime.fromtimestamp(wall)
        return Reply(f"Сегодня {_WEEKDAYS[d.weekday()]}, {d.day} {_MONTHS[d.month - 1]}.", "neutral")

    def _set_timer(self, text: str, wall: float) -> Reply | None:
        seconds = split_duration(text.split())
        if not seconds:
            return None
        self.memory.add_timer(wall + seconds[0], None, seconds[0])
        self.memory.save()
        return Reply(f"Ставлю таймер на {say_duration(seconds[0], acc=True)}.", "happy")

    def _answer_duration(self, text: str, wall: float) -> Reply | None:
        """Ответ на «На сколько поставить таймер?»: только длительность, без чужих слов («который час» — не ответ)."""
        span = split_duration(text.split())
        if not span or set(span[1]) - _ANSWER_FILLER:
            return None
        return self._set_timer(text, wall)

    def _timer(self, text: str, wall: float) -> Reply | None:
        if not _TIMER.search(text):
            return None
        reply = self._set_timer(text, wall)
        if reply:
            return reply
        self._ask_until = wall + ASK_WINDOW_S
        return Reply("На сколько поставить таймер?", "curious")

    def _remind(self, text: str, wall: float) -> Reply | None:
        found = _REMIND.search(text)
        if not found:
            return None
        words = text[found.end():].split()
        when = self._schedule(words, wall)
        return when or Reply("Когда напомнить? Скажи, например: через десять минут.", "curious")

    def _schedule(self, words: list[str], wall: float) -> Reply | None:
        found = _after_span(words, wall) or _at_span(words, wall)
        if not found:
            return None
        due, seconds, rest, when = found
        while rest and rest[0] in _LEADING_FILLER:
            rest.pop(0)
        what = " ".join(rest) or None
        self.memory.add_timer(due, what, seconds)
        self.memory.save()
        return Reply(f"Хорошо, напомню {when}: {what}." if what else f"Хорошо, напомню {when}.", "happy")

    def _left(self, text: str, wall: float) -> Reply | None:
        if not _LEFT.search(text):
            return None
        nearest = self._nearest()
        if not nearest:
            return Reply(_NO_TIMERS, "neutral")
        return Reply(with_verb(max(math.ceil(nearest["due"] - wall), 0), _LEFT_VERBS) + ".", "neutral")

    @staticmethod
    def _describe(t: dict) -> str:
        if _is_timer(t):
            return f"Остался таймер на {say_duration(t['seconds'])}."
        return f"Осталось напоминание на {_clock_text(t['due'])}."

    def _cancel(self, text: str, wall: float) -> Reply | None:
        if not (_CANCEL.search(text) and _CANCELLABLE.search(text)):
            return None
        if not self.memory.timers:
            return Reply(_NO_TIMERS, "neutral")
        if "все" in text.split():
            self.memory.timers.clear()
            self.memory.save()
            return Reply("Отменил все.", "neutral")
        self.memory.timers.remove(self._nearest())
        self.memory.save()
        nearest = self._nearest()
        return Reply("Отменил." + (f" {self._describe(nearest)}" if nearest else ""), "neutral")

    def _who_am_i(self, text: str, wall: float) -> Reply | None:
        if not _WHO_AM_I.search(text):
            return None
        name = self.memory.name
        return Reply(f"Тебя зовут {name}." if name else "Я пока не знаю, как тебя зовут.", "neutral")

    def _my_name(self, text: str, wall: float) -> Reply | None:
        found = _MY_NAME.search(text)
        if not found:
            return None
        self.memory.name = found.group(1).capitalize()
        self.memory.save()
        return Reply(f"Приятно познакомиться, {self.memory.name}!", "love")

    def _remember(self, text: str, wall: float) -> Reply | None:
        found = _REMEMBER.match(text)
        if not found:
            return None
        if found.group(1) not in self.memory.facts:
            self.memory.facts.append(found.group(1))
            self.memory.save()
        return Reply("Запомнил.", "happy")

    def _know(self, text: str, wall: float) -> Reply | None:
        if not _KNOW.search(text):
            return None
        parts = [f"Тебя зовут {self.memory.name}."] if self.memory.name else []
        if self.memory.facts:
            parts.append(f"Я помню твои слова: {quoted(self.memory.facts[-KNOW_FACTS:])}.")
        return Reply(" ".join(parts) or _NOTHING_KNOWN, "neutral")

    def _forget(self, text: str, wall: float) -> Reply | None:
        if not _FORGET.search(text):
            return None
        self.memory.name, self.memory.facts = None, []
        self.memory.save()
        return Reply("Хорошо, забыл.", "neutral")
