"""几何计算：迹线端点与走向转换。

该模块实现向量化的迹线端点坐标计算，核心流程：
1. 解析 Excel 表头（测线走向、迹线数量）
2. 提取并校验数值矩阵，将倾向转为走向
3. 按左/右/双侧三种情况，使用复数向量计算端点坐标

所有角度计算均使用向量化操作，避免 Python 层循环。

Excel 数据布局约定（每行一条迹线，前 7 列为数值数据，第 8-9 列为表头信息）:
  列 0: r1 — 沿测线位移
  列 1: r2 — 垂直测线位移（正=左侧，负=右侧）
  列 2: 倾向（将被转为走向）
  列 3: r4 — 左迹长 1
  列 4: r5 — 左迹长 2
  列 5: r6 — 右迹长 1
  列 6: r7 — 右迹长 2
  列 7: ang0 — 测线走向角（度），仅首行有效
  列 8: n — 迹线条数，仅首行有效
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 列索引常量（0-based，映射 Excel 原始列位置）
# ---------------------------------------------------------------------------

# 数据区（前 7 列）
COL_R1 = 0  # 沿测线位移
COL_R2 = 1  # 垂直测线位移（正=左侧，负=右侧）
COL_DIP = 2  # 倾向（输入值，将被转为走向）
COL_R4 = 3  # 左侧迹长 1
COL_R5 = 4  # 左侧迹长 2
COL_R6 = 5  # 右侧迹长 1
COL_R7 = 6  # 右侧迹长 2

# 表头区（第 8-9 列，位于首行）
HEADER_COL_ANG0 = 7  # 测线走向角 ang0（度）
HEADER_COL_N = 8  # 迹线条数 n

# Excel 最低列数要求
_MIN_COLUMNS = HEADER_COL_N + 1  # 9

__all__ = [
    "COL_DIP",
    "COL_R1",
    "COL_R2",
    "COL_R4",
    "COL_R5",
    "COL_R6",
    "COL_R7",
    "dip_to_strike_vec",
    "parse_trace_table",
]


# ---------------------------------------------------------------------------
# 角度工具
# ---------------------------------------------------------------------------


def dip_to_strike_vec(dip_deg: np.ndarray) -> np.ndarray:
    """倾向 → 走向（向量化）。

    规则（与 MATLAB 原版一致）:
    - dd ≥ 270°  → strike = dd - 270°
    - 90° ≤ dd < 270° → strike = dd - 90°
    - dd < 90°  → strike = dd + 90°

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


def _get_adjusted_angle_vec(
    base_angle_deg: float,
    target_angles_deg: np.ndarray,
    invert: bool = False,
) -> np.ndarray:
    """将目标角折叠到以基准角为参考的半平面内，返回弧度制。

    工作原理:
    - 基准角 base_angle 定义了一条参考方向线（0°–360°）。
    - 对于每个 target 角，判断其是否落在 base_angle 所确定的"前向半平面"内。
      * base ≤ 180°: 半平面为 (base, base+180)
      * base > 180°: 半平面为 (base-180, base)
    - 若目标角不在半平面内，则加 180° 翻转到对侧。
    - invert=True 时反转判定逻辑（用于计算右侧方向）。

    Args:
        base_angle_deg: 基准走向角（度），0–360。
        target_angles_deg: 待调整的目标角数组（度）。
        invert: 是否反转半平面判定。

    Returns:
        调整后的角度弧度数组，形状与 target_angles_deg 一致。
    """
    targets = np.mod(np.asarray(target_angles_deg, dtype=float), 360.0)
    base = float(base_angle_deg) % 360.0

    if base <= 180.0:
        # 半平面: (base, base+180)
        in_half = (base < targets) & (targets < base + 180.0)
    else:
        # 半平面: (base-180, base)
        in_half = (base - 180.0 < targets) & (targets < base)

    # invert 控制将"在半平面内"还是"在半平面外"的角度加 180°
    if invert:
        adjusted = np.where(in_half, targets + 180.0, targets)
    else:
        adjusted = np.where(in_half, targets, targets + 180.0)

    return np.radians(np.mod(adjusted, 360.0))


# ---------------------------------------------------------------------------
# 表头与数据提取
# ---------------------------------------------------------------------------


def _parse_header(df: pd.DataFrame) -> Tuple[float, int]:
    """从 DataFrame 首行解析测线走向 ang0 与迹线条数 n。

    约定（见模块级文档）:
      第 HEADER_COL_ANG0 列为 ang0（度），第 HEADER_COL_N 列为 n。
    """
    if df.empty:
        raise ValueError("输入表格为空")
    if df.shape[1] < _MIN_COLUMNS:
        raise ValueError(
            f"输入表格至少需要 {_MIN_COLUMNS} 列，当前仅有 {df.shape[1]} 列"
        )

    try:
        ang0 = float(pd.to_numeric(df.iloc[0, HEADER_COL_ANG0]))
        n = int(pd.to_numeric(df.iloc[0, HEADER_COL_N]))
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError(
            f"无法解析表头（第1行第{HEADER_COL_ANG0 + 1}-{HEADER_COL_N + 1}列）：{exc}"
        ) from exc

    if not np.isfinite(ang0):
        raise ValueError("表头中的走向角度无效（inf 或 NaN）")
    if n <= 0:
        raise ValueError(f"迹线条数必须为正数，当前为 {n}")
    if len(df.index) < n:
        raise ValueError(f"迹线条数 {n} 超出数据行数 {len(df.index)}")

    # 规范化 ang0 到 [0, 360)
    ang0 = ang0 % 360.0
    return ang0, n


def _extract_numeric_block(df: pd.DataFrame, n: int) -> np.ndarray:
    """提取前 n 行、前 7 列数值矩阵，并将倾向列转为走向。

    Returns:
        (n, 7) float64 矩阵，其中第 COL_DIP 列已从倾向转为走向。

    Raises:
        ValueError: 若数据块包含无法转为数值的内容。
    """
    numeric_block = df.iloc[:n, 0:7].apply(pd.to_numeric, errors="coerce")
    M = numeric_block.to_numpy(dtype=float)

    if np.isnan(M).any():
        bad_rows, bad_cols = np.where(np.isnan(M))
        raise ValueError(
            f"数据块第 {int(bad_rows[0]) + 1} 行第 {int(bad_cols[0]) + 1} 列"
            f"包含非数值内容"
        )

    # 将倾向列转为走向
    M[:, COL_DIP] = dip_to_strike_vec(M[:, COL_DIP])
    return M


# ---------------------------------------------------------------------------
# 端点计算（三种情况）
# ---------------------------------------------------------------------------


def _compute_case_left(
    X1: np.ndarray,
    Y1: np.ndarray,
    X2: np.ndarray,
    Y2: np.ndarray,
    mask: np.ndarray,
    z1: np.ndarray,
    col_r2: np.ndarray,
    col_r4: np.ndarray,
    col_r5: np.ndarray,
    vec_perp_left: complex,
    vec_skew_a: np.ndarray,
) -> None:
    """Case 1 — 仅左侧有迹线数据 (r5 ≠ 0, r7 = 0)。

    公式:
      start = z1 + r2·L_perp + r4·L_skew
      end   = start + r5·L_skew
    """
    _z1 = z1[mask]
    _r2 = col_r2[mask]
    _r4 = col_r4[mask]
    _r5 = col_r5[mask]
    _skew = vec_skew_a[mask]

    s1 = _z1 + _r2 * vec_perp_left + _r4 * _skew
    s2 = s1 + _r5 * _skew
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
    col_r2: np.ndarray,
    col_r6: np.ndarray,
    col_r7: np.ndarray,
    vec_perp_right: complex,
    vec_skew_e: np.ndarray,
) -> None:
    """Case 2 — 仅右侧有迹线数据 (r5 = 0, r7 ≠ 0)。

    公式:
      start = z1 + r2·R_perp + r6·R_skew
      end   = start + r7·R_skew
    """
    _z1 = z1[mask]
    _r2 = col_r2[mask]
    _r6 = col_r6[mask]
    _r7 = col_r7[mask]
    _skew = vec_skew_e[mask]

    s1 = _z1 + _r2 * vec_perp_right + _r6 * _skew
    s2 = s1 + _r7 * _skew
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
    col_r2: np.ndarray,
    col_r4: np.ndarray,
    col_r5: np.ndarray,
    col_r6: np.ndarray,
    col_r7: np.ndarray,
    vec_perp_left: complex,
    vec_perp_right: complex,
    vec_skew_a: np.ndarray,
    vec_skew_e: np.ndarray,
) -> None:
    """Case 3 — 双侧均有迹线数据 (r5 ≠ 0, r7 ≠ 0)。

    公式:
      s_left  = z1 + r2·L_perp + (r4+r5)·L_skew
      s_right = z1 + r2·R_perp + (r6+r7)·R_skew
    """
    _z1 = z1[mask]
    _r2 = col_r2[mask]
    _skew_a = vec_skew_a[mask]
    _skew_e = vec_skew_e[mask]

    s_left = _z1 + _r2 * vec_perp_left + (col_r4[mask] + col_r5[mask]) * _skew_a
    s_right = _z1 + _r2 * vec_perp_right + (col_r6[mask] + col_r7[mask]) * _skew_e
    X1[mask] = s_left.real
    Y1[mask] = s_left.imag
    X2[mask] = s_right.real
    Y2[mask] = s_right.imag


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------


def parse_trace_table(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray]:
    """从原始表格解析测线走向、迹线条数与端点坐标（纯向量化）。

    本函数是 geometry 模块的主入口，整合了表头解析、数值提取、
    角度转换与三种情况的端点计算。

    Args:
        df: 原始 Excel DataFrame，需满足模块级文档描述的列布局约定。

    Returns:
        (ang0, n, XY, joint_strike_deg):
        - ang0: 测线走向角（度），已规范化到 [0, 360)
        - n: 迹线条数
        - XY: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]
        - joint_strike_deg: 每条迹线的节理走向（度），长度 N

    Raises:
        ValueError: 表格格式不符或数据无法解析时抛出。
    """
    # ---- 1. 表头 ----
    ang0, n = _parse_header(df)

    # ---- 2. 数值矩阵（倾向列已转为走向） ----
    M = _extract_numeric_block(df, n)

    col_r1 = M[:, COL_R1]  # 沿测线位移
    col_r2 = M[:, COL_R2]  # 垂直测线位移
    joint_strike = M[:, COL_DIP]  # 节理走向（已由倾向转换）
    col_r4 = M[:, COL_R4]  # 左侧迹长 1
    col_r5 = M[:, COL_R5]  # 左侧迹长 2
    col_r6 = M[:, COL_R6]  # 右侧迹长 1
    col_r7 = M[:, COL_R7]  # 右侧迹长 2

    # ---- 3. 角度预处理 ----
    # 基准角转换：将测线走向 ang0 转换为计算使用的基准角 ang_base
    #   若 ang0 < 90°:  ang_base = 90° - ang0（将测线旋转到垂直方向）
    #   若 ang0 ≥ 90°: ang_base = 450° - ang0（等价于 90° - (ang0 - 360°)）
    ang_base_deg = 90.0 - ang0 if ang0 < 90.0 else 450.0 - ang0
    rad_base = math.radians(ang_base_deg)

    # 节理方向角：270° - strike，规范化到 [0, 360)
    ang_joint = np.mod(270.0 - joint_strike, 360.0)

    # ---- 4. 侧向判定 ----
    # r5 ≠ 0 表示左侧存在迹线；r7 ≠ 0 表示右侧存在迹线
    mask_left = col_r5 != 0.0
    mask_right = col_r7 != 0.0

    # ---- 5. 预计算公共复数向量 ----
    # z1: 测线方向上的基准点（r1 投影到 rad_base 方向）
    z1_base = col_r1 * np.exp(1j * rad_base)

    # 垂直方向向量（左/右）
    vec_perp_left = np.exp(1j * (rad_base + math.pi / 2))  # +90°
    vec_perp_right = np.exp(1j * (rad_base - math.pi / 2))  # -90°

    # 节理偏斜方向向量（左半平面 / 右半平面）
    vec_skew_left = np.exp(1j * _get_adjusted_angle_vec(ang_base_deg, ang_joint, invert=False))
    vec_skew_right = np.exp(1j * _get_adjusted_angle_vec(ang_base_deg, ang_joint, invert=True))

    # ---- 6. 分情况计算端点 ----
    X1, Y1, X2, Y2 = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)

    # Case 1: 仅左侧
    mask_only_left = mask_left & (~mask_right)
    if np.any(mask_only_left):
        _compute_case_left(
            X1, Y1, X2, Y2, mask_only_left,
            z1_base, col_r2, col_r4, col_r5,
            vec_perp_left, vec_skew_left,
        )

    # Case 2: 仅右侧
    mask_only_right = (~mask_left) & mask_right
    if np.any(mask_only_right):
        _compute_case_right(
            X1, Y1, X2, Y2, mask_only_right,
            z1_base, col_r2, col_r6, col_r7,
            vec_perp_right, vec_skew_right,
        )

    # Case 3: 双侧
    mask_both = mask_left & mask_right
    if np.any(mask_both):
        _compute_case_both(
            X1, Y1, X2, Y2, mask_both,
            z1_base, col_r2, col_r4, col_r5, col_r6, col_r7,
            vec_perp_left, vec_perp_right, vec_skew_left, vec_skew_right,
        )

    # ---- 7. 组装输出 ----
    XY = np.column_stack((X1, Y1, X2, Y2))
    return ang0, n, XY, joint_strike
