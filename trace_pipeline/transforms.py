"""迹线坐标平移与旋转。"""
from __future__ import annotations

import math
import numpy as np


def strike_to_rad(ang0: float) -> float:
    """
    将走向角转换为弧度，按象限修正方向。
    
    逻辑说明：
    将 0-360 度的走向角映射到 [-90, 90] 区间（弧度制），
    以便在绘图时将走向旋转至水平或垂直方向。
    - 0-90: 保持正值
    - 90-180: 减去 180（负值）
    - 180-270: 减去 180（正值）
    - 270-360: 减去 360（负值）
    
    Args:
        ang0: 走向角（角度制）
        
    Returns:
        修正后的弧度值
    """
    if ang0 > 270:
        return -(360 - ang0) * math.pi / 180.0
    if ang0 > 180:
        return (ang0 - 180) * math.pi / 180.0
    if ang0 > 90:
        return -(180 - ang0) * math.pi / 180.0
    return ang0 * math.pi / 180.0


def shift_lines_pos(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    """
    统一平移到正坐标系并预留少量空白。
    
    Args:
        XY: 迹线坐标数组 (N, 4)
        padding: 边距
        
    Returns:
        平移后的坐标数组
    """
    min_x = abs(np.round(np.min(XY[:, [0, 2]]))) + padding
    min_y = abs(np.round(np.min(XY[:, [1, 3]]))) + padding
    return XY + np.array([min_x, min_y, min_x, min_y])


def rotate_shift_lines(lines: np.ndarray, ang0: float) -> np.ndarray:
    """
    先旋转，再平移使坐标非负，便于后续绘图。
    
    Args:
        lines: 迹线坐标数组 (N, 4)
        ang0: 旋转角度（走向角）
        
    Returns:
        旋转并平移后的坐标数组
    """
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
    """
    标准化流程：平移到正象限后按走向旋转。
    
    Args:
        XY: 原始迹线坐标数组
        ang0: 走向角
        padding: 边距
        
    Returns:
        处理后的坐标数组
    """
    shifted = shift_lines_pos(XY, padding=padding)
    return rotate_shift_lines(shifted, ang0)
