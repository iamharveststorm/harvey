"""provision.py: правка config.txt, служба systemd и план установки. Настоящие apt/systemctl/sudo не вызываются."""
import pytest

from setup import provision as pv

BOOKWORM = """# For more options and information see
# http://rptl.io/configtxt
# Some settings may impact device functionality. See link above for details

# Uncomment some or all of these to enable the optional hardware interfaces
#dtparam=i2c_arm=on
#dtparam=i2s=on
#dtparam=spi=on

# Enable audio (loads snd_bcm2835)
dtparam=audio=on

# Automatically load overlays for detected cameras
camera_auto_detect=1

[cm4]
otg_mode=1

[cm5]
dtoverlay=dwc2,dr_mode=host

[all]
"""
CONFIG = "/boot/firmware/config.txt"


class FakeFs:
    def __init__(self, files=None):
        self.files = dict(files or {})
        self.written = []

    def exists(self, path):
        return path in self.files

    def read(self, path):
        return self.files.get(path)

    def write(self, path, text):
        self.files[path] = text
        self.written.append(path)


class Runner:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return type("R", (), {"returncode": 0})()


def test_edit_config_adds_block_at_the_end_under_all():
    out = pv.edit_config(BOOKWORM)
    assert out.endswith(pv.BLOCK_END + "\n")
    head, block = out.split(pv.BLOCK_BEGIN)
    assert head.rstrip().endswith("[all]")
    for line in ("dtparam=spi=on", "dtparam=i2c_arm=on", "dtparam=i2s=on", "dtoverlay=googlevoicehat-soundcard"):
        assert line in block


def test_edit_config_adds_all_when_last_section_is_other():
    text = "[all]\ndtparam=audio=on\n\n[pi4]\narm_boost=1\n"
    out = pv.edit_config(text)
    before = out.split(pv.BLOCK_BEGIN)[0].rstrip()
    assert before.splitlines()[-1] == "[all]"
    assert "[pi4]" in before


def test_edit_config_idempotent_bytes():
    once = pv.edit_config(BOOKWORM)
    assert pv.edit_config(once) == once
    other = "[all]\n\n[pi4]\narm_boost=1\n"
    assert pv.edit_config(pv.edit_config(other)) == pv.edit_config(other)


def test_edit_config_does_not_duplicate_existing_lines():
    text = "dtparam=spi=on\ncamera_auto_detect=1\n[all]\n"
    out = pv.edit_config(text)
    assert out.count("dtparam=spi=on") == 1 and out.count("camera_auto_detect=1") == 1
    assert pv.edit_config(out) == out


def test_edit_config_commented_line_is_not_present():
    assert "dtparam=spi=on" in pv.edit_config("#dtparam=spi=on\n[all]\n").split(pv.BLOCK_BEGIN)[1]


def test_edit_config_replaces_old_block():
    old = "[all]\n" + pv.BLOCK_BEGIN + "\ndtoverlay=old\n" + pv.BLOCK_END + "\n"
    out = pv.edit_config(old)
    assert "dtoverlay=old" not in out and out.count(pv.BLOCK_BEGIN) == 1


def test_edit_config_unterminated_block_is_replaced():
    out = pv.edit_config("[all]\n" + pv.BLOCK_BEGIN + "\ndtoverlay=old\n")
    assert "dtoverlay=old" not in out and out.count(pv.BLOCK_BEGIN) == 1


def test_edit_config_all_lines_present_adds_nothing():
    text = "\n".join(pv.HARVEY_LINES) + "\n"
    assert pv.edit_config(text) == text


def test_unit_text():
    text = pv.unit_text("pi", "/home/pi")
    for line in ("After=network-online.target sound.target", "Wants=network-online.target", "User=pi",
                 "EnvironmentFile=-/etc/harvey/head.env",
                 "WorkingDirectory=/home/pi/harvey/код/голова",
                 "ExecStart=/home/pi/harvey/venv/bin/python -m harvey_head.main",
                 "Restart=always", "RestartSec=3", "WantedBy=multi-user.target"):
        assert line in text.splitlines()


def test_env_text():
    assert pv.env_text("pc.local") == "HARVEY_BRAIN_HOST=pc.local\nHARVEY_BRAIN_PORT=8765\n"


def run_plan(fs, **kw):
    runner = Runner()
    steps = pv.plan("pi", "/home/pi", "pc.local", fs=fs, run=runner, **kw)
    for step in steps:
        step.action()
    return steps, runner


def test_plan_fresh_pi_order_and_effects():
    fs = FakeFs({CONFIG: BOOKWORM})
    steps, runner = run_plan(fs)
    flat = [" ".join(c) for c in runner.calls]
    assert "apt-get install -y" in flat[0] and "python3-picamera2" in flat[0]
    assert any("venv --system-site-packages" in c for c in flat)
    assert any("pip install pyserial" in c for c in flat)
    assert flat[-2:] == ["systemctl daemon-reload", "systemctl enable harvey-head"]
    assert fs.files[CONFIG + ".harvey.bak"] == BOOKWORM
    assert pv.BLOCK_BEGIN in fs.files[CONFIG]
    assert fs.files["/etc/harvey/head.env"] == pv.env_text("pc.local")
    assert fs.files["/etc/systemd/system/harvey-head.service"] == pv.unit_text("pi", "/home/pi")
    assert all(s.description for s in steps)


def test_plan_second_run_changes_nothing():
    fs = FakeFs({CONFIG: BOOKWORM})
    run_plan(fs)
    snapshot = dict(fs.files)
    fs.written.clear()
    steps, _ = run_plan(fs)
    assert fs.files == snapshot
    assert fs.written == []
    assert not any("config.txt" in s.description for s in steps)


def test_plan_keeps_user_edited_env_and_existing_backup():
    fs = FakeFs({CONFIG: BOOKWORM, "/etc/harvey/head.env": "HARVEY_ALSA_DEVICE=x\n", CONFIG + ".harvey.bak": "orig"})
    run_plan(fs)
    assert fs.files["/etc/harvey/head.env"] == "HARVEY_ALSA_DEVICE=x\n"
    assert fs.files[CONFIG + ".harvey.bak"] == "orig"


def test_plan_missing_config_fails_clearly_when_applied():
    fs = FakeFs()
    steps = pv.plan("pi", "/home/pi", "pc.local", fs=fs, run=Runner())
    bad = [s for s in steps if "config.txt" in s.description]
    assert bad
    with pytest.raises(SystemExit, match="config.txt"):
        for s in bad:
            s.action()


def test_main_dry_run_runs_nothing(capsys):
    fs, runner = FakeFs({CONFIG: BOOKWORM}), Runner()
    assert pv.main(["--dry-run", "--brain", "pc.local"], run=runner, fs=fs, env={}) == 0
    assert runner.calls == [] and fs.written == []
    assert "apt" in capsys.readouterr().out


def test_main_default_is_dry_run():
    fs, runner = FakeFs({CONFIG: BOOKWORM}), Runner()
    assert pv.main([], run=runner, fs=fs, env={}) == 0
    assert runner.calls == [] and fs.written == []


def test_main_apply_requires_brain_and_sudo_user():
    with pytest.raises(SystemExit):
        pv.main(["--apply"], run=Runner(), fs=FakeFs(), env={"SUDO_USER": "pi"})
    with pytest.raises(SystemExit):
        pv.main(["--apply", "--brain", "pc.local"], run=Runner(), fs=FakeFs(), env={})


def test_main_apply_executes_and_says_reboot(capsys):
    fs, runner = FakeFs({CONFIG: BOOKWORM}), Runner()
    assert pv.main(["--apply", "--brain", "pc.local"], run=runner, fs=fs, env={"SUDO_USER": "pi"}) == 0
    assert runner.calls and "sudo reboot" in capsys.readouterr().out


def test_home_of_uses_system_home_or_default():
    assert pv.home_of("pi", expand=lambda p: "/srv/pi") == "/srv/pi"
    assert pv.home_of("pi", expand=lambda p: p) == "/home/pi"


def test_unit_has_no_supplementary_groups():
    assert "SupplementaryGroups" not in pv.unit_text("pi", "/home/pi")


def test_groups_to_add_keeps_order_and_skips_missing():
    assert pv.groups_to_add({"audio", "gpio", "i2c", "spi", "video", "dialout", "root"}) == [
        "gpio", "spi", "i2c", "audio", "video", "dialout"]
    assert pv.groups_to_add({"gpio", "audio"}) == ["gpio", "audio"]
    assert pv.groups_to_add(set()) == []


class MissingGroupRunner(Runner):
    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        code = 2 if cmd[:3] == ["getent", "group", "i2c"] else 0
        return type("R", (), {"returncode": code})()


def test_plan_adds_user_only_to_existing_groups(capsys):
    runner = MissingGroupRunner()
    for step in pv.plan("pi", "/home/pi", "pc.local", fs=FakeFs({CONFIG: BOOKWORM}), run=runner):
        step.action()
    added = [c[2] for c in runner.calls if c[0] == "usermod"]
    assert added == ["gpio", "spi", "audio", "video", "dialout"]
    assert all(c[-1] == "pi" for c in runner.calls if c[0] == "usermod")
    assert "нет группы i2c — пропущено" in capsys.readouterr().out


def test_dry_run_does_not_touch_groups():
    runner = Runner()
    pv.main(["--dry-run"], run=runner, fs=FakeFs({CONFIG: BOOKWORM}), env={})
    assert runner.calls == []
