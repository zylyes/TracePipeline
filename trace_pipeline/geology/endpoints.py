"""迹线几何计算 — 表头解析与端点坐标的向量化计算。

核心流程：
  1. 解析 Excel 表头（测线走向、迹线条数）
  2. 提取数值矩阵，倾向 → 走向转换
  3. 按左/右/双侧三种情况，复数向量计算端点坐标

Excel 列布局（0-based）:
  0: 沿测线位移 r1       4: 左迹长 2 (r5)
  1: 垂直测线位移 r2      5: 右迹长 1 (r6)
  2: 倾向（输入，转为走向） 6: 右迹长 2 (r7)
  3: 左迹长 1 (r4)        7: 测线走向 ang0 [首行]
                           8: 迹线条数 n [首行]

MATLAB ↔ Python 变量对照（见 docs/matlab_reference/Coordinate.m）:
  MATLAB          ┃ Python
  ─────────────── ┃ ─────────────────────────────
  ang0            ┃ azimuth
  dd              ┃ M[:, COL_DIP]（转换前=倾向，转换后=走向）
  traceAngles     ┃ joint_strike
  ang_0 / rad_0   ┃ ang_base_deg / rad_base
  ang1            ┃ ang_joint
  rada / rade     ┃ fold_to_halfplane(..., invert=False/True) 结果
  r1..r7          ┃ r1..r7（同名）
  z1              ┃ z1_base（复数向量）
  r4≠0,r6=0       ┃ mask_only_left   → _compute_left_only
  r4=0,r6≠0       ┃ mask_only_right  → _compute_right_only
  r4≠0,r6≠0       ┃ mask_both        → _compute_bilateral

历史文件名：geometry.py（位于 trace_pipeline 根）。
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pandas as pd

from .angles import dip_to_strike, fold_to_halfplane

# ===========================================================================
# Excel 列索引常量
# ===========================================================================

COL_SHIFT_ALONG = 0   # r1 — 沿测线位移
COL_SHIFT_ACROSS = 1  # r2 — 垂直测线位移
COL_DIP = 2           # 倾向（输入值，运行时转为走向）
COL_LEFT_LEN1 = 3     # r4 — 左侧迹长 1
COL_LEFT_LEN2 = 4     # r5 — 左侧迹长 2
COL_RIGHT_LEN1 = 5    # r6 — 右侧迹长 1
COL_RIGHT_LEN2 = 6    # r7 — 右侧迹长 2

COL_HEADER_AZIMUTH = 7  # 测线走向角（度），仅首行
COL_HEADER_COUNT = 8    # 迹线条数，仅首行

_MIN_COLUMNS = COL_HEADER_COUNT + 1


# ===========================================================================
# 表头解析
# ===========================================================================


def _parse_header(df: pd.DataFrame) -> Tuple[float, int]:
    """从 DataFrame 首行解析测线走向与迹线条数。"""
    if df.empty:
        raise ValueError("输入表格为空")
    if df.shape[1] < _MIN_COLUMNS:
        raise ValueError(f"输入表格至少需要 {_MIN_COLUMNS} 列，当前仅有 {df.shape[1]} 列")

    try:
        ang0 = float(pd.to_numeric(df.iloc[0, COL_HEADER_AZIMUTH]))
        n = int(pd.to_numeric(df.iloc[0, COL_HEADER_COUNT]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(
            f"无法解析表头（第1行第{COL_HEADER_AZIMUTH + 1}-{COL_HEADER_COUNT + 1}列）：{exc}"
        ) from exc

    if not np.isfinite(ang0):
        raise ValueError("表头中的走向角度无效（inf 或 NaN）")
    if n <= 0:
        raise ValueError(f"迹线条数必须为正数，当前为 {n}")
    if len(df.index) < n:
        raise ValueError(f"迹线条数 {n} 超出数据行数 {len(df.index)}")

    return ang0 % 360.0, n


def _extract_numeric_block(df: pd.DataFrame, n: int) -> np.ndarray:
    """提取前 n 行 × 7 列数值矩阵，倾向列转为走向。"""
    numeric_block = df.iloc[:n, 0:7].apply(pd.to_numeric, errors="coerce")
    M = numeric_block.to_numpy(dtype=float)

    if np.isnan(M).any():
        bad_rows, bad_cols = np.where(np.isnan(M))
        raise ValueError(
            f"数据块第 {int(bad_rows[0]) + 1} 行第 {int(bad_cols[0]) + 1} 列"
            f"包含非数值内容"
        )

    M[:, COL_DIP] = dip_to_strike(M[:, COL_DIP])
    return M


# ===========================================================================
# 三种情形的端点计算
# ===========================================================================


def _compute_left_only(
    X1: np.ndarray, Y1: np.ndarray, X2: np.ndarray, Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray, r2: np.ndarray, r4: np.ndarray, r5: np.ndarray,
    vec_perp_left: complex, vec_skew: np.ndarray,
) -> None:
    """Case 1 — 仅左侧有迹线 (r5 ≠ 0, r7 = 0)。

    start = z1 + r2·L_perp + r4·L_skew
    end   = start + r5·L_skew
    """
    _z1 = z1[mask]
    _skew = vec_skew[mask]
    s1 = _z1 + r2[mask] * vec_perp_left + r4[mask] * _skew
    s2 = s1 + r5[mask] * _skew
    X1[mask], Y1[mask] = s1.real, s1.imag
    X2[mask], Y2[mask] = s2.real, s2.imag


def _compute_right_only(
    X1: np.ndarray, Y1: np.ndarray, X2: np.ndarray, Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray, r2: np.ndarray, r6: np.ndarray, r7: np.ndarray,
    vec_perp_right: complex, vec_skew: np.ndarray,
) -> None:
    """Case 2 — 仅右侧有迹线 (r5 = 0, r7 ≠ 0)。

    start = z1 + r2·R_perp + r6·R_skew
    end   = start + r7·R_skew
    """
    _z1 = z1[mask]
    _skew = vec_skew[mask]
    s1 = _z1 + r2[mask] * vec_perp_right + r6[mask] * _skew
    s2 = s1 + r7[mask] * _skew
    X1[mask], Y1[mask] = s1.real, s1.imag
    X2[mask], Y2[mask] = s2.real, s2.imag


def _compute_bilateral(
    X1: np.ndarray, Y1: np.ndarray, X2: np.ndarray, Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray, r2: np.ndarray, r4: np.ndarray, r5: np.ndarray,
    r6: np.ndarray, r7: np.ndarray,
    vec_perp_left: complex, vec_perp_right: complex,
    vec_skew_left: np.ndarray, vec_skew_right: np.ndarray,
) -> None:
    """Case 3 — 双侧均有迹线 (r5 ≠ 0, r7 ≠ 0)。

    left  = z1 + r2·L_perp + (r4+r5)·L_skew
    right = z1 + r2·R_perp + (r6+r7)·R_skew
    """
    _z1 = z1[mask]
    _r2 = r2[mask]
    s_left = _z1 + _r2 * vec_perp_left + (r4[mask] + r5[mask]) * vec_skew_left[mask]
    s_right = _z1 + _r2 * vec_perp_right + (r6[mask] + r7[mask]) * vec_skew_right[mask]
    X1[mask], Y1[mask] = s_left.real, s_left.imag
    X2[mask], Y2[mask] = s_right.real, s_right.imag


# ===========================================================================
# 主入口
# ===========================================================================


def compute_endpoints(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray, np.ndarray]:
    """从原始表格解析测线走向、迹线条数与端点坐标（纯向量化）。

    整合表头解析、数值提取、角度转换与三种情况的端点计算。

    Returns:
        (azimuth, count, endpoints, joint_strikes, segment_lengths):
        - azimuth: 测线走向角（度），[0, 360)
        - count: 迹线条数
        - endpoints: 端点坐标 (N, 4), [x1, y1, x2, y2]
        - joint_strikes: 节理走向（度），长度 N
        - segment_lengths: 沿测段的迹线长度 r5+r7（MATLAB 定义），长度 N
    """
    azimuth, n = _parse_header(df)
    M = _extract_numeric_block(df, n)

    r1 = M[:, COL_SHIFT_ALONG]
    r2 = M[:, COL_SHIFT_ACROSS]
    joint_strike = M[:, COL_DIP]
    r4 = M[:, COL_LEFT_LEN1]
    r5 = M[:, COL_LEFT_LEN2]
    r6 = M[:, COL_RIGHT_LEN1]
    r7 = M[:, COL_RIGHT_LEN2]

    segment_lengths = r5 + r7

    # ---- 基准角 ----
    ang_base_deg = 90.0 - azimuth if azimuth < 90.0 else 450.0 - azimuth
    rad_base = math.radians(ang_base_deg)

    # 节理方向角
    ang_joint = np.mod(270.0 - joint_strike, 360.0)

    # ---- 侧向判定 ----
    has_left = r5 != 0.0
    has_right = r7 != 0.0

    # ---- 复数向量 ----
    z1_base = r1 * np.exp(1j * rad_base)
    vec_perp_left = np.exp(1j * (rad_base + math.pi / 2))
    vec_perp_right = np.exp(1j * (rad_base - math.pi / 2))
    vec_skew_left = np.exp(1j * fold_to_halfplane(ang_base_deg, ang_joint, invert=False))
    vec_skew_right = np.exp(1j * fold_to_halfplane(ang_base_deg, ang_joint, invert=True))

    # ---- 分情况计算 ----
    X1, Y1, X2, Y2 = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    mask_only_left = has_left & (~has_right)
    if np.any(mask_only_left):
        _compute_left_only(
            X1, Y1, X2, Y2, mask_only_left,
            z1_base, r2, r4, r5, vec_perp_left, vec_skew_left,
        )

    mask_only_right = (~has_left) & has_right
    if np.any(mask_only_right):
        _compute_right_only(
            X1, Y1, X2, Y2, mask_only_right,
            z1_base, r2, r6, r7, vec_perp_right, vec_skew_right,
        )

    mask_both = has_left & has_right
    if np.any(mask_both):
        _compute_bilateral(
            X1, Y1, X2, Y2, mask_both,
            z1_base, r2, r4, r5, r6, r7,
            vec_perp_left, vec_perp_right, vec_skew_left, vec_skew_right,
        )

    endpoints = np.column_stack((X1, Y1, X2, Y2))
    return azimuth, n, endpoints, joint_strike, segment_lengths


__all__ = [
    "COL_DIP",
    "COL_HEADER_AZIMUTH", "COL_HEADER_COUNT",
    "COL_LEFT_LEN1", "COL_LEFT_LEN2",
    "COL_RIGHT_LEN1", "COL_RIGHT_LEN2",
    "COL_SHIFT_ALONG", "COL_SHIFT_ACROSS",
    "compute_endpoints",
]
