"""迹线坐标平移与旋转 — 纯函数式变换流水线。

流水线顺序:
  1. shift_to_positive  → 平移到正象限（留白边距）
  2. rotate_shift_lines → 按走向角旋转后平移到非负区域

以及走向角 → 绘图弧度的辅助转换。
所有函数均接受 ndarray，返回新 ndarray，不修改入参。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "norm_rotate_lines",
    "rotate_shift_lines",
    "shift_to_positive",
    "strike_to_rad",
]

# ---------------------------------------------------------------------------
# 内部校验
# ---------------------------------------------------------------------------


def _validate_lines_array(lines: np.ndarray, arg_name: str = "XY") -> np.ndarray:
    """校验线段数组格式 (N,4) 并返回 float64 副本。

    Args:
        lines: 待校验的数组。
        arg_name: 用于错误信息的参数名。

    Returns:
        float64 副本。

    Raises:
        ValueError: 形状不是 (N,4) 或包含 NaN/inf。
    """
    arr = np.asarray(lines, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"{arg_name} 必须为 (N,4) 形状，当前 {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{arg_name} 包含 NaN 或 inf")
    return arr


# ---------------------------------------------------------------------------
# 走向角 → 绘图弧度
# ---------------------------------------------------------------------------


def strike_to_rad(strike_deg: float) -> float:
    """将 0°–360° 走向角折叠到 [-90°, 90°] 并转为弧度。

    映射规则（适用于绘图方向）:
      - (0, 90]     → 正值，与走向一致
      - (90, 180]   → ang - 180°（负值，表示反方向）
      - (180, 270]  → ang - 180°（正值）
      - (270, 360)  → ang - 360°（负值）

    Args:
        strike_deg: 走向角（度），可超出 [0,360]，会自动取模。

    Returns:
        折叠后的弧度值，范围 [-π/2, π/2]。
    """
    ang = float(strike_deg) % 360.0
    if ang > 270.0:
        return math.radians(ang - 360.0)
    if ang > 90.0:
        return math.radians(ang - 180.0)
    return math.radians(ang)


# ---------------------------------------------------------------------------
# 平移与旋转
# ---------------------------------------------------------------------------


def shift_to_positive(XY: np.ndarray, padding: float = 1.0) -> np.ndarray:
    """平移线段数组使所有坐标 ≥ padding。

    仅平移必要量；若已满足条件则不做平移。

    Args:
        XY: (N,4) 线段数组 [x1, y1, x2, y2]。
        padding: 正象限最小边距，默认 1.0。

    Returns:
        平移后的 (N,4) 数组。
    """
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


def rotate_shift_lines(lines: np.ndarray, strike_deg: float) -> np.ndarray:
    """按走向角旋转线段，然后平移到非负区域。

    旋转中心为原点 (0,0)，旋转后自动平移使所有坐标 ≥ 0。

    Args:
        lines: (N,4) 线段数组 [x1, y1, x2, y2]。
        strike_deg: 走向角（度），决定旋转量。

    Returns:
        旋转并平移后的 (N,4) 数组。
    """
    checked = _validate_lines_array(lines, arg_name="lines")
    if checked.size == 0:
        return checked.copy()

    angle = strike_to_rad(strike_deg)
    rot_mat = np.array([
        [math.cos(angle), -math.sin(angle)],
        [math.sin(angle), math.cos(angle)],
    ])

    # 将 (N,4) 重塑为 (N*2,2) 进行矩阵乘法，再恢复形状
    rot_lines = (checked.reshape(-1, 2) @ rot_mat.T).reshape(checked.shape)

    min_rot_x = float(np.min(rot_lines[:, [0, 2]]))
    min_rot_y = float(np.min(rot_lines[:, [1, 3]]))
    shift_x = max(0.0, -min_rot_x)
    shift_y = max(0.0, -min_rot_y)
    return rot_lines + np.array([shift_x, shift_y, shift_x, shift_y], dtype=float)


def norm_rotate_lines(XY: np.ndarray, strike_deg: float, padding: float = 1.0) -> np.ndarray:
    """规范化流水线：正象限平移 → 走向旋转 → 非负平移。

    两步平移说明:
      第一步确保旋转前所有点在正象限；
      第二步补偿旋转可能引入的负坐标。

    Args:
        XY: (N,4) 线段数组 [x1, y1, x2, y2]。
        strike_deg: 走向角（度）。
        padding: 初始平移边距，默认 1.0。

    Returns:
        规范化后的 (N,4) 数组。
    """
    shifted = shift_to_positive(XY, padding=padding)
    return rotate_shift_lines(shifted, strike_deg)
