import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple

from coordinate import coordinate


def resolve_paths(input_dir: str, output_dir: str) -> Tuple[str, str, str]:
    """Return usable input/output directories and the cwd fallback."""
    cwd = os.getcwd()
    in_dir = input_dir if os.path.isdir(input_dir) else cwd
    out_dir = output_dir if os.path.isdir(output_dir) else cwd
    return in_dir, out_dir, cwd


def to_strike_from_dip_direction(dd: float) -> float:
    """Convert dip direction to strike, matching the original MATLAB rules."""
    if dd >= 270:
        return dd + 90 - 360
    if dd >= 180:
        return dd - 90
    if dd >= 90:
        return dd - 90
    return dd + 90


def read_trace_table(base_path: str, excel_base: str, sheet: str) -> pd.DataFrame:
    """Load the input table, preferring .xlsx and falling back to .xls."""
    excel_path_xlsx = os.path.join(base_path, excel_base + ".xlsx")
    excel_path_xls = os.path.join(base_path, excel_base + ".xls")

    def _read(path: str, engine: str) -> pd.DataFrame:
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet, header=None)
        except ValueError:
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    if os.path.exists(excel_path_xlsx):
        return _read(excel_path_xlsx, engine="openpyxl")
    if os.path.exists(excel_path_xls):
        return _read(excel_path_xls, engine="xlrd")
    raise FileNotFoundError(f"未找到 {excel_base}.xlsx 或 {excel_base}.xls 在路径: {base_path}")


def parse_trace_geometry(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray, np.ndarray]:
    """Extract ang0, n, and computed coordinates/angles from the raw table."""
    ang0 = float(df.iloc[0, 7])
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors="coerce")[0]
    if np.isnan(n_num):
        raise ValueError(f"第1行第9列无法解析为数字，实际值: {n_raw!r}")
    n = int(n_num)

    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([to_strike_from_dip_direction(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    XY = np.zeros((n, 4), dtype=float)
    trace_lengths = np.zeros((n,), dtype=float)
    trace_angles = np.zeros((n,), dtype=float)

    for m in range(n):
        trace_lengths[m] = M[m, 4] + M[m, 6]
        trace_angles[m] = M[m, 2]
        X1, Y1, X2, Y2 = coordinate(
            ang0,
            M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6],
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY, trace_lengths, trace_angles


def build_polyline_arrays(XY: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Create NaN-separated coordinate arrays for plotting segments."""
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    """Apply consistent styling for trace plots."""
    plt.axis("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    try:
        ax.set_fontname("Times New Roman")
    except Exception:
        pass
    ax.set_facecolor("white")
    fig = ax.get_figure()
    fig.patch.set_facecolor("white")
    return ax
