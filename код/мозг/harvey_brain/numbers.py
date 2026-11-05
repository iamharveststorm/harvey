"""Русские числа словами и цифрами -> длительность / время суток; склонение единиц для ответа."""
from datetime import datetime, timedelta

_ONES = dict(zip(
    ("ноль один два три четыре пять шесть семь восемь девять десять одиннадцать двенадцать тринадцать "
     "четырнадцать пятнадцать шестнадцать семнадцать восемнадцать девятнадцать").split(), range(20)))
_ONES.update({"одна": 1, "одну": 1, "одно": 1, "две": 2})
_TENS = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50}
_PAIR = "пару"

# (секунд в единице, именительный, родительный ед., родительный мн., винительный ед.)
_UNITS = (
    (3600, "час", "часа", "часов", "час"),
    (60, "минута", "минуты", "минут", "минуту"),
    (1, "секунда", "секунды", "секунд", "секунду"),
)
_UNIT_SECONDS = {form: unit[0] for unit in _UNITS for form in (*unit[1:4], unit[4])}
_HALVES = {"полтора": 1.5, "полторы": 1.5}
_HOUR_WORDS = ("час", "часа", "часов")
_PARTS = {
    "утра": lambda h: 0 if h == 12 else h,
    "утром": lambda h: 0 if h == 12 else h,
    "дня": lambda h: h + 12 if h < 12 else h,
    "вечера": lambda h: h + 12 if h < 12 else h,
    "ночи": lambda h: 0 if h == 12 else (h if h < 6 else h + 12 if h < 12 else h),
}


def words_of(text: str) -> list[str]:
    return text.lower().replace("ё", "е").replace(":", " ").split()


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _word(words: list[str], i: int) -> str:
    return words[i] if i < len(words) else ""


def _tens(words: list[str], i: int) -> tuple[int, int]:
    """«двадцать» или «двадцать пять» с позиции i."""
    ones = _ONES.get(_word(words, i + 1))
    return (_TENS[words[i]] + ones, i + 2) if ones and ones < 10 else (_TENS[words[i]], i + 1)


def parse_number(words: list[str], i: int) -> tuple[int | None, int]:
    """Число с позиции i: цифры, слова 0–59, «пару» = 2. (None, i), если числа нет."""
    word = _word(words, i)
    if word.isascii() and word.isdigit():
        return int(word), i + 1
    if word == _PAIR:
        return 2, i + 1
    if word in _TENS:
        return _tens(words, i)
    if word in _ONES:
        return _ONES[word], i + 1
    return None, i


def _component(words: list[str], i: int) -> tuple[float, int] | None:
    """Одна часть длительности с позиции i: «полчаса», «полтора часа», «20 минут», «минуту»."""
    word = words[i]
    if word == "полчаса":
        return 1800.0, i + 1
    nxt = words[i + 1] if i + 1 < len(words) else ""
    if word in _HALVES and nxt in _UNIT_SECONDS:
        return _HALVES[word] * _UNIT_SECONDS[nxt], i + 2
    n, j = parse_number(words, i)
    unit = _UNIT_SECONDS.get(words[j]) if j < len(words) else None
    if n is not None:
        return (n * unit, j + 1) if unit else None
    return (float(_UNIT_SECONDS[word]), i + 1) if word in _UNIT_SECONDS else None


def split_duration(words: list[str]) -> tuple[float, list[str]] | None:
    """(секунды, слова без длительности): первая подряд идущая цепочка частей. Нет длительности — None."""
    start, total, i = None, 0.0, 0
    while i < len(words):
        part = _component(words, i)
        if part:
            start, total, i = i if start is None else start, total + part[0], part[1]
        elif start is None:
            i += 1
        else:
            break
    return None if start is None else (total, words[:start] + words[i:])


def parse_duration(text: str) -> float | None:
    found = split_duration(words_of(text))
    return found[0] if found else None


def _day_part(words: list[str], k: int, hour: int) -> tuple[int, int]:
    """«вечера» / «утра» / «дня» / «ночи» на позиции k переводят час в 24-часовой."""
    part = _PARTS.get(_word(words, k))
    return (part(hour), k + 1) if part else (hour, k)


def _clock_at(words: list[str], j: int) -> tuple[int, int, int] | None:
    """(час, минуты, следующая позиция) для «7», «18 30», «7 вечера», «7 часов утра» с позиции j."""
    hour, k = parse_number(words, j)
    if hour is None:
        return None
    minute, k = parse_number(words, k)
    if minute is not None and minute > 59:
        return None
    k += _word(words, k) in _HOUR_WORDS
    hour, k = _day_part(words, k, hour)
    return (hour, minute or 0, k) if hour <= 23 else None


def _next_moment(hour: int, minute: int, wall: float) -> float:
    moment = datetime.fromtimestamp(wall).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return (moment + timedelta(days=1) * (moment.timestamp() <= wall)).timestamp()


def split_clock(words: list[str], wall: float) -> tuple[float, list[str]] | None:
    """(epoch ближайшего будущего момента, слова без «в 18:30»); нет времени суток — None."""
    for i, word in enumerate(words):
        spec = _clock_at(words, i + 1) if word == "в" else None
        if spec:
            return _next_moment(spec[0], spec[1], wall), words[:i] + words[spec[2]:]
    return None


def parse_clock(text: str, wall: float) -> float | None:
    found = split_clock(words_of(text), wall)
    return found[0] if found else None


def _parts(seconds: float) -> list[tuple[int, int]]:
    """[(сколько, номер единицы в _UNITS)] без нулевых; для нуля — 0 секунд."""
    left, parts = round(seconds), []
    for idx, unit in enumerate(_UNITS):
        n, left = divmod(left, unit[0])
        if n:
            parts.append((n, idx))
    return parts or [(0, 2)]


def say_duration(seconds: float, acc: bool = False) -> str:
    """«1 час 20 минут»; acc — винительный («на 1 минуту»)."""
    def one(n: int, idx: int) -> str:
        unit = _UNITS[idx]
        return f"{n} {plural(n, unit[4] if acc else unit[1], unit[2], unit[3])}"
    return " ".join(one(n, idx) for n, idx in _parts(seconds))


def with_verb(seconds: float, forms: tuple[str, str, str]) -> str:
    """Глагол в согласии с числом: forms = (муж., жен., сред.) — «Прошёл 1 час», «Прошла 1 минута», «Прошло 5 минут»."""
    parts = _parts(seconds)
    n, idx = parts[0]
    verb = plural(n, forms[0] if idx == 0 else forms[1], forms[2], forms[2]) if len(parts) == 1 else forms[2]
    return f"{verb} {say_duration(seconds)}"
