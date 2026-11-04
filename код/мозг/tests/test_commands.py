import pytest

from harvey_brain.commands import quick_reply, wants_action


@pytest.mark.parametrize("text,goal", [
    ("иди домой", "home"), ("на зарядку", "home"), ("заряжаться", "home"), ("на базу", "home"),
    ("посмотри на меня", "look"), ("смотри на меня", "look"),
    ("иди ко мне", "hand"), ("иди сюда", "hand"), ("к руке", "hand"),
    ("стоп", "idle"), ("стой", "idle"), ("отдыхай", "idle"), ("хватит", "idle"),
])
def test_goals(text, goal):
    assert quick_reply(text).goal == goal


def test_texts():
    assert quick_reply("иди домой").say == "Иду домой."
    assert quick_reply("иди ко мне").emote == "happy"
    assert quick_reply("посмотри на меня").emote == "curious"


def test_no_command():
    assert quick_reply("как дела") is None
    assert quick_reply("") is None


@pytest.mark.parametrize("text", ["иди сюда", "подойди поближе", "посмотри", "вернись", "домой", "заряжаться на зарядку",
                                  "ляг", "остановись", "повернись", "иди ко мне", "взгляни"])
def test_wants_action(text):
    assert wants_action(text)


@pytest.mark.parametrize("text", ["привет", "как дела", "", "что ты умеешь"])
def test_no_action_wanted(text):
    assert not wants_action(text)


@pytest.mark.parametrize("text", ["ты меня видишь", "посмотрим потом", "у тебя стойкий характер", "раздомой"])
def test_cue_inside_word_is_not_action(text):
    assert not wants_action(text)


@pytest.mark.parametrize("text", ["стопка книг", "стойкий"])
def test_command_inside_word_is_not_command(text):
    assert quick_reply(text) is None
