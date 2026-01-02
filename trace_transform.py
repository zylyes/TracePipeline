# 功能：提供迹线坐标的平移、旋转与归一化计算工具。
import math
from typing import Tuple
import numpy as np


def rotate_vector(x: float, y: float, rad: float) -> Tuple[float, float]:
    """将向量按弧度角旋转，保持长度不变。"""
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return x * cos_a - y * sin_a, x * sin_a + y * cos_a


def strike_to_rotation_rad(ang0: float) -> float:
    """根据走向角得到旋转弧度，保持与 MATLAB 分段逻辑一致。"""
    if ang0 > 270:
        return -(360 - ang0) * math.pi / 180.0
    if ang0 > 180:
        return (ang0 - 180) * math.pi / 180.0
    if ang0 > 90:
        return -(180 - ang0) * math.pi / 180.0
    return ang0 * math.pi / 180.0


def shift_lines_to_positive(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    """将所有坐标平移到正半轴，贴近原 MATLAB 行为。"""
    min_x = abs(np.round(np.min([XY[:, 0].min(), XY[:, 2].min()]))) + padding
    min_y = abs(np.round(np.min([XY[:, 1].min(), XY[:, 3].min()]))) + padding
    return np.column_stack([
        XY[:, 0] + min_x,
        XY[:, 1] + min_y,
        XY[:, 2] + min_x,
        XY[:, 3] + min_y,
    ])


def rotate_lines_and_shift(lines: np.ndarray, ang0: float) -> np.ndarray:
    """按走向旋转线段端点后，再次平移到正半轴。"""
    rotate_angle = strike_to_rotation_rad(ang0)
    rot_lines = np.zeros_like(lines)
    for i in range(lines.shape[0]):
        rot_lines[i, 0:2] = rotate_vector(lines[i, 0], lines[i, 1], rotate_angle)
        rot_lines[i, 2:4] = rotate_vector(lines[i, 2], lines[i, 3], rotate_angle)

    min_rot_x = abs(np.round(np.min([rot_lines[:, 0].min(), rot_lines[:, 2].min()])))
    min_rot_y = abs(np.round(np.min([rot_lines[:, 1].min(), rot_lines[:, 3].min()])))
    return np.column_stack([
        rot_lines[:, 0] + min_rot_x,
        rot_lines[:, 1] + min_rot_y,
        rot_lines[:, 2] + min_rot_x,
        rot_lines[:, 3] + min_rot_y,
    ])


def normalize_and_rotate_lines(XY: np.ndarray, ang0: float, padding: float = 1.0) -> np.ndarray:
    """先归一化到正半轴，再旋转并回到正半轴，便于后续绘制。"""
    shifted = shift_lines_to_positive(XY, padding=padding)
    return rotate_lines_and_shift(shifted, ang0)
