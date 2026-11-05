"""Запуск mini_brain: аргументы, команда окна мозга, цикл без окна и с поддельным окном MuJoCo (окон в тестах нет)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
import mini_brain as mb  # noqa: E402


class FakeBrain:
    def __init__(self, host="127.0.0.1", port=8765):
        self.port, self.started, self.closed, self.connected = port, False, False, False

    def start(self):
        self.started = True

    def poll(self):
        return []

    def offer(self, msg):
        pass

    def close(self, timeout=2.0):
        self.closed = True


class FakePopen:
    made = []

    def __init__(self, cmd, **kw):
        self.cmd, self.kw, self.terminated = cmd, kw, False
        FakePopen.made.append(self)

    def terminate(self):
        self.terminated = True


class FakeViewer:
    """Окно MuJoCo: живо, пока не сделано `frames` синхронизаций; камера — как у настоящего."""

    def __init__(self, frames):
        self.frames, self.syncs, self.closed = frames, 0, False
        self.cam = type("Cam", (), {"lookat": np.zeros(3), "distance": 1.0, "elevation": 0.0, "azimuth": 0.0})()

    def is_running(self):
        return self.syncs < self.frames

    def sync(self):
        self.syncs += 1

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _reset():
    FakePopen.made = []


def test_brain_command_uses_default_venv_and_brain_dir():
    cmd, cwd = mb.brain_command(9000, env={})
    assert cmd == ["C:/venvs/harvey-brain/Scripts/python.exe", "-m", "harvey_brain", "--text", "--port", "9000"]
    assert (cwd / "harvey_brain").is_dir() and cwd.name == "мозг"


def test_brain_command_venv_from_env():
    cmd, _ = mb.brain_command(8765, env={"HARVEY_BRAIN_VENV": "D:/v"})
    assert cmd[0] == "D:/v/Scripts/python.exe"


def test_parse_args_defaults_and_flags():
    a = mb.parse_args([])
    assert (a.with_brain, a.headless, a.fast, a.port, a.seconds) == (False, False, False, 8765, None)
    a = mb.parse_args(["--with-brain", "--headless", "--fast", "--port", "9", "--seconds", "5"])
    assert (a.with_brain, a.headless, a.fast, a.port, a.seconds) == (True, True, True, 9, 5.0)


def test_headless_fast_run_exits_zero_and_closes_brain():
    brains, lines = [], []

    def factory(host, port):
        brains.append(FakeBrain(host, port))
        return brains[0]

    code = mb.main(["--headless", "--fast", "--seconds", "5"], brain_factory=factory, popen=FakePopen, out=lines.append)
    assert code == 0 and brains[0].started and brains[0].closed and FakePopen.made == []
    assert "Поведение: idle" in lines and "Мозг: не на связи" in lines


def test_with_brain_starts_console_and_terminates_it_on_exit():
    mb.main(["--with-brain", "--headless", "--fast", "--seconds", "1"], brain_factory=FakeBrain, popen=FakePopen,
            out=lambda s: None)
    (proc,) = FakePopen.made
    assert proc.cmd[1:3] == ["-m", "harvey_brain"] and proc.kw["cwd"].name == "мозг"
    assert proc.kw["creationflags"] == getattr(mb.subprocess, "CREATE_NEW_CONSOLE", 0) and proc.terminated


def test_closing_the_window_stops_everything():
    viewers, brains = [], []

    def viewer_factory(model, data):
        viewers.append(FakeViewer(frames=3))
        return viewers[0]

    def factory(host, port):
        brains.append(FakeBrain(host, port))
        return brains[0]

    code = mb.main(["--with-brain", "--fast"], brain_factory=factory, popen=FakePopen, viewer_factory=viewer_factory,
                   out=lambda s: None)
    assert code == 0 and viewers[0].syncs == 3 and viewers[0].closed
    assert brains[0].closed and FakePopen.made[0].terminated
    assert np.linalg.norm(viewers[0].cam.lookat) > 0          # камера следила за корпусом


def test_main_terminates_console_even_if_loop_raises():
    class Boom(FakeBrain):
        def poll(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        mb.main(["--with-brain", "--headless", "--fast", "--seconds", "5"], brain_factory=Boom, popen=FakePopen,
                out=lambda s: None)
    assert FakePopen.made[0].terminated
