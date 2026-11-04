import pytest

from harvey_brain.wake import normalize, split_wake


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
