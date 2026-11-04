from harvey_brain.dialog import Dialog
from harvey_brain.reply import Reply


class FakeLLM:
    def __init__(self):
        self.asked = []

    def ask(self, text):
        self.asked.append(text)
        return Reply("Хорошо.", "happy")


def test_sleeping_ignores_speech():
    llm = FakeLLM()
    d = Dialog(llm)
    assert d.on_text("как дела", 0) is None
    assert llm.asked == [] and not d.awake(0)


def test_wake_only():
    d = Dialog(FakeLLM())
    assert d.on_text("Харви", 0) == Reply("Да?", "curious")
    assert d.awake(1)


def test_quick_command_skips_llm():
    llm = FakeLLM()
    r = Dialog(llm).on_text("Харви, иди домой", 0)
    assert r.goal == "home" and llm.asked == []


def test_follow_up_window():
    llm = FakeLLM()
    d = Dialog(llm, follow_s=8)
    d.on_text("Харви", 0)
    assert d.on_text("как дела", 3).say == "Хорошо."
    assert llm.asked == ["как дела"]
    assert d.on_text("как дела", 3 + 9) is None


def test_wake_with_question_goes_to_llm():
    llm = FakeLLM()
    Dialog(llm).on_text("Харви, что ты умеешь?", 0)
    assert llm.asked == ["что ты умеешь"]


def test_head_events_and_rate_limit():
    d = Dialog(FakeLLM())
    assert d.on_head({"t": "ev", "ev": "lifted"}, 0).emote == "surprised"
    assert d.on_head({"t": "ev", "ev": "lifted"}, 5) is None
    assert d.on_head({"t": "ev", "ev": "lifted"}, 21).say.startswith("Ой!")
    assert d.on_head({"t": "ev", "ev": "docked"}, 5).say == "Ммм, зарядка."
    assert d.on_head({"t": "ev", "ev": "bat_low"}, 5).emote == "tired"
    assert d.on_head({"t": "ev", "ev": "other"}, 5) is None
    assert d.on_head({"t": "link", "brain": "up"}, 5) is None


def test_silence_while_awake_is_ignored():
    llm = FakeLLM()
    d = Dialog(llm)
    d.on_text("Харви", 0)
    assert d.on_text("  ", 1) is None and llm.asked == []


class GoalLLM:
    def ask(self, text):
        return Reply("Ок.", "happy", "look" if "привет" in text else "hand")


def test_small_talk_goal_dropped():
    r = Dialog(GoalLLM()).on_text("Харви, привет", 0)
    assert r == Reply("Ок.", "happy", None)


def test_action_request_keeps_goal():
    r = Dialog(GoalLLM()).on_text("Харви, подойди поближе", 0)
    assert r.goal == "hand"


def test_awake_window_boundary():
    d = Dialog(FakeLLM(), follow_s=8)
    d.on_text("Харви", 0)
    assert d.awake(7.9) and not d.awake(8)


def test_event_gap_boundary():
    d = Dialog(FakeLLM())
    d.on_head({"t": "ev", "ev": "docked"}, 0)
    assert d.on_head({"t": "ev", "ev": "docked"}, 19.9) is None
    assert d.on_head({"t": "ev", "ev": "docked"}, 20) is not None
