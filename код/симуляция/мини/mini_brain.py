"""Мозг ведёт Харви в симуляции: окно мини + «большой мозг» на ПК (harvey_brain, TCP :8765).

    (окружение C:/venvs/harvey) python mini_brain.py --with-brain     # мозг откроется в своём окне, набирайте фразы там

Цепочка настоящая: мозг -> Head + Body (как на Pi) -> Spine прошивки RP2350 в SimRobot -> робот. Голова подключается
к мозгу настоящим BrainLink в отдельном потоке (ThreadedBrain); без мозга Харви ведёт себя сам и раз в 5 с пробует снова.
"""
import argparse
import asyncio
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

import mini_behave as mb  # добавляет код/голова в sys.path
from harvey_head.behavior import Behavior
from harvey_head.body import Body
from harvey_head.gait import Gait
from harvey_head.head import Head
from harvey_head.links import BrainLink

RETRY_MAX_S = 5.0                                    # пауза между попытками подключиться к мозгу


def _find_dir(name, marker):
    for base in (Path(__file__).absolute(), Path(__file__).resolve()):
        p = base.parents[2] / name
        if (p / marker).exists():
            return p
    raise FileNotFoundError(f"не найдена код/{name}")


def brain_dir():
    return _find_dir("мозг", "harvey_brain/__main__.py")


class RetryLink(BrainLink):
    """BrainLink, который не отдаляет попытки дальше RETRY_MAX_S (у голови на Pi потолок 30 с)."""

    @staticmethod
    async def _wait(stop, seconds):
        await BrainLink._wait(stop, min(seconds, RETRY_MAX_S))


class ThreadedBrain:
    """Связь с мозгом в потоке-демоне; poll() и offer() можно звать из потока симуляции. Совместим с Head(brain=...)."""

    def __init__(self, host="127.0.0.1", port=8765):
        self.link = RetryLink(host, port)
        self._msgs = queue.SimpleQueue()
        self._loop = None
        self._stop = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    @property
    def connected(self):
        return self.link.connected

    def start(self):
        self._thread.start()
        self._ready.wait(2.0)

    def poll(self):
        out = []
        while True:
            try:
                out.append(self._msgs.get_nowait())
            except queue.Empty:
                return out

    def offer(self, msg):
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self.link.offer, msg)
        except RuntimeError:
            pass

    def close(self, timeout=2.0):
        loop, stop = self._loop, self._stop
        if loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(stop.set)
            except RuntimeError:
                pass
        if self._thread.is_alive():
            self._thread.join(timeout)

    def _run(self):
        asyncio.run(self._main())

    async def _main(self):
        self._loop, self._stop = asyncio.get_running_loop(), asyncio.Event()
        self._ready.set()
        drain, running = asyncio.ensure_future(self._drain()), asyncio.ensure_future(self.link.run(self._stop))
        await self._stop.wait()
        for task in (running, drain):                  # connect() не смотрит на stop — снимаем задачи сами
            task.cancel()
        await asyncio.gather(running, drain, return_exceptions=True)

    async def _drain(self):
        while True:
            self._msgs.put(await self.link.inbox.get())


START = (-0.15, 0.0, 0.0)
HAND = (0.067, 0.15)                                  # спереди-слева, ~0,26 м от старта, неподвижна; виден из старта (45° слева), домой не мешает
NO_LINK_AFTER_S = 1.0                                 # столько ждём связи, потом один раз пишем «не на связи»


def make_robot():
    """Стол, станция и рука (она всегда в кадре со старта: цель «hand» не уведёт Харви с края)."""
    return mb.mr.SimRobot(table=mb.HOME_TABLE, dock_pos=mb.DOCK, start=START, hand=HAND)


class Session:
    """Голова (Head + Body, как mb.run) ведёт робота; сообщения мозга — в голову перед её тиком."""

    def __init__(self, robot, brain, now_fn=time.monotonic, fast=False, sleep_fn=time.sleep):
        self.robot, self.brain, self.fast, self.now_fn, self.sleep_fn = robot, brain, fast, now_fn, sleep_fn
        port = robot.link()
        self.body = Body(port, Behavior(robot.t), Gait(), vision=lambda now: robot.vision(), now=robot.t)
        self.head = Head(port, brain=brain, body=self.body, now=robot.t)
        self.t0_wall, self.t0_sim = now_fn(), robot.t
        self._pending, self._shown, self._link = [], {"state": None, "eyes": None}, None

    @property
    def state(self):
        return self.body.behavior.state

    def step(self):
        """Один шаг физики (5 мс); на тике головы — сообщения мозга, голова, ожидание реального времени."""
        self.robot.physics()
        if round(self.robot.t / mb.mr.TICK) % mb.HEAD_EVERY:
            return
        for msg in self.brain.poll():
            self._on_brain(msg)
        self.head.tick(self.robot.t)
        self._watch()
        if not self.fast:
            ahead = (self.robot.t - self.t0_sim) - (self.now_fn() - self.t0_wall)
            if ahead > 0:
                self.sleep_fn(ahead)

    def events(self):
        """Строки для консоли, накопленные с прошлого вызова."""
        if self._link is None and self.robot.t >= NO_LINK_AFTER_S and not self.brain.connected:
            self._link = "down"
            self._pending.append("Мозг: не на связи")
        out, self._pending = self._pending, []
        return out

    def _on_brain(self, msg):
        if msg.get("t") == "link":
            state = msg.get("brain")
            if state != self._link:
                self._link = state
                self._pending.append("Мозг: на связи" if state == "up" else "Мозг: не на связи")
        self.head.on_brain(msg, self.robot.t)

    def _watch(self):
        for key, label, value in (("state", "Поведение", self.state), ("eyes", "Глаза", self.head.expression)):
            if self._shown[key] != value:
                if self._shown[key] is not None or key == "state":
                    self._pending.append(f"{label}: {value}")
                self._shown[key] = value


DEFAULT_BRAIN_VENV = "C:/venvs/harvey-brain"


def brain_command(port, env=None):
    """(команда, рабочая папка) окна мозга: harvey_brain --text в своём venv."""
    venv = (os.environ if env is None else env).get("HARVEY_BRAIN_VENV", DEFAULT_BRAIN_VENV)
    return [f"{venv}/Scripts/python.exe", "-m", "harvey_brain", "--text", "--port", str(port)], brain_dir()


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Мозг ведёт Харви в симуляции (окно MuJoCo + harvey_brain)")
    p.add_argument("--with-brain", action="store_true", help="открыть мозг в своём окне консоли и закрыть при выходе")
    p.add_argument("--headless", action="store_true", help="без окна MuJoCo, только консоль")
    p.add_argument("--fast", action="store_true", help="не ждать реального времени")
    p.add_argument("--port", type=int, default=8765, help="порт мозга (по умолчанию 8765)")
    p.add_argument("--seconds", type=float, default=None, help="остановиться через столько секунд времени симуляции")
    return p.parse_args(argv)


def open_viewer(model, data):
    from mujoco import viewer
    v = viewer.launch_passive(model, data, show_left_ui=False, show_right_ui=False)
    v.cam.distance, v.cam.elevation, v.cam.azimuth = 0.42, -20, 200
    return v


def running(robot, args, viewer):
    if args.seconds is not None and robot.t >= args.seconds:
        return False
    return viewer is None or viewer.is_running()


def run_loop(session, args, viewer, out):
    """Шаги симуляции до конца: секунды вышли или окно закрыто; консоль печатает events()."""
    robot = session.robot
    follow = robot.sim.d.body("torso").xpos
    while running(robot, args, viewer):
        session.step()
        for line in session.events():
            out(line)
        if viewer is not None and round(robot.t / mb.mr.TICK) % mb.HEAD_EVERY == 0:
            viewer.cam.lookat[:] = follow
            viewer.sync()


def shutdown(viewer, brain, console):
    for part, stop in ((viewer, "close"), (brain, "close"), (console, "terminate")):
        if part is not None:
            getattr(part, stop)()


def main(argv=None, brain_factory=ThreadedBrain, popen=subprocess.Popen, viewer_factory=open_viewer, out=print):
    args = parse_args(argv)
    robot = make_robot()
    brain = brain_factory("127.0.0.1", args.port)
    brain.start()
    console = None
    if args.with_brain:
        cmd, cwd = brain_command(args.port)
        console = popen(cmd, cwd=cwd, creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    viewer = None if args.headless else viewer_factory(robot.sim.m, robot.sim.d)
    try:
        run_loop(Session(robot, brain, fast=args.fast), args, viewer, out)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown(viewer, brain, console)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
