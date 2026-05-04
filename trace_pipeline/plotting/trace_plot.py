"""迹线长度图绘制。"""
from __future__ import annotations

from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np

from ._helpers import new_figure, save_figure

__all__ = ["render_trace_plot", "segments_to_xy"]

_TRACE_FIGSIZE_CM: Tuple[float, float] = (24, 12)
_DEFAULT_TRACE_DPI = 300
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 1.0


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


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景。"""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    ax.set_facecolor("white")


def render_trace_plot(
    segments: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    dpi: int = _DEFAULT_TRACE_DPI,
    figsize_cm: Tuple[float, float] = _TRACE_FIGSIZE_CM,
) -> str:
    """绘制并保存单张迹线长度图。

    Returns:
        输出文件的完整路径。
    """
    X_plot, Y_plot = segments_to_xy(segments)
    fig, ax = new_figure(figsize_cm, dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=_TRACE_LINE_COLOR, linewidth=_TRACE_LINE_WIDTH)
    _style_trace_axes(ax)
    ax.set_title(title, fontsize=12)
    return save_figure(fig, output_dir, filename, dpi=dpi)
