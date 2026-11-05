"""deploy.py: какие файлы уходят на Pi, как они упакованы и какие команды ssh запускаются. Настоящий ssh не вызывается."""
import io
import tarfile
from pathlib import Path

from setup import deploy

GC = "документы/GC9D01 — код запуска Waveshare 0.71.txt"


def tree(root: Path, with_calib: bool):
    names = ["код/голова/harvey_head/head.py", "код/голова/harvey_head/mini_geometry.json",
             "код/голова/harvey_head/__pycache__/head.cpython-312.pyc", "код/голова/harvey_head/x.pyc",
             "код/голова/setup/deploy.py", "код/голова/setup/__pycache__/a.pyc",
             "код/голова/tests/test_x.py", "код/прошивка/rp2350/link.py", "код/прошивка/rp2350/main.py", GC]
    if with_calib:
        names.append("код/голова/servo_calib.json")
    for n in names:
        p = root / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")


def rel(paths):
    return {p.as_posix() for p in paths}


def test_files_selects_head_and_dependencies(tmp_path):
    tree(tmp_path, with_calib=False)
    got = rel(deploy.files(tmp_path))
    assert got == {"код/голова/harvey_head/head.py", "код/голова/harvey_head/mini_geometry.json",
                   "код/голова/setup/deploy.py", "код/прошивка/rp2350/link.py", GC}


def test_files_includes_calibration_when_present(tmp_path):
    tree(tmp_path, with_calib=True)
    assert "код/голова/servo_calib.json" in rel(deploy.files(tmp_path))


def test_make_tar_keeps_utf8_names(tmp_path):
    tree(tmp_path, with_calib=False)
    data = deploy.make_tar(tmp_path, deploy.files(tmp_path))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        names = t.getnames()
        assert "код/голова/harvey_head/head.py" in names and GC in names
        assert t.extractfile(GC).read() == b"x"


def test_ssh_commands_install():
    assert deploy.ssh_commands("harvey.local", "pc.local", True) == [
        ["ssh", "harvey.local", "mkdir -p ~/harvey && tar xzf - -C ~/harvey"],
        ["ssh", "-t", "harvey.local", "sudo python3 ~/harvey/код/голова/setup/provision.py --apply --brain pc.local"]]


def test_ssh_commands_without_install():
    assert len(deploy.ssh_commands("harvey.local", "pc.local", False)) == 1


def test_main_pipes_tar_to_first_ssh(tmp_path, monkeypatch):
    tree(tmp_path, with_calib=False)
    monkeypatch.setattr(deploy, "repo_root", lambda: tmp_path)
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw))
        return type("R", (), {"returncode": 0})()
    assert deploy.main(["harvey.local", "--brain", "pc.local", "--install"], run=run) == 0
    assert len(calls) == 2
    assert calls[0][0][:2] == ["ssh", "harvey.local"] and isinstance(calls[0][1]["input"], bytes)
    assert "input" not in calls[1][1]


def test_main_stops_on_failure(tmp_path, monkeypatch):
    tree(tmp_path, with_calib=False)
    monkeypatch.setattr(deploy, "repo_root", lambda: tmp_path)
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        return type("R", (), {"returncode": 255})()
    assert deploy.main(["h", "--brain", "b", "--install"], run=run) == 255
    assert len(calls) == 1


def test_default_brain_is_this_pc(monkeypatch):
    monkeypatch.setattr(deploy.socket, "gethostname", lambda: "MY-PC")
    assert deploy.default_brain() == "my-pc.local"


def test_repo_root_has_project_files():
    assert (deploy.repo_root() / GC).exists() or (deploy.repo_root().resolve() / GC).exists()
