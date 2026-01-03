"""迹线坐标平移与旋转。"""
from __future__ import annotations

import math
import numpy as np


def strike_to_rad(ang0: float) -> float:
    if ang0 > 270:
        return -(360 - ang0) * math.pi / 180.0
    if ang0 > 180:
        return (ang0 - 180) * math.pi / 180.0
    if ang0 > 90:
        return -(180 - ang0) * math.pi / 180.0
    return ang0 * math.pi / 180.0


def shift_lines_pos(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    min_x = abs(np.round(np.min(XY[:, [0, 2]]))) + padding
    min_y = abs(np.round(np.min(XY[:, [1, 3]]))) + padding
    return XY + np.array([min_x, min_y, min_x, min_y])


def rotate_shift_lines(lines: np.ndarray, ang0: float) -> np.ndarray:
    angle = strike_to_rad(ang0)
    rot_mat = np.array([
        [math.cos(angle), -math.sin(angle)],
        [math.sin(angle), math.cos(angle)],
    ])
    rot_lines = (lines.reshape(-1, 2) @ rot_mat.T).reshape(lines.shape)

    min_rot_x = abs(np.round(np.min(rot_lines[:, [0, 2]])))
    min_rot_y = abs(np.round(np.min(rot_lines[:, [1, 3]])))
    return rot_lines + np.array([min_rot_x, min_rot_y, min_rot_x, min_rot_y])


def norm_rotate_lines(XY: np.ndarray, ang0: float, padding: float = 1.0) -> np.ndarray:
    shifted = shift_lines_pos(XY, padding=padding)
    return rotate_shift_lines(shifted, ang0)
