"""check.py: разборщики вывода aplay / rpicam / ls и сводная таблица. Настоящих команд не запускается."""
import subprocess

from setup import check

APLAY = """**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi [vc4-hdmi], device 0: MAI PCM i2s-hifi-0 [MAI PCM i2s-hifi-0]
  Subdevices: 1/1
card 1: sndrpigooglevoi [snd_rpi_googlevoicehat_soundcard], device 0: Google voiceHAT SoundCard HiFi voicehat-hifi-0
  Subdevices: 1/1
"""
NO_CARDS = "aplay: device_list:274: no soundcards found...\n"
CAMERAS = "Available cameras\n-----------------\n0 : imx708_wide [4608x2592 10-bit RGGB] (/base/soc/i2c0mux/i2c@1/imx708@1a)\n"


def test_cards_names():
    assert check.cards(APLAY) == ["vc4hdmi", "sndrpigooglevoi"]


def test_cards_none():
    assert check.cards(NO_CARDS) == [] and check.cards("") == []


def test_has_spi_needs_both():
    assert check.has_spi(["/dev/spidev0.0", "/dev/spidev0.1", "/dev/null"])
    assert not check.has_spi(["/dev/spidev0.0"])
    assert not check.has_spi([])


def test_camera_found():
    assert check.camera_found(CAMERAS)
    assert not check.camera_found("No cameras available!\n")
    assert not check.camera_found("")


def test_spine_ports():
    assert check.spine_ports(["/dev/ttyACM1", "/dev/ttyS0", "/dev/ttyACM0"]) == ["/dev/ttyACM0", "/dev/ttyACM1"]
    assert check.spine_ports([]) == []


class Sock:
    closed = False

    def close(self):
        self.closed = True


def test_brain_reachable_ok():
    sock = Sock()
    ok, text = check.brain_reachable("pc.local", 8765, connect=lambda addr, timeout: sock)
    assert ok and sock.closed and "pc.local:8765" in text


def test_brain_reachable_errors_are_readable():
    for error in (ConnectionRefusedError("отказ"), TimeoutError("timed out")):
        def connect(addr, timeout, error=error):
            raise error
        ok, text = check.brain_reachable("pc.local", 8765, connect=connect)
        assert not ok
        assert text.startswith("ПК pc.local:8765 не отвечает: ") and "брандмауэр Windows?" in text


def test_parse_env_file():
    assert check.parse_env("# c\nHARVEY_BRAIN_HOST=pc.local\n\nHARVEY_ALSA_DEVICE=plughw:1,0\n") == {
        "HARVEY_BRAIN_HOST": "pc.local", "HARVEY_ALSA_DEVICE": "plughw:1,0"}


def fake_run(outputs, active="active\n", missing=()):
    def run(cmd, **kw):
        if cmd[0] in missing:
            raise FileNotFoundError(cmd[0])
        text = active if cmd[0] == "systemctl" else outputs[cmd[0]]
        return subprocess.CompletedProcess(cmd, 0, stdout=text, stderr="")
    return run


GOOD = {"aplay": APLAY, "arecord": APLAY, "rpicam-hello": CAMERAS}


def ports(pattern):
    return {"/dev/spidev*": ["/dev/spidev0.0", "/dev/spidev0.1"], "/dev/ttyACM*": ["/dev/ttyACM0"]}[pattern]


def connect_ok(addr, timeout):
    return Sock()


def run_main(capsys, run, glob=ports, connect=connect_ok):
    code = check.main(run=run, glob=glob, connect=connect, read=lambda p: "HARVEY_BRAIN_HOST=pc.local\n", env={})
    return code, capsys.readouterr().out


def test_main_all_good(capsys):
    code, out = run_main(capsys, fake_run(GOOD))
    assert code == 0 and "✗" not in out and "?" not in out and out.count("✓") == 7


def test_main_failures_give_exit_1(capsys):
    def refuse(addr, timeout):
        raise ConnectionRefusedError("отказ")
    code, out = run_main(capsys, fake_run(GOOD, active="inactive\n"), glob=lambda p: [], connect=refuse)
    assert code == 1 and out.count("✗") >= 4 and "брандмауэр Windows?" in out


def test_main_missing_command_is_unknown(capsys):
    code, out = run_main(capsys, fake_run(GOOD, missing=("rpicam-hello",)))
    assert code == 1 and "?" in out


def test_main_uses_env_file_host(capsys):
    seen = []

    def connect(addr, timeout):
        seen.append(addr)
        return Sock()
    run_main(capsys, fake_run(GOOD), connect=connect)
    assert seen == [("pc.local", 8765)]
