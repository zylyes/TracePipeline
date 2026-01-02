"""迹线几何解析与角度转换工具。"""
from typing import Tuple
import numpy as np
import pandas as pd
from trace_coordinate import compute_joint_endpoints


def convert_dip_to_strike(dd: float) -> float:
    """将倾向转换为走向角度，保持与原 MATLAB 规则一致。"""
    if dd >= 270:
        return dd + 90 - 360
    if dd >= 180:
        return dd - 90
    if dd >= 90:
        return dd - 90
    return dd + 90


def parse_trace_table(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray, np.ndarray]:
    """
    从原始表格中提取走向、条数、端点坐标、迹长与迹线角度。
    返回顺序与后续绘图及导出步骤兼容。
    """
    ang0 = float(df.iloc[0, 7])  # 测线走向角度
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors="coerce")[0]
    if np.isnan(n_num):
        raise ValueError(f"Row 1 col 9 is not numeric: {n_raw!r}")
    n = int(n_num)

    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([convert_dip_to_strike(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    XY = np.zeros((n, 4), dtype=float)
    trace_lengths = np.zeros((n,), dtype=float)
    trace_angles = np.zeros((n,), dtype=float)

    for m in range(n):
        trace_lengths[m] = M[m, 4] + M[m, 6]
        trace_angles[m] = M[m, 2]
        X1, Y1, X2, Y2 = compute_joint_endpoints(
            ang0,
            M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6],
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY, trace_lengths, trace_angles
