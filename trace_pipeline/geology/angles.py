"""地质角度转换 — 纯函数工具集。

提供：
  - dip_to_strike              倾向 → 走向（向量化）
  - fold_strike_angle          走向角折叠到 [-90°, 90°] 并转弧度
  - fold_to_halfplane          将角度折叠到参考基准角所确定的半平面内
  - fold_strikes_to_semicircle 走向角折叠到 [0°, 180°)（向量化，用于玫瑰图）
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "dip_to_strike",
    "fold_strike_angle",
    "fold_strikes_to_semicircle",
    "fold_to_halfplane",
]


# ===========================================================================
# 倾向 ⇄ 走向
# ===========================================================================


def dip_to_strike(dip_deg: np.ndarray) -> np.ndarray:
    """倾向 → 走向（向量化）。

    规则（与 MATLAB 原版一致）:
      - dd ≥ 270°        → strike = dd − 270°
      - 90° ≤ dd < 270°  → strike = dd − 90°
      - dd < 90°         → strike = dd + 90°

    Args:
        dip_deg: 倾向角度数组（度），任意形状。

    Returns:
        走向角度（度），与输入同形状，值域 [0, 360)。
    """
    dd = np.asarray(dip_deg, dtype=float)
    res = np.empty_like(dd, dtype=float)

    mask_ge270 = dd >= 270.0
    mask_mid = (dd >= 90.0) & (dd < 270.0)
    mask_lt90 = dd < 90.0

    res[mask_ge270] = dd[mask_ge270] - 270.0
    res[mask_mid] = dd[mask_mid] - 90.0
    res[mask_lt90] = dd[mask_lt90] + 90.0
    return res


# ===========================================================================
# 走向角折叠
# ===========================================================================


def fold_strike_angle(strike_deg: float) -> float:
    """将 0°–360° 走向角折叠到 [−90°, 90°] 并转为弧度。

    映射规则（用于确定绘图/旋转方向）:
      - (0, 90]     → 正值（与走向一致）
      - (90, 180]   → ang − 180°（负值，反向）
      - (180, 270]  → ang − 180°（正值）
      - (270, 360)  → ang − 360°（负值）

    注意（与 MATLAB 参考代码的差异）:
      `docs/matlab_reference/A_outcrop_0map_rotate.m` 第 68-76 行存在 bug——
      `if ang0 <= 360` 永远为真，导致后续 `elseif` 分支均不可达，实际效果始终为
      `rotate_angle = (ang0 - 360)·π/180`。Python 版采用上述正确的
      [-90°, 90°] 折叠语义，使测线方向在旋转后最接近水平轴。

    Args:
        strike_deg: 走向角（度），可超出 [0, 360]，会自动取模。

    Returns:
        折叠后的弧度值，范围 [−π/2, π/2]。
    """
    ang = float(strike_deg) % 360.0
    if ang > 270.0:
        return math.radians(ang - 360.0)
    if ang > 90.0:
        return math.radians(ang - 180.0)
    return math.radians(ang)


# ===========================================================================
# 半平面折叠
# ===========================================================================


def fold_to_halfplane(
    base_angle_deg: float,
    target_angles_deg: np.ndarray,
    *,
    invert: bool = False,
) -> np.ndarray:
    """将目标角折叠到以基准角为界的半平面内，返回弧度。

    算法：
      1. 基准角 base 定义一条参考方向线。
      2. 对于每个 target，判断其是否落在 (base, base+180°) 半平面内
         （或 (base−180°, base) 当 base > 180°）。
      3. 若在半平面内 → 返回 target；否则 → 返回 target+180°（模 360°）。
      4. invert=True 反转上述判定逻辑。

    用途：确保左/右侧迹线的方向向量严格位于测线的左/右半平面。

    Args:
        base_angle_deg: 基准角度（度），0–360。
        target_angles_deg: 待折叠的目标角度数组（度）。
        invert: 是否反转半平面判定。

    Returns:
        折叠后的弧度数组，形状与 target_angles_deg 一致。
    """
    targets = np.mod(np.asarray(target_angles_deg, dtype=float), 360.0)
    base = float(base_angle_deg) % 360.0

    if base <= 180.0:
        in_half = (base < targets) & (targets < base + 180.0)
    else:
        in_half = (base - 180.0 < targets) & (targets < base)

    adjusted = np.where(in_half ^ invert, targets, targets + 180.0)
    return np.radians(np.mod(adjusted, 360.0))


# ===========================================================================
# 走向角半圆折叠（用于玫瑰图）
# ===========================================================================


def fold_strikes_to_semicircle(strike_deg: np.ndarray) -> np.ndarray:
    """将走向角折叠到 [0°, 180°)（向量化，用于玫瑰图分箱）。

    对称走向（如 NE 与 SW）合并为同一区间。

    Args:
        strike_deg: 走向角度数组（度），任意形状。

    Returns:
        折叠后的角度数组，值域 [0, 180)。
    """
    folded = np.mod(np.asarray(strike_deg, dtype=float), 180.0)
    folded[np.isclose(folded, 180.0)] = 0.0
    return folded
