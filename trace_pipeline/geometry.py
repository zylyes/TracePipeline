"""几何计算：迹线端点与走向转换。

该模块实现向量化的迹线端点坐标计算，核心流程：
1. 解析 Excel 表头（测线走向、迹线数量）
2. 提取并校验数值矩阵，将倾向转为走向
3. 按左/右/双侧三种情况，使用复数向量计算端点坐标

所有角度计算均使用向量化操作，避免 Python 层循环。
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 角度工具
# ---------------------------------------------------------------------------


def dip_to_strike_vec(dd: np.ndarray) -> np.ndarray:
    """倾向 → 走向（向量化）。

    规则（与 MATLAB 原版一致）:
    - dd ≥ 270  → strike = dd - 270
    - 90 ≤ dd < 270 → strike = dd - 90
    - dd < 90  → strike = dd + 90
    """
    res = np.empty_like(dd, dtype=float)
    mask1 = dd >= 270.0
    mask2 = (dd >= 90.0) & (dd < 270.0)
    mask3 = dd < 90.0
    res[mask1] = dd[mask1] - 270.0
    res[mask2] = dd[mask2] - 90.0
    res[mask3] = dd[mask3] + 90.0
    return res


def _get_adjusted_angle_vec(
    base_angle: float,
    target_angles: np.ndarray,
    invert: bool = False,
) -> np.ndarray:
    """根据基准角调整目标角（向量化），返回弧度制数组。

    核心思想：将目标角折叠到以 base_angle 为参考的某半平面内，
    使得计算出的方向指向期望的节理侧（左/右）。
    """
    targets = np.mod(np.asarray(target_angles, dtype=float), 360.0)

    if base_angle <= 180.0:
        cond = (base_angle < targets) & (targets < base_angle + 180.0)
        res = np.where(cond, targets, targets + 180.0) if not invert else np.where(cond, targets + 180.0, targets)
    else:
        cond = (base_angle - 180.0 < targets) & (targets < base_angle)
        res = np.where(cond, targets + 180.0, targets) if not invert else np.where(cond, targets, targets + 180.0)

    return np.radians(np.mod(res, 360.0))


# ---------------------------------------------------------------------------
# 表头与数据提取
# ---------------------------------------------------------------------------


def _parse_header(df: pd.DataFrame) -> Tuple[float, int]:
    """从 DataFrame 首行解析测线走向 ang0 与迹线条数 n。

    约定：第 8 列为 ang0（度），第 9 列为 n。
    """
    if df.empty:
        raise ValueError("输入表格为空")
    if df.shape[1] < 9:
        raise ValueError(f"输入表格至少需要 9 列，当前仅有 {df.shape[1]} 列")

    try:
        ang0 = float(df.iloc[0, 7])
        n = int(pd.to_numeric(df.iloc[0, 8]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"无法解析表头（第1行第8-9列）：{exc}") from exc

    if not np.isfinite(ang0):
        raise ValueError("表头中的走向角度无效（inf 或 NaN）")
    if n <= 0:
        raise ValueError(f"迹线条数必须为正数，当前为 {n}")
    if len(df.index) < n:
        raise ValueError(f"迹线条数 {n} 超出数据行数 {len(df.index)}")

    return ang0, n


def _extract_numeric_block(df: pd.DataFrame, n: int) -> np.ndarray:
    """提取前 n 行、前 7 列数值矩阵，并将第 3 列倾向转为走向。"""
    numeric_block = df.iloc[:n, 0:7].apply(pd.to_numeric, errors="coerce")
    M = numeric_block.to_numpy(dtype=float)

    if np.isnan(M).any():
        bad_rows, bad_cols = np.where(np.isnan(M))
        raise ValueError(
            f"数据块第 {int(bad_rows[0]) + 1} 行第 {int(bad_cols[0]) + 1} 列包含非数值内容"
        )

    # 第 3 列：倾向 → 走向
    M[:, 2] = dip_to_strike_vec(M[:, 2])
    return M


# ---------------------------------------------------------------------------
# 端点计算（三种情况）
# ---------------------------------------------------------------------------

# 列索引常量（0-based）
_COL_R1 = 0  # 沿测线位移
_COL_R2 = 1  # 垂直测线位移
_COL_A = 2  # 节理走向（由倾向转换而来）
_COL_R3 = 3  # 左侧迹长 1
_COL_R4 = 4  # 左侧迹长 2
_COL_R5 = 5  # 右侧迹长 1
_COL_R6 = 6  # 右侧迹长 2


def _compute_case_left(
    X1: np.ndarray,
    Y1: np.ndarray,
    X2: np.ndarray,
    Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray,
    r2: np.ndarray,
    r3: np.ndarray,
    r4: np.ndarray,
    vec_perp_left: complex,
    vec_skew_a: np.ndarray,
) -> None:
    """Case 1: 仅左侧有迹线数据 (r4 ≠ 0, r6 = 0)。

    s1 = z1 + r2·L_perp + r3·L_skew
    s2 = s1 + r4·L_skew
    """
    s1 = z1[mask] + r2[mask] * vec_perp_left + r3[mask] * vec_skew_a[mask]
    s2 = s1 + r4[mask] * vec_skew_a[mask]
    X1[mask] = s1.real
    Y1[mask] = s1.imag
    X2[mask] = s2.real
    Y2[mask] = s2.imag


def _compute_case_right(
    X1: np.ndarray,
    Y1: np.ndarray,
    X2: np.ndarray,
    Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray,
    r2: np.ndarray,
    r5: np.ndarray,
    r6: np.ndarray,
    vec_perp_right: complex,
    vec_skew_e: np.ndarray,
) -> None:
    """Case 2: 仅右侧有迹线数据 (r4 = 0, r6 ≠ 0)。

    s1 = z1 + r2·R_perp + r5·R_skew
    s2 = s1 + r6·R_skew
    """
    s1 = z1[mask] + r2[mask] * vec_perp_right + r5[mask] * vec_skew_e[mask]
    s2 = s1 + r6[mask] * vec_skew_e[mask]
    X1[mask] = s1.real
    Y1[mask] = s1.imag
    X2[mask] = s2.real
    Y2[mask] = s2.imag


def _compute_case_both(
    X1: np.ndarray,
    Y1: np.ndarray,
    X2: np.ndarray,
    Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray,
    r2: np.ndarray,
    r3: np.ndarray,
    r4: np.ndarray,
    r5: np.ndarray,
    r6: np.ndarray,
    vec_perp_left: complex,
    vec_perp_right: complex,
    vec_skew_a: np.ndarray,
    vec_skew_e: np.ndarray,
) -> None:
    """Case 3: 双侧均有迹线数据 (r4 ≠ 0, r6 ≠ 0)。

    s_left  = z1 + r2·L_perp + (r3+r4)·L_skew
    s_right = z1 + r2·R_perp + (r5+r6)·R_skew
    """
    _z1 = z1[mask]
    _r2 = r2[mask]
    s_left = _z1 + _r2 * vec_perp_left + (r3[mask] + r4[mask]) * vec_skew_a[mask]
    s_right = _z1 + _r2 * vec_perp_right + (r5[mask] + r6[mask]) * vec_skew_e[mask]
    X1[mask] = s_left.real
    Y1[mask] = s_left.imag
    X2[mask] = s_right.real
    Y2[mask] = s_right.imag


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------


def parse_trace_table(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray]:
    """从原始表格解析测线走向、迹线条数与端点坐标（纯向量化）。

    Returns:
        (ang0, n, XY, joint_strike_deg):
        - ang0: 测线走向角（度）
        - n: 迹线条数
        - XY: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]
        - joint_strike_deg: 每条迹线的节理走向（度）
    """
    # 1. 表头
    ang0, n = _parse_header(df)

    # 2. 数值矩阵（第3列已转为走向）
    M = _extract_numeric_block(df, n)

    r1 = M[:, _COL_R1]
    r2 = M[:, _COL_R2]
    ang = M[:, _COL_A]
    r3 = M[:, _COL_R3]
    r4 = M[:, _COL_R4]
    r5 = M[:, _COL_R5]
    r6 = M[:, _COL_R6]

    # 3. 角度预处理
    ang_0 = 90.0 - ang0 if ang0 < 90.0 else 450.0 - ang0
    rad_0 = math.radians(ang_0)
    ang1 = np.mod(270.0 - ang, 360.0)

    # 4. 侧向判定
    has_left = r4 != 0.0
    has_right = r6 != 0.0

    # 5. 预计算公共复数向量
    z1 = r1 * np.exp(1j * rad_0)
    vec_perp_left = np.exp(1j * (rad_0 + math.pi / 2))
    vec_perp_right = np.exp(1j * (rad_0 - math.pi / 2))
    vec_skew_a = np.exp(1j * _get_adjusted_angle_vec(ang_0, ang1, invert=False))
    vec_skew_e = np.exp(1j * _get_adjusted_angle_vec(ang_0, ang1, invert=True))

    # 6. 分情况计算端点
    X1, Y1, X2, Y2 = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    mask_l = has_left & (~has_right)
    if np.any(mask_l):
        _compute_case_left(X1, Y1, X2, Y2, mask_l, z1, r2, r3, r4, vec_perp_left, vec_skew_a)

    mask_r = (~has_left) & has_right
    if np.any(mask_r):
        _compute_case_right(X1, Y1, X2, Y2, mask_r, z1, r2, r5, r6, vec_perp_right, vec_skew_e)

    mask_b = has_left & has_right
    if np.any(mask_b):
        _compute_case_both(
            X1, Y1, X2, Y2, mask_b, z1, r2, r3, r4, r5, r6,
            vec_perp_left, vec_perp_right, vec_skew_a, vec_skew_e,
        )

    XY = np.column_stack((X1, Y1, X2, Y2))
    return ang0, n, XY, ang
