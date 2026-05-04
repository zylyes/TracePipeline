"""迹线坐标平移与旋转 — 纯函数式变换流水线。

流水线顺序：
  1. shift_to_positive  → 平移到正象限（留白边距）
  2. rotate_and_shift   → 按走向角旋转后平移到非负区域

以及线段数组到绘图序列的转换与走向角辅助转换。
所有函数均接受 ndarray，返回新 ndarray，不修改入参。
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from .angles import fold_strike_angle

__all__ = [
    "normalize_coordinates",
    "rotate_and_shift",
    "segments_to_xy",
    "shift_to_positive",
]


# ===========================================================================
# 内部校验
# ===========================================================================


def _validate_lines(lines: np.ndarray, arg_name: str = "lines") -> np.ndarray:
    """校验线段数组格式 (N, 4) 并返回 float64 副本。"""
    arr = np.asarray(lines, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"{arg_name} 必须为 (N,4) 形状，当前 {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{arg_name} 包含 NaN 或 inf")
    return arr


# ===========================================================================
# 平移
# ===========================================================================


def shift_to_positive(lines: np.ndarray, margin: float = 1.0) -> np.ndarray:
    """平移线段数组使所有坐标 ≥ margin。

    仅平移必要量；若已满足条件则不做平移。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        margin: 正象限最小边距，默认 1.0。

    Returns:
        平移后的 (N, 4) 数组。
    """
    if margin < 0:
        raise ValueError("margin 必须 ≥ 0")

    arr = _validate_lines(lines)
    if arr.size == 0:
        return arr.copy()

    min_x = float(np.min(arr[:, [0, 2]]))
    min_y = float(np.min(arr[:, [1, 3]]))
    dx = max(0.0, margin - min_x)
    dy = max(0.0, margin - min_y)
    return arr + np.array([dx, dy, dx, dy], dtype=float)


# ===========================================================================
# 旋转 + 平移
# ===========================================================================


def rotate_and_shift(lines: np.ndarray, azimuth_deg: float) -> np.ndarray:
    """按走向角旋转线段，然后平移到非负区域。

    旋转中心为原点 (0, 0)，旋转后自动平移使所有坐标 ≥ 0。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        azimuth_deg: 走向角（度），决定旋转量。

    Returns:
        旋转并平移后的 (N, 4) 数组。
    """
    arr = _validate_lines(lines)
    if arr.size == 0:
        return arr.copy()

    angle = fold_strike_angle(azimuth_deg)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    rot_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])

    # (N, 4) → (N×2, 2) 矩阵乘法 → (N, 4)
    rotated = (arr.reshape(-1, 2) @ rot_mat.T).reshape(arr.shape)

    min_x = float(np.min(rotated[:, [0, 2]]))
    min_y = float(np.min(rotated[:, [1, 3]]))
    dx = max(0.0, -min_x)
    dy = max(0.0, -min_y)
    return rotated + np.array([dx, dy, dx, dy], dtype=float)


# ===========================================================================
# 规范化流水线
# ===========================================================================


def normalize_coordinates(lines: np.ndarray, azimuth_deg: float, margin: float = 1.0) -> np.ndarray:
    """规范化流水线：正象限平移 → 走向旋转 → 非负平移。

    两步平移说明：
      第一步确保旋转前所有点在正象限；
      第二步补偿旋转可能引入的负坐标。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        azimuth_deg: 走向角（度）。
        margin: 初始平移边距，默认 1.0。

    Returns:
        规范化后的 (N, 4) 数组。
    """
    shifted = shift_to_positive(lines, margin=margin)
    return rotate_and_shift(shifted, azimuth_deg)


# ===========================================================================
# 线段 → 绘图序列
# ===========================================================================


def segments_to_xy(segments: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """将 (N, 4) 线段数组转为带 NaN 分隔的一维 X/Y 序列。

    NaN 作为线段间分隔符，使 matplotlib 的 line plot 自动断开各线段。
    """
    if segments.ndim != 2 or segments.shape[1] != 4:
        raise ValueError(f"segments 必须为 (N,4) 形状，当前 {segments.shape}")
    n = segments.shape[0]
    if n == 0:
        return np.array([]), np.array([])

    X = np.column_stack([segments[:, 0], segments[:, 2], np.full((n,), np.nan)]).ravel()
    Y = np.column_stack([segments[:, 1], segments[:, 3], np.full((n,), np.nan)]).ravel()
    return X, Y
