"""Метка AprilTag на башенке станции → направление и расстояние до неё по кадру камеры головы. Работает без ПК.

Метка 36h11 №0, 30 × 30 мм, на башенке станции (модели/мини/harvey_mini_parts.py, dock_tower; заметки/Комплектация
мини.md). Камера — Camera Module 3 Wide в передней стенке, смотрит вперёд (x 66,2 мм и z 8,5 мм от осей бедра).
Оптика — документы/Camera Module 3 — краткое описание.pdf: f = 2,75 мм, пиксель 1,4 мкм, кадр 4608 × 2592.

Что метка даёт надёжно — направление (±0,3°) и расстояние (±2 %). Под каким углом Харви смотрит на метку, она НЕ
даёт: метка 30 мм в 30 см почти не искажается в перспективе, и поворот Харви на 2° неотличим от сдвига вбок на 13 мм
(проверено на синтетических кадрах). Сторону оси станции даёт ИК-маяк с двумя светодиодами и перегородкой.

ПРЕДВАРИТЕЛЬНО: объектив Wide даёт сильную дисторсию по краям — на стенде откалибровать камеру по шахматной доске
(cv2.calibrateCamera) и передать матрицу и коэффициенты в locate. Кадр 1280 × 720 и уточнение углов до долей
пикселя; скорость на Pi Zero 2 W проверить (если медленно — искать в 640 × 360, углы уточнять в полном кадре).
"""
from __future__ import annotations

import math

import cv2
import numpy as np

DICT, TAG_ID, TAG_MM = cv2.aruco.DICT_APRILTAG_36h11, 0, 30.0
CAM_IN_BODY = (66.2, 0.0, 8.5)
FOCAL_MM, PIXEL_MM, SENSOR_PX = 2.75, 0.0014, (4608, 2592)
FRAME = (1280, 720)
MAX_DIST_MM = 600                                     # дальше метка мелкая (≤ 14 px) — позе не верим

# камера (OpenCV: x вправо, y вниз, z вперёд) в системе корпуса (x вперёд, y влево, z вверх): столбцы — оси камеры
R_BC = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float)
_H = TAG_MM / 2
OBJECT = np.array([(-_H, _H, 0), (_H, _H, 0), (_H, -_H, 0), (-_H, -_H, 0)], np.float32)   # углы ArUco: ЛВ, ПВ, ПН, ЛН


def camera_matrix(width: int, height: int) -> np.ndarray:
    f = FOCAL_MM / PIXEL_MM * width / SENSOR_PX[0]
    return np.array([[f, 0, width / 2], [0, f, height / 2], [0, 0, 1]], float)


_params = cv2.aruco.DetectorParameters()
_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
_detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICT), _params)


def detect(gray: np.ndarray) -> np.ndarray | None:
    """Углы метки №0 в кадре (4 × 2, px) или None."""
    corners, ids, _ = _detector.detectMarkers(gray)
    if ids is None:
        return None
    for c, i in zip(corners, ids.ravel()):
        if i == TAG_ID:
            return c.reshape(4, 2)
    return None


def where(corners: np.ndarray, K: np.ndarray, dist=None) -> dict | None:
    """{"bearing_deg": + — слева, "dist_mm": по столу от центра корпуса} до метки или None, если она дальше MAX_DIST_MM."""
    ok, _, tvec = cv2.solvePnP(OBJECT, corners.astype(np.float32), K, dist, flags=cv2.SOLVEPNP_IPPE_SQUARE)
    if not ok or float(np.linalg.norm(tvec)) > MAX_DIST_MM:
        return None
    p = np.array(CAM_IN_BODY) + R_BC @ tvec.ravel()            # центр метки в системе корпуса
    return {"bearing_deg": round(math.degrees(math.atan2(p[1], p[0])), 2), "dist_mm": round(math.hypot(p[0], p[1]), 1)}


def locate(gray: np.ndarray, K: np.ndarray, dist=None) -> dict | None:
    corners = detect(gray)
    return None if corners is None else where(corners, K, dist)
