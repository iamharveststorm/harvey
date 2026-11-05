from datetime import datetime

import pytest

from harvey_brain.numbers import parse_clock, parse_duration, parse_number, plural, say_duration, with_verb


def at(h, m=0, day=5):
    return datetime(2026, 11, day, h, m).timestamp()


@pytest.mark.parametrize("text,seconds", [
    ("10 минут", 600),
    ("десять минут", 600),
    ("двадцать пять минут", 1500),
    ("двадцать пять секунд", 25),
    ("1 час 20 минут", 4800),
    ("час", 3600),
    ("полчаса", 1800),
    ("полтора часа", 5400),
    ("полторы минуты", 90),
    ("пару минут", 120),
    ("одну минуту", 60),
    ("две минуты", 120),
    ("на пять минут позвонить", 300),
    ("45 секунд", 45),
])
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("text", ["", "привет", "позвонить маме"])
def test_no_duration(text):
    assert parse_duration(text) is None


def test_parse_number_words_and_digits():
    assert parse_number(["так", "двадцать", "пять", "минут"], 1) == (25, 3)
    assert parse_number(["25", "минут"], 0) == (25, 1)
    assert parse_number(["пару", "минут"], 0) == (2, 1)
    assert parse_number(["привет"], 0) == (None, 0)
    assert parse_number([], 0) == (None, 0)


@pytest.mark.parametrize("text,wall,expect", [
    ("в 18:30", at(14), at(18, 30)),
    ("в 18 30", at(14), at(18, 30)),
    ("в семь вечера", at(10), at(19)),
    ("в 7 вечера", at(10), at(19)),
    ("в восемь утра", at(20), at(8, day=6)),
    ("в 12 дня", at(9), at(12)),
    ("в 7", at(20), at(7, day=6)),          # уже прошло -> завтра, а не «в прошлом»
    ("в 7 вечера", at(20), at(19, day=6)),
    ("в 7", at(5), at(7)),
    ("в семь", at(5), at(7)),
    ("в 12 ночи", at(20), at(0, day=6)),
    ("напомни в 18 30 позвонить", at(14), at(18, 30)),
])
def test_parse_clock(text, wall, expect):
    assert parse_clock(text, wall) == expect


@pytest.mark.parametrize("text", ["позвонить маме", "в 25", "в 7 75", "в окно"])
def test_no_clock(text):
    assert parse_clock(text, at(10)) is None


def test_clock_equal_to_now_is_tomorrow():
    assert parse_clock("в 14", at(14)) == at(14, day=6)


@pytest.mark.parametrize("n,word", [(1, "a"), (2, "b"), (4, "b"), (5, "c"), (11, "c"), (12, "c"),
                                    (21, "a"), (22, "b"), (111, "c"), (0, "c")])
def test_plural(n, word):
    assert plural(n, "a", "b", "c") == word


@pytest.mark.parametrize("seconds,said", [
    (4800, "1 час 20 минут"), (120, "2 минуты"), (45, "45 секунд"), (60, "1 минута"),
    (7200, "2 часа"), (18000, "5 часов"), (0, "0 секунд"), (3601, "1 час 1 секунда"), (89.6, "1 минута 30 секунд"),
])
def test_say_duration(seconds, said):
    assert say_duration(seconds) == said


def test_say_duration_accusative_for_one():
    assert say_duration(60, acc=True) == "1 минуту"
    assert say_duration(21, acc=True) == "21 секунду"
    assert say_duration(3600, acc=True) == "1 час"


@pytest.mark.parametrize("seconds,said", [
    (60, "Прошла 1 минута"), (120, "Прошло 2 минуты"), (300, "Прошло 5 минут"),
    (3600, "Прошёл 1 час"), (7200, "Прошло 2 часа"), (1, "Прошла 1 секунда"),
    (4800, "Прошло 1 час 20 минут"), (660, "Прошло 11 минут"), (1260, "Прошла 21 минута"),
])
def test_with_verb(seconds, said):
    assert with_verb(seconds, ("Прошёл", "Прошла", "Прошло")) == said
