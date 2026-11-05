import json

import pytest

from harvey_brain import memory as memory_mod
from harvey_brain.memory import Memory, resolve_home


def test_empty_when_no_file(tmp_path):
    m = Memory(tmp_path / "memory.json")
    m.load()
    assert (m.name, m.facts, m.timers, m.about()) == (None, [], [], "")
    assert not (tmp_path / "memory.json").exists()


def test_save_and_reload(tmp_path):
    path = tmp_path / "sub" / "memory.json"
    m = Memory(path)
    m.name, m.facts = "Аня", ["люблю чай"]
    m.add_timer(100.0, "позвонить маме", None)
    m.save()
    other = Memory(path)
    other.load()
    assert other.name == "Аня" and other.facts == ["люблю чай"]
    assert other.timers == [{"id": 1, "due": 100.0, "text": "позвонить маме", "seconds": None}]
    assert other.add_timer(200.0, None, 60.0)["id"] == 2
    assert [p.name for p in path.parent.iterdir()] == ["memory.json"]     # временного файла не осталось


def test_failed_write_keeps_old_file(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    m = Memory(path)
    m.name = "Аня"
    m.save()
    m.name = "Боря"

    def boom(*args):
        raise OSError("диск")
    monkeypatch.setattr(memory_mod.os, "replace", boom)
    with pytest.raises(OSError):
        m.save()
    assert json.loads(path.read_text("utf-8"))["name"] == "Аня"


@pytest.mark.parametrize("junk", ["{не json", "[1, 2]", '{"facts": "не список"}', '{"timers": [1]}'])
def test_broken_file_is_set_aside(tmp_path, junk):
    path = tmp_path / "memory.json"
    path.write_text(junk, "utf-8")
    m = Memory(path)
    m.load()
    assert (m.name, m.facts, m.timers) == (None, [], [])
    assert (tmp_path / "memory.json.broken").read_text("utf-8") == junk
    assert not path.exists()


def test_about(tmp_path):
    m = Memory(tmp_path / "memory.json")
    m.name, m.facts = "Аня", ["люблю чай", "есть кот"]
    assert m.about() == "Собеседника зовут Аня. Тебя просили запомнить, дословно: «люблю чай»; «есть кот»."
    m.name = None
    assert m.about() == "Тебя просили запомнить, дословно: «люблю чай»; «есть кот»."
    m.facts = [f"факт {i}" for i in range(30)]
    text = m.about()
    assert "«факт 29»" in text and "«факт 10»" in text and "«факт 9»" not in text


def test_resolve_home(tmp_path):
    assert resolve_home("X", {"HARVEY_HOME": "Y"}, tmp_path).name == "X"
    assert resolve_home(None, {"HARVEY_HOME": str(tmp_path / "Y")}, tmp_path) == tmp_path / "Y"
    assert resolve_home(None, {}, tmp_path) == tmp_path / ".harvey"
