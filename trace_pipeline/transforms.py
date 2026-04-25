"""迹线坐标平移与旋转工具。

提供线段数组的规范化流水线：
1. 平移到正象限（留白边距）
2. 按走向角旋转
3. 再次平移到非负区域

以及走向角→绘图弧度的转换。
"""
from __future__ import annotations

import math

import numpy as np


def _validate_lines_array(lines: np.ndarray, arg_name: str = "XY") -> np.ndarray:
    """校验线段数组格式 (N,4) 并返回 float 副本。"""
    arr = np.asarray(lines, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"{arg_name} 必须为 (N,4) 形状，当前 {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{arg_name} 包含 NaN 或 inf")
    return arr


# ---------------------------------------------------------------------------
# 走向角 → 绘图弧度
# ---------------------------------------------------------------------------


def strike_to_rad(ang0: float) -> float:
    """将 0°–360° 走向角折叠到 [-90°, 90°] 并转为弧度。

    映射规则:
    - (0, 90]   → 正值
    - (90, 270] → ang - 180°（负值或正值）
    - (270, 360) → ang - 360°（负值）
    """
    ang = float(ang0) % 360.0
    if ang > 270.0:
        return math.radians(ang - 360.0)
    if ang > 90.0:
        return math.radians(ang - 180.0)
    return math.radians(ang)


# ---------------------------------------------------------------------------
# 平移与旋转
# ---------------------------------------------------------------------------


def shift_lines_pos(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    """向正方向平移，使所有坐标 ≥ padding。"""
    if padding < 0:
        raise ValueError("padding 必须 ≥ 0")

    lines = _validate_lines_array(XY, arg_name="XY")
    if lines.size == 0:
        return lines.copy()

    min_x = float(np.min(lines[:, [0, 2]]))
    min_y = float(np.min(lines[:, [1, 3]]))
    shift_x = max(0.0, padding - min_x)
    shift_y = max(0.0, padding - min_y)
    return lines + np.array([shift_x, shift_y, shift_x, shift_y], dtype=float)


def rotate_shift_lines(lines: np.ndarray, ang0: float) -> np.ndarray:
    """按走向角旋转线段，然后平移到非负区域。"""
    checked = _validate_lines_array(lines, arg_name="lines")
    if checked.size == 0:
        return checked.copy()

    angle = strike_to_rad(ang0)
    rot_mat = np.array([
        [math.cos(angle), -math.sin(angle)],
        [math.sin(angle), math.cos(angle)],
    ])
    rot_lines = (checked.reshape(-1, 2) @ rot_mat.T).reshape(checked.shape)

    min_rot_x = float(np.min(rot_lines[:, [0, 2]]))
    min_rot_y = float(np.min(rot_lines[:, [1, 3]]))
    shift_x = max(0.0, -min_rot_x)
    shift_y = max(0.0, -min_rot_y)
    return rot_lines + np.array([shift_x, shift_y, shift_x, shift_y], dtype=float)


def norm_rotate_lines(XY: np.ndarray, ang0: float, padding: float = 1.0) -> np.ndarray:
    """规范化流水线：正象限平移 → 走向旋转 → 再次非负平移。

    两步平移是必要的：旋转可能将原本在正象限的点带到负坐标，
    因此旋转后需要再次校正。
    """
    shifted = shift_lines_pos(XY, padding=padding)
    return rotate_shift_lines(shifted, ang0)
