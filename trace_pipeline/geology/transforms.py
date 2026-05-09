"""迹线坐标平移与旋转 — 纯函数式变换流水线。

流水线顺序：
  1. shift_to_positive  → 平移到正象限（留白边距）
  2. rotate_and_shift   → 按走向角旋转后平移到非负区域

所有函数均接受 ndarray，返回新 ndarray，不修改入参。
"""
from __future__ import annotations

import math

import numpy as np

from .angles import azimuth_to_cartesian_deg, fold_strike_angle

__all__ = [
    "normalize_coordinates",
    "normalize_points_like_lines",
    "rotate_and_shift",
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


def _validate_points(points: np.ndarray, arg_name: str = "points") -> np.ndarray:
    """校验点数组格式 (N, 2) 并返回 float64 副本。"""
    arr = np.asarray(points, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"{arg_name} 必须为 (N,2) 形状，当前 {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{arg_name} 包含 NaN 或 inf")
    return arr


def _line_shift_vector(arr: np.ndarray, margin: float = 0.0) -> np.ndarray:
    """计算线段数组平移到非负坐标所需的二维偏移量。"""
    if arr.size == 0:
        return np.array([0.0, 0.0], dtype=float)
    min_x = float(np.min(arr[:, [0, 2]]))
    min_y = float(np.min(arr[:, [1, 3]]))
    dx = max(0.0, margin - min_x)
    dy = max(0.0, margin - min_y)
    return np.array([dx, dy], dtype=float)


def _shift_lines(arr: np.ndarray, shift: np.ndarray) -> np.ndarray:
    if float(shift[0]) == 0.0 and float(shift[1]) == 0.0:
        return arr.copy()
    return arr + np.array([shift[0], shift[1], shift[0], shift[1]], dtype=float)


def _shift_to_nonnegative(arr: np.ndarray, margin: float = 0.0) -> np.ndarray:
    """内部辅助：平移使所有坐标 ≥ margin。不做校验。"""
    return _shift_lines(arr, _line_shift_vector(arr, margin=margin))


def _rotation_matrix(azimuth_deg: float) -> np.ndarray:
    angle = fold_strike_angle(azimuth_deg)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return np.array([[cos_a, -sin_a], [sin_a, cos_a]])


def _rotate_lines(arr: np.ndarray, rot_mat: np.ndarray) -> np.ndarray:
    if arr.size == 0:
        return arr.copy()
    return (arr.reshape(-1, 2) @ rot_mat.T).reshape(arr.shape)


def local_points_to_global(points: np.ndarray, azimuth_deg: float) -> np.ndarray:
    """将测线局部坐标点反投影到原始全局坐标系。"""
    local = _validate_points(points)
    if local.size == 0:
        return local.copy()

    angle = math.radians(azimuth_to_cartesian_deg(azimuth_deg))
    along = np.array([math.cos(angle), math.sin(angle)], dtype=float)
    left = np.array([-math.sin(angle), math.cos(angle)], dtype=float)
    return local[:, [0]] * along + local[:, [1]] * left


# ===========================================================================
# 平移
# ===========================================================================


def shift_to_positive(lines: np.ndarray, margin: float = 1.0) -> np.ndarray:
    """平移线段数组使所有坐标 ≥ margin。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        margin: 正象限最小边距，默认 1.0。

    Returns:
        平移后的 (N, 4) 数组。
    """
    if margin < 0:
        raise ValueError("margin 必须 ≥ 0")
    arr = _validate_lines(lines)
    return _shift_to_nonnegative(arr, margin=margin)


# ===========================================================================
# 旋转 + 平移
# ===========================================================================


def rotate_and_shift(lines: np.ndarray, azimuth_deg: float) -> np.ndarray:
    """按走向角旋转线段，然后平移到非负区域。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        azimuth_deg: 走向角（度），决定旋转量。

    Returns:
        旋转并平移后的 (N, 4) 数组。
    """
    arr = _validate_lines(lines)
    if arr.size == 0:
        return arr.copy()

    # (N, 4) → (N×2, 2) 矩阵乘法 → (N, 4)
    rotated = _rotate_lines(arr, _rotation_matrix(azimuth_deg))
    return _shift_to_nonnegative(rotated, margin=0.0)


# ===========================================================================
# 规范化流水线
# ===========================================================================


def normalize_coordinates(lines: np.ndarray, azimuth_deg: float, margin: float = 1.0) -> np.ndarray:
    """规范化流水线：正象限平移 → 走向旋转 → 非负平移。

    Args:
        lines: (N, 4) 线段数组 [x1, y1, x2, y2]。
        azimuth_deg: 走向角（度）。
        margin: 初始平移边距，默认 1.0。

    Returns:
        规范化后的 (N, 4) 数组。
    """
    if margin < 0:
        raise ValueError("margin 必须 ≥ 0")
    arr = _validate_lines(lines)
    shifted = _shift_to_nonnegative(arr, margin=margin)

    if shifted.size == 0:
        return shifted.copy() if shifted is arr else shifted

    rotated = _rotate_lines(shifted, _rotation_matrix(azimuth_deg))
    return _shift_to_nonnegative(rotated, margin=0.0)


def normalize_points_like_lines(
    points: np.ndarray,
    reference_lines: np.ndarray,
    azimuth_deg: float,
    margin: float = 1.0,
) -> np.ndarray:
    """用与 ``normalize_coordinates`` 相同的平移/旋转流程转换点坐标。"""
    if margin < 0:
        raise ValueError("margin 必须 ≥ 0")
    point_arr = _validate_points(points)
    line_arr = _validate_lines(reference_lines, arg_name="reference_lines")

    first_shift = _line_shift_vector(line_arr, margin=margin)
    shifted_lines = _shift_lines(line_arr, first_shift)
    shifted_points = point_arr + first_shift

    rot_mat = _rotation_matrix(azimuth_deg)
    rotated_lines = _rotate_lines(shifted_lines, rot_mat)
    rotated_points = shifted_points @ rot_mat.T

    second_shift = _line_shift_vector(rotated_lines, margin=0.0)
    return rotated_points + second_shift
