"""Метка AprilTag станции в кадре камеры головы → направление и расстояние до неё. Кадры рисуются по известной позе."""
import math

import cv2
import numpy as np
import pytest

from harvey_head import dock_tag as dt

W, H = dt.FRAME
BODY_Z = 43.0                                     # мм: оси бедра над столом в стойке (симуляция мини)


def render(x, y, yaw_deg, light=1.0, size=W):
    """Кадр камеры: серый фон, метка 36h11 №0 с белым полем, вид с корпуса в (x, y, yaw) системы станции."""
    K = dt.camera_matrix(size, size * H // W)
    R_SB = rot_z(math.radians(yaw_deg))
    R_SC = R_SB @ dt.R_BC
    p_C = np.array([x, y, BODY_Z]) + R_SB @ np.array(dt.CAM_IN_BODY)
    n, pad = 240, 60                                 # метка 240 px и белое поле 60 px по кругу
    marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(dt.DICT), dt.TAG_ID, n)
    canvas = np.full((n + 2 * pad, n + 2 * pad), 255, np.uint8)
    canvas[pad:pad + n, pad:pad + n] = marker
    half = dt.TAG_MM / 2 * (n + 2 * pad) / n
    img_pts = []
    for u, v in [(-half, half), (half, half), (half, -half), (-half, -half)]:      # как углы ArUco: ЛВ, ПВ, ПН, ЛН
        c = R_SC.T @ (np.array(TAG_IN_STATION) + R_ST @ np.array([u, v, 0.0]) - p_C)
        img_pts.append((K[0, 0] * c[0] / c[2] + K[0, 2], K[1, 1] * c[1] / c[2] + K[1, 2]))
    src = np.float32([(0, 0), (canvas.shape[1], 0), (canvas.shape[1], canvas.shape[0]), (0, canvas.shape[0])])
    M = cv2.getPerspectiveTransform(src, np.float32(img_pts))
    frame = cv2.warpPerspective(canvas, M, (size, size * H // W), borderValue=128, flags=cv2.INTER_AREA)
    return (frame.astype(np.float32) * light).astype(np.uint8), K


TAG_IN_STATION = (140.0, 0.0, 30.0)                # мм: модели/мини/harvey_mini_parts.py, окно метки в dock_tower
R_ST = np.array([[0, 0, -1], [-1, 0, 0], [0, 1, 0]], float)   # метка смотрит по −x станции


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def truth(x, y, yaw):
    """Направление (°, + — слева) и расстояние по столу (мм) от центра корпуса до метки."""
    dx, dy = TAG_IN_STATION[0] - x, TAG_IN_STATION[1] - y
    return math.degrees(math.atan2(dy, dx)) - yaw, math.hypot(dx, dy)


@pytest.mark.parametrize("x, y, yaw", [(-250, 0, 0), (-250, 4, 2), (-320, 70, 25), (-200, -40, -15), (-150, 20, 30),
                                       (-60, 3, -2), (-20, -1, 0)])
def test_direction_and_distance_to_the_tag(x, y, yaw):
    frame, K = render(x, y, yaw)
    seen = dt.locate(frame, K)
    bearing, dist = truth(x, y, yaw)
    assert seen["bearing_deg"] == pytest.approx(bearing, abs=0.3)
    assert seen["dist_mm"] == pytest.approx(dist, rel=0.02)


def test_no_tag_in_an_empty_frame():
    assert dt.locate(np.full((H, W), 128, np.uint8), dt.camera_matrix(W, H)) is None


def test_tag_seen_from_too_far_is_not_trusted():
    frame, K = render(-700, 0, 0)
    assert dt.locate(frame, K) is None


def test_dim_light_still_reads_the_tag():
    frame, K = render(-250, 10, 5, light=0.25)
    bearing, _ = truth(-250, 10, 5)
    assert dt.locate(frame, K)["bearing_deg"] == pytest.approx(bearing, abs=0.3)


def test_camera_matrix_matches_the_lens():
    K = dt.camera_matrix(4608, 2592)
    assert K[0, 0] == pytest.approx(2.75 / 0.0014, rel=1e-6) and K[0, 2] == 2304 and K[1, 2] == 1296
    assert dt.camera_matrix(640, 360)[0, 0] == pytest.approx(2.75 / 0.0014 * 640 / 4608, rel=1e-6)
