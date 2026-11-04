"""Стенд без приводов, сторона ПК: отчёт по самопроверке и проверка связи с настоящей прошивкой (Spine на имитации)."""
import bench_pc
import edge
from fakes import FakeBus, FakeI2C, FakePin, FakeVL53L4CD
from spine import Spine

NAMES = ("FL", "FR", "BL", "BR", "L", "R")


def test_files_for_the_board_include_bus_driver_station_and_imu_config():
    names = {dst for _, dst in bench_pc.board_files()}
    assert {"spine.py", "main.py", "selftest.py", "sts_bus.py", "beacon_station.py", "bmi270_config.bin"} <= names
    assert "bench_pc.py" not in names and not any(n.startswith("test_") for n in names)


def test_parse_keeps_json_lines_only():
    text = 'MicroPython v1.24\n{"check":"uart_a","ok":true,"got":68}\nTraceback...\n{"check":"done","ok":true}\n'
    assert [r["check"] for r in bench_pc.parse(text)] == ["uart_a", "done"]


def test_report_says_what_to_check_when_a_jumper_is_missing():
    lines = bench_pc.report([{"check": "uart_a", "ok": True, "got": 68, "sent": 68, "bad": 0},
                             {"check": "uart_b", "ok": False, "got": 0, "sent": 68, "bad": 0},
                             {"check": "beacon", "ok": False, "counts": [[30, 30], [0, 0], [30, 30]], "silent": ["center"],
                              "expect": 30},
                             {"check": "done", "ok": True}])
    text = "\n".join(lines)
    assert "ОК  шина A" in text and "НЕТ шина B" in text and "GP4 → GP5" in text and "GP28" in text


def test_report_notices_an_unfinished_selftest():
    assert any("не дошла до конца" in line for line in bench_pc.report([{"check": "uart_a", "ok": True}]))


# ---------- связь с прошивкой ----------
class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FirmwareSerial:
    """USB к плате, на которой крутится настоящий Spine (датчики края — имитации, приводов нет)."""

    def __init__(self, clock, silent=False):
        self.clock, self.inbox, self.outbox, self.silent = clock, b"", bytearray(), silent
        pins = [FakePin(0) for _ in NAMES]
        arr = edge.EdgeArray(FakeI2C(*[FakeVL53L4CD(p, dist=80) for p in pins]), pins, NAMES)
        port = self

        class Port:
            def read(self):
                data, port.inbox = port.inbox, b""
                return data

            def write(self, data):
                port.outbox += data
        self.spine = Spine(Port(), {"A": FakeBus(), "B": FakeBus(), "C": FakeBus()}, edge=arr,
                           cfg={"telemetry_ms": 50, "edge_names": NAMES}, clock=lambda: int(self.clock.t * 1000))

    def write(self, data):
        self.inbox += data

    def run(self, sec):
        for _ in range(round(sec / 0.005)):
            self.clock.t += 0.005
            if not self.silent:
                self.spine.step()

    def read_all(self):
        data, self.outbox = bytes(self.outbox), bytearray()
        return data


def test_link_with_the_firmware_hello_telemetry_targets_and_positions():
    clock = Clock()
    ser = FirmwareSerial(clock)
    res = {r["check"]: r for r in bench_pc.link_check(ser, clock, ser.run)}
    assert res["hello"]["ok"] and res["hello"]["version"] == 1
    assert res["telemetry"]["ok"] and 18 <= res["telemetry"]["hz"] <= 22
    assert res["targets"]["ok"] and res["positions"]["ok"] and len(res["positions"]["missing"]) == 28


def test_link_with_a_silent_board():
    clock = Clock()
    ser = FirmwareSerial(clock, silent=True)
    res = {r["check"]: r for r in bench_pc.link_check(ser, clock, ser.run)}
    assert not res["hello"]["ok"] and not res["telemetry"]["ok"]


def test_all_servo_ids_are_asked():
    ids = bench_pc.SERVO_IDS
    assert len(ids) == 28 and ids[0] == 11 and 63 in ids and 84 in ids and ids[-1] == 92


def test_link_report_explains_a_silent_board():
    lines = bench_pc.link_report([{"check": "hello", "ok": False, "version": None, "missing": None},
                                  {"check": "telemetry", "ok": True, "hz": 20.0}])
    assert lines[0].startswith("НЕТ hello") and "main.py не запустился" in lines[0] and lines[1].startswith("ОК  telemetry")
