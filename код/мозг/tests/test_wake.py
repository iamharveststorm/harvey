import pytest

from harvey_brain.wake import normalize, sound_key, split_wake


@pytest.mark.parametrize("text,expected", [
    ("Харви, иди домой", (True, "иди домой")),
    ("ХАРВИ!", (True, "")),
    ("Wake up, Harvey", (True, "")),
    ("привет харвей как дела", (True, "привет как дела")),
    ("Харвиус", (False, "харвиус")),
    ("открой архив", (False, "открой архив")),
    ("Вейк ап Харви, стоп", (True, "стоп")),
])
def test_split_wake(text, expected):
    assert split_wake(text) == expected


def test_normalize():
    assert normalize("  Ёлка,  ПРИВЕТ!! ") == "елка привет"


@pytest.mark.parametrize("text", [
    "карви иди домой", "харви иди домой", "карве иди домой", "корви иди домой", "харве иди домой",
    "корве иди домой", "харбе иди домой", "фарви иди домой", "гарви иди домой", "харвей иди домой",
    "Wake up, Harvey, иди домой", "вейк ап харви, иди домой", "иди домой, Харви!",
])
def test_name_by_sound(text):
    assert split_wake(text) == (True, "иди домой")


@pytest.mark.parametrize("word", ["архив", "харвиус", "корова", "карие", "кафе", "горб", "открой архив"])
def test_not_the_name(word):
    assert split_wake(word)[0] is False


@pytest.mark.parametrize("word,key", [("харвей", "KARVI"), ("Корве", "KARVI"), ("архив", "ARKIV"), ("ёлка", "IлKA")])
def test_sound_key(word, key):
    assert sound_key(word) == key

