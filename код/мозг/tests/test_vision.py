"""Зрение: лица в кадре (YuNet), направление на лицо, наблюдатель за лицом. Камеру не открываем."""
import math
import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from harvey_brain.vision import (Face, FaceFinder, HeadFrames, Sight, Watcher, WebcamFrames, decode, direction, gaze,
                                 head_camera)
from harvey_head import dock_tag

MODELS = Path(os.environ.get("HARVEY_MODELS") or Path.home() / ".harvey" / "models") / "vision"
MODEL = MODELS / "face_detection_yunet_2023mar.onnx"
needs_model = pytest.mark.skipif(not MODEL.exists() or not (MODELS / "test" / "messi5.jpg").exists(),
                                 reason="модель YuNet и тестовые картинки лежат вне репозитория (~/.harvey/models/vision)")

W, H = 1280, 720
K = dock_tag.camera_matrix(W, H)


def face(cx=W / 2, cy=H / 2, size=100, score=0.9):
    return Face(cx - size / 2, cy - size / 2, size, size, score)


# ---------- модель на настоящих картинках ----------
def picture(name):
    img = cv2.imread(str(MODELS / "test" / name))
    assert img is not None
    return img


@needs_model
def test_finds_the_one_face_in_messi():
    faces = FaceFinder(MODEL).find(picture("messi5.jpg"))
    assert len(faces) == 1 and faces[0].score >= 0.8 and faces[0].w > 20


@needs_model
def test_no_faces_in_fruits():
    assert FaceFinder(MODEL).find(picture("fruits.jpg")) == []


@needs_model
def test_grey_frame_works_like_colour_and_finder_is_reusable_across_sizes():
    finder, img = FaceFinder(MODEL), picture("messi5.jpg")
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    assert len(finder.find(grey)) == 1
    assert finder.find(picture("fruits.jpg")) == []
    assert len(finder.find(img)) == 1


@needs_model
def test_mirrored_picture_flips_the_azimuth_sign():
    finder, img = FaceFinder(MODEL), picture("messi5.jpg")
    h, w = img.shape[:2]
    k = dock_tag.camera_matrix(w, h)
    a = direction(finder.find(img)[0], k)[0]
    b = direction(finder.find(cv2.flip(img, 1))[0], k)[0]
    assert abs(a) > 1 and a * b < 0 and abs(a + b) < 4


@needs_model
def test_faces_come_largest_first(tmp_path):
    img = picture("messi5.jpg")
    h, w = img.shape[:2]
    small = cv2.resize(img, (w // 3, h // 3))
    canvas = np.zeros((h, w * 2, 3), np.uint8)
    canvas[:, :w] = img
    canvas[:h // 3, w:w + w // 3] = small
    found = FaceFinder(MODEL).find(canvas)
    assert len(found) == 2 and found[0].w * found[0].h > found[1].w * found[1].h and found[0].x < w


# ---------- кадр ----------
def test_decode_grey_jpeg():
    ok, jpg = cv2.imencode(".jpg", np.full((72, 128), 90, np.uint8))
    img = decode(jpg.tobytes())
    assert img.shape == (72, 128) and abs(int(img.mean()) - 90) < 3


@pytest.mark.parametrize("junk", [b"", b"not a jpeg"])
def test_decode_junk_is_none(junk):
    assert decode(junk) is None


# ---------- геометрия ----------
def test_center_of_frame_is_straight_ahead():
    az, el = direction(face(), K)
    assert abs(az) < 0.5 and abs(el) < 0.5


def test_face_to_the_right_is_negative_azimuth_like_the_dock_tag():
    """Метка в правой половине кадра -> bearing_deg < 0 (поворот направо); лицо там же -> азимут с тем же знаком."""
    u, v = W * 0.75, H / 2
    rvec = np.zeros(3)
    tvec = np.array([(u - K[0, 2]) / K[0, 0] * 300, 0.0, 300.0])           # метка в 300 мм перед камерой, правее оси
    px, _ = cv2.projectPoints(dock_tag.OBJECT.astype(np.float64), rvec, tvec, K, None)
    tag = dock_tag.where(px.reshape(4, 2), K)["bearing_deg"]
    az, _ = direction(face(cx=u, cy=v), K)
    assert tag < 0 and az < 0 and abs(az - tag) < 6          # разница — смещение камеры от центра корпуса на 66 мм


def test_face_above_centre_has_positive_elevation_and_left_positive_azimuth():
    az, el = direction(face(cx=W * 0.25, cy=H * 0.25), K)
    assert az > 0 and el > 0


def test_azimuth_matches_pinhole_geometry():
    az, _ = direction(face(cx=W / 2 + K[0, 0]), K)                         # 45 градусов вправо
    assert az == pytest.approx(-45, abs=0.1)


def test_gaze_is_in_unit_square_with_eyes_convention():
    assert gaze(face(), W, H) == pytest.approx((0, 0))
    gx, gy = gaze(face(cx=W * 0.75, cy=H * 0.25), W, H)
    assert gx == pytest.approx(0.5) and gy == pytest.approx(0.5)           # вправо и вверх — плюс
    assert gaze(face(cx=W + 500, cy=-500), W, H) == (1.0, 1.0)


def test_head_camera_matches_dock_tag_for_any_frame_size():
    k, size = head_camera(W, H)
    assert size == (W, H) and np.allclose(k, K)
    assert head_camera(640, 360)[0][0, 2] == 320


# ---------- Watcher ----------
class Seen:
    """Гоняет Watcher: кадры с лицами по времени."""

    def __init__(self, **kw):
        self.w, self.out = Watcher(**kw), []

    def at(self, now, *faces):
        msgs = self.w.update(list(faces), now, K, (W, H))
        self.out.append((now, msgs))
        return msgs


def test_first_face_greets_once():
    s = Seen()
    s.at(0.0, face())
    assert s.w.appeared is True
    assert s.w.take_greeting() is True and s.w.take_greeting() is False and s.w.appeared is False
    s.at(0.2, face())
    assert s.w.take_greeting() is False


def test_face_after_five_minutes_does_not_greet_but_after_eleven_does():
    s = Seen()
    s.at(0.0, face())
    s.w.take_greeting()
    s.at(1.0)                                                              # лица нет
    s.at(5.0)                                                              # потеряно
    s.at(300.0, face())
    assert s.w.take_greeting() is False
    s.at(301.0)
    s.at(310.0)
    s.at(310 + 11 * 60, face())
    assert s.w.take_greeting() is True


def test_gap_counts_from_the_last_time_the_face_was_seen_not_from_the_greeting():
    s = Seen()
    s.at(0.0, face())
    s.w.take_greeting()
    for t in range(1, 1500, 2):                                             # человек сидит 25 минут, лицо видно
        s.at(float(t), face())
    s.at(1500.0)
    s.at(1504.0)
    s.at(1510.0, face())
    assert s.w.take_greeting() is False


def test_one_second_blink_neither_loses_the_face_nor_greets_again():
    s = Seen()
    s.at(0.0, face(cx=W * 0.7))
    s.w.take_greeting()
    s.at(1.0, face(cx=W * 0.7))
    s.at(1.2)
    s.at(1.6)
    s.at(2.0, face(cx=W * 0.7))
    assert s.w.take_greeting() is False and s.w.bearing is not None
    assert all(m.get("x") != 0 or m.get("y") != 0 for _, ms in s.out for m in ms if m["t"] == "look")


def test_face_gone_for_three_seconds_sends_one_centered_look_and_forgets_bearing():
    s = Seen()
    s.at(0.0, face(cx=W * 0.8))
    assert s.w.bearing is not None
    assert s.at(2.9) == [] and s.w.bearing is not None
    assert s.at(3.0) == [{"t": "look", "x": 0.0, "y": 0.0}]
    assert s.at(3.2) == [] and s.at(10.0) == [] and s.w.bearing is None


def test_follows_the_biggest_face():
    s = Seen()
    far, near = face(cx=W * 0.2, size=40), face(cx=W * 0.8, size=200)
    msgs = s.at(0.0, far, near)
    assert msgs[0]["x"] > 0.5 and s.w.bearing < 0
    msgs = Seen().at(0.0, near, far)
    assert msgs[0]["x"] > 0.5


def test_look_messages_at_most_five_per_second_and_smoothed():
    s = Seen(alpha=0.5)
    s.at(0.0, face(cx=W / 2))
    sent = []
    for i in range(1, 41):                                                  # 20 кадров в секунду в течение 2 с
        t = i * 0.05
        sent += [(t, m) for m in s.at(t, face(cx=W * 0.9))]
    looks = [(t, m) for t, m in sent if m["t"] == "look"]
    assert 8 <= len(looks) <= 10
    assert all(b[0] - a[0] >= 0.2 - 1e-9 for a, b in zip(looks, looks[1:]))
    assert looks[0][1]["x"] < 0.79 and looks[-1][1]["x"] > 0.7        # сглаживание: сперва ещё не дошёл, потом дошёл


def test_bearing_follows_the_face_side():
    s = Seen()
    s.at(0.0, face(cx=W * 0.8))
    assert s.w.bearing < -5
    s2 = Seen()
    s2.at(0.0, face(cx=W * 0.2))
    assert s2.w.bearing > 5


def test_returns_after_loss_start_from_the_new_place_without_sweeping():
    s = Seen(alpha=0.5)
    s.at(0.0, face(cx=W * 0.9))
    s.at(1.0)
    s.at(5.0)
    msg = s.at(6.0, face(cx=W * 0.1))
    assert msg and msg[0]["x"] < -0.7


# ---------- источники кадров ----------
def jpeg(value=90):
    return cv2.imencode(".jpg", np.full((72, 128), value, np.uint8))[1].tobytes()


class FakeMedia:
    def __init__(self, frame=None):
        self.frame = frame

    def latest_frame(self):
        return self.frame


def test_head_frame_is_used_while_fresh():
    frames = HeadFrames(FakeMedia((100.0, jpeg())), max_age_s=1.0, clock=lambda: 100.9)
    assert frames.read().shape == (72, 128)


def test_head_frame_older_than_a_second_is_ignored():
    """Голова отключилась, а последний кадр так и висит в MediaServer: «лицом сейчас» он не считается."""
    assert HeadFrames(FakeMedia((100.0, jpeg())), max_age_s=1.0, clock=lambda: 101.1).read() is None


def test_no_head_frame_and_junk_frame_give_none():
    assert HeadFrames(FakeMedia(None), clock=lambda: 0.0).read() is None
    assert HeadFrames(FakeMedia((0.0, b"junk")), clock=lambda: 0.0).read() is None


class FakeCapture:
    def __init__(self, frames):
        self.frames, self.released = list(frames), False

    def read(self):
        return (True, self.frames.pop(0)) if self.frames else (False, None)

    def release(self):
        self.released = True


def test_webcam_frames_read_and_release_through_the_injected_capture():
    cap = FakeCapture([np.zeros((4, 4, 3), np.uint8)])
    frames = WebcamFrames(0, capture=lambda index: cap)
    assert frames.read().shape == (4, 4, 3) and frames.read() is None
    frames.close()
    assert cap.released


class FakeFinder:
    def __init__(self, faces):
        self.faces, self.seen = faces, []

    def find(self, img):
        self.seen.append(img.shape)
        return self.faces


class FakeFrames:
    def __init__(self, img):
        self.img, self.closed = img, False

    def read(self):
        return self.img

    def close(self):
        self.closed = True


def test_sight_gives_faces_with_camera_matrix_and_size():
    f = [face()]
    faces, k, size = Sight(FakeFrames(np.zeros((720, 1280), np.uint8)), FakeFinder(f)).look()
    assert faces == f and size == (1280, 720) and np.allclose(k, K)


def test_sight_without_a_frame_sees_nobody_and_does_not_ask_the_finder():
    finder = FakeFinder([face()])
    assert Sight(FakeFrames(None), finder).look() == ([], None, None) and finder.seen == []


def test_sight_close_closes_the_frames():
    frames = FakeFrames(None)
    Sight(frames, FakeFinder([])).close()
    assert frames.closed
