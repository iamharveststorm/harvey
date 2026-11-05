from datetime import datetime

import pytest

from harvey_brain.assistant import Assistant
from harvey_brain.memory import Memory


def at(h, m=0, s=0, day=5):
    return datetime(2026, 11, day, h, m, s).timestamp()


def make(tmp_path):
    m = Memory(tmp_path / "memory.json")
    m.load()
    return Assistant(m), m


def reload(m):
    other = Memory(m.path)
    other.load()
    return other


def say(a, text, wall):
    r = a.handle(text, wall)
    return r and r.say


def test_time_and_date(tmp_path):
    a, _ = make(tmp_path)
    assert say(a, "который час", at(14, 5)) == "Сейчас 14:05."
    assert say(a, "сколько сейчас времени", at(9, 7)) == "Сейчас 9:07."
    assert say(a, "какое сегодня число", at(10)) == "Сегодня четверг, 5 ноября."
    assert say(a, "какой сегодня день", at(10, day=8)) == "Сегодня воскресенье, 8 ноября."


def test_unknown_goes_to_llm(tmp_path):
    a, _ = make(tmp_path)
    assert a.handle("как дела", at(10)) is None
    assert a.handle("", at(10)) is None


def test_timer_set_and_fire(tmp_path):
    a, m = make(tmp_path)
    r = a.handle("поставь таймер на десять минут", at(10))
    assert (r.say, r.emote) == ("Ставлю таймер на 10 минут.", "happy")
    assert m.timers[0]["due"] == at(10, 10)
    assert a.due(at(10, 9)) == []
    fired = a.due(at(10, 10, 5))
    assert [(r.say, r.emote) for r in fired] == [("Динь! Прошло 10 минут.", "surprised")]
    assert a.due(at(10, 30)) == [] and m.timers == []


@pytest.mark.parametrize("phrase,said", [
    ("таймер на одну минуту", ("Ставлю таймер на 1 минуту.", "Динь! Прошла 1 минута.")),
    ("засеки две минуты", ("Ставлю таймер на 2 минуты.", "Динь! Прошло 2 минуты.")),
    ("таймер на пять минут", ("Ставлю таймер на 5 минут.", "Динь! Прошло 5 минут.")),
    ("таймер на час", ("Ставлю таймер на 1 час.", "Динь! Прошёл 1 час.")),
])
def test_timer_phrase_agreement(tmp_path, phrase, said):
    a, m = make(tmp_path)
    assert say(a, phrase, at(10)) == said[0]
    assert a.due(m.timers[0]["due"])[0].say == said[1]


def test_timer_without_duration_asks_then_sets(tmp_path):
    a, m = make(tmp_path)
    r = a.handle("поставь таймер", at(10))
    assert (r.say, r.emote) == ("На сколько поставить таймер?", "curious")
    assert say(a, "на десять минут", at(10, 0, 20)) == "Ставлю таймер на 10 минут."
    assert len(m.timers) == 1
    assert a.handle("на десять минут", at(10, 0, 25)) is None        # вопрос закрыт


def test_timer_question_expires_and_is_dropped(tmp_path):
    a, m = make(tmp_path)
    a.handle("таймер", at(10))
    assert a.handle("на десять минут", at(10, 0, 31)) is None
    a.handle("таймер", at(10))
    assert say(a, "который час", at(10, 0, 5)) == "Сейчас 10:00."      # другая просьба отменяет вопрос
    assert a.handle("на десять минут", at(10, 0, 6)) is None
    assert m.timers == []


def test_remind_after_and_at(tmp_path):
    a, m = make(tmp_path)
    assert say(a, "напомни через полчаса выключить чайник", at(10)) == "Хорошо, напомню через 30 минут: выключить чайник."
    assert m.timers[0]["due"] == at(10, 30) and m.timers[0]["text"] == "выключить чайник"
    assert say(a, "напомни мне в 18 30 позвонить маме", at(10)) == "Хорошо, напомню в 18:30: позвонить маме."
    assert say(a, "напомни через 20 минут", at(10)) == "Хорошо, напомню через 20 минут."
    assert say(a, "напомни в 7 вечера позвонить маме", at(10)) == "Хорошо, напомню в 19:00: позвонить маме."
    assert [r.say for r in a.due(at(10, 20, 30))] == ["Динь! Прошло 20 минут."]
    assert [r.say for r in a.due(at(10, 30, 30))] == ["Напоминаю: выключить чайник."]


def test_remind_evening_7_is_tomorrow(tmp_path):
    a, m = make(tmp_path)
    assert say(a, "напомни в 7 принять таблетки", at(20)) == "Хорошо, напомню в 7:00: принять таблетки."
    assert m.timers[0]["due"] == at(7, day=6)


def test_remind_without_when(tmp_path):
    a, m = make(tmp_path)
    assert "Когда" in say(a, "напомни позвонить маме", at(10)) and m.timers == []


def test_reminder_fired_emote(tmp_path):
    a, _ = make(tmp_path)
    a.handle("напомни через 5 минут позвонить маме", at(10))
    r = a.due(at(10, 5))[0]
    assert (r.say, r.emote) == ("Напоминаю: позвонить маме.", "curious")


def test_overdue_after_restart_fires_once(tmp_path):
    a, m = make(tmp_path)
    a.handle("напомни через 5 минут позвонить маме", at(10))
    a.handle("таймер на десять минут", at(10))
    b, _ = make(tmp_path)                                        # Харви выключили и включили
    first = [r.say for r in b.due(at(12))]
    assert first == ["Пока меня не было: позвонить маме.", "Пока меня не было: прошло 10 минут."]
    c, _ = make(tmp_path)
    assert c.due(at(12, 1)) == [] and b.due(at(12, 1)) == []


def test_slightly_late_is_normal(tmp_path):
    a, _ = make(tmp_path)
    a.handle("таймер на одну минуту", at(10))
    assert a.due(at(10, 1, 50))[0].say == "Динь! Прошла 1 минута."


def test_how_much_left(tmp_path):
    a, _ = make(tmp_path)
    assert say(a, "сколько осталось", at(10)) == "Таймеров нет."
    a.handle("таймер на десять минут", at(10))
    a.handle("таймер на час", at(10))
    assert say(a, "сколько осталось", at(10, 3)) == "Осталось 7 минут."
    a.handle("таймер на одну минуту", at(10, 3))
    assert say(a, "сколько еще осталось", at(10, 3, 30)) == "Осталось 30 секунд."


def test_cancel_nearest_and_says_what_remains(tmp_path):
    a, m = make(tmp_path)
    a.handle("таймер на пять минут", at(10))
    a.handle("напомни в 18 30 позвонить маме", at(10))
    assert say(a, "отмени таймер", at(10, 1)) == "Отменил. Осталось напоминание на 18:30."
    assert len(m.timers) == 1
    assert say(a, "отмени напоминание", at(10, 1)) == "Отменил."
    assert say(a, "отмени таймер", at(10, 1)) == "Таймеров нет."


def test_cancel_two_timers_names_the_remaining(tmp_path):
    a, m = make(tmp_path)
    a.handle("таймер на пять минут", at(10))
    a.handle("таймер на десять минут", at(10))
    assert say(a, "отмени таймер", at(10)) == "Отменил. Остался таймер на 10 минут."
    assert m.timers[0]["seconds"] == 600


def test_cancel_all(tmp_path):
    a, m = make(tmp_path)
    a.handle("таймер на пять минут", at(10))
    a.handle("таймер на десять минут", at(10))
    assert say(a, "отмени все таймеры", at(10)) == "Отменил все."
    assert m.timers == [] and say(a, "отмени все таймеры", at(10)) == "Таймеров нет."


def test_name(tmp_path):
    a, m = make(tmp_path)
    assert say(a, "как меня зовут", at(10)) == "Я пока не знаю, как тебя зовут."
    r = a.handle("меня зовут аня", at(10))
    assert (r.say, r.emote) == ("Приятно познакомиться, Аня!", "love")
    assert say(a, "как меня зовут", at(10)) == "Тебя зовут Аня."
    assert "Аня" in m.about() and reload(m).name == "Аня"


def test_remember_know_forget(tmp_path):
    a, m = make(tmp_path)
    assert say(a, "что ты обо мне знаешь", at(10)) == "Я пока ничего о тебе не знаю."
    assert say(a, "запомни что я люблю чай", at(10)) == "Запомнил."
    assert say(a, "запомни у меня есть кот", at(10)) == "Запомнил."
    a.handle("меня зовут аня", at(10))
    a.handle("таймер на пять минут", at(10))
    know = say(a, "что ты знаешь обо мне", at(10))
    assert know == "Тебя зовут Аня. Я помню твои слова: «я люблю чай»; «у меня есть кот»."
    assert reload(m).facts == ["я люблю чай", "у меня есть кот"]
    assert say(a, "забудь все обо мне", at(10)) == "Хорошо, забыл."
    assert (m.name, m.facts) == (None, []) and len(m.timers) == 1
    assert reload(m).facts == []
    assert say(a, "что ты обо мне знаешь", at(10)) == "Я пока ничего о тебе не знаю."


def test_know_lists_at_most_five_latest_facts(tmp_path):
    a, m = make(tmp_path)
    for i in range(8):
        a.handle(f"запомни факт{i}", at(10))
    know = say(a, "что ты обо мне знаешь", at(10))
    assert "факт7" in know and "факт3" in know and "факт2" not in know
