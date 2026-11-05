from harvey_brain.reply import Reply, parse_reply, to_head, trim_say


def test_json_reply():
    assert parse_reply('{"say":"Привет!","emote":"happy","goal":"none"}') == Reply("Привет!", "happy", None)


def test_unknown_emote_and_goal():
    r = parse_reply('{"say":"Да","emote":"angry","goal":"fly"}')
    assert r == Reply("Да", "neutral", None)


def test_think_block_dropped():
    assert parse_reply('<think>x</think>{"say":"Да","emote":"love","goal":"look"}') == Reply("Да", "love", "look")


def test_plain_text():
    assert parse_reply("Просто текст") == Reply("Просто текст")


def test_json_inside_text():
    r = parse_reply('Вот: {"say":"Ок","emote":"happy","goal":"home"} всё')
    assert r == Reply("Ок", "happy", "home")


def test_broken_json_is_text_and_empty_is_blank():
    assert parse_reply("{не json").say == "{не json"
    assert parse_reply("").say == ""
    assert parse_reply('{"say":5}').say == ""


def test_trim_three_sentences():
    assert trim_say("Раз. Два! Три?") == "Раз. Два!"


def test_trim_long_without_period():
    out = trim_say("а" * 500)
    assert len(out) <= 300 and out.endswith("…")


def test_parse_trims():
    r = parse_reply('{"say":"Раз. Два. Три.","emote":"happy","goal":"none"}')
    assert r.say == "Раз. Два."


def test_to_head():
    assert to_head(Reply("x", "sad", "home")) == [{"t": "emote", "name": "sad", "s": 3.0}, {"t": "goal", "goal": "home"}]
    assert to_head(Reply("x", "happy")) == [{"t": "emote", "name": "happy", "s": 3.0}]


def test_prompt_says_goal_none_by_default():
    from harvey_brain.persona import SYSTEM_PROMPT
    assert "none, если человек не просил" in SYSTEM_PROMPT


def test_trim_exact_limit_untouched():
    assert trim_say("а" * 300) == "а" * 300


def test_to_head_turn_replaces_the_goal():
    assert to_head(Reply("x", "curious", None, 12.5)) == [{"t": "emote", "name": "curious", "s": 3.0},
                                                          {"t": "turn", "deg": 12.5}]
    assert to_head(Reply("x", "curious", None, 0.0))[-1] == {"t": "turn", "deg": 0.0}
