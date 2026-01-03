"""迹线绘图工具。"""
from __future__ import annotations

import os
from typing import Tuple
import matplotlib.pyplot as plt
import numpy as np

# 允许图形与控制台输出展示中文
def configure_plotting_style():
    """配置 matplotlib 绘图样式（字体等）。"""
    plt.rcParams["font.sans-serif"] = [
        "SimHei",
        "Microsoft YaHei",
        "Arial Unicode MS",
        "sans-serif",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def build_nan_lines(XY: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    构建用于 matplotlib 绘制的断开线段数据。
    
    Args:
        XY: 形状为 (N, 4) 的数组，每行 [x1, y1, x2, y2]
        
    Returns:
        (X_plot, Y_plot): 包含 NaN 分隔符的一维数组
    """
    # 每条线段后拼接 NaN 以断开折线，便于 matplotlib 分段绘制
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    """设置迹线图的坐标轴样式（等比例、隐藏刻度、白色背景）。"""
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    ax.set_facecolor("white")
    ax.get_figure().patch.set_facecolor("white")
    return ax


def export_figure(fig: plt.Figure, output_dir: str, filename: str, dpi: int = 300) -> str:
    """导出图片到输出目录并返回完整路径。"""

    # 确保目录存在再导出，返回实际保存位置
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(full_path, dpi=dpi, facecolor="white")
    return full_path


def render_trace_plot(
    X_plot: np.ndarray, 
    Y_plot: np.ndarray, 
    title: str, 
    output_dir: str, 
    filename: str, 
    dpi: int = 300
) -> None:
    """绘制单张迹线图并导出到指定目录。"""

    fig, ax = plt.subplots(figsize=(24 / 2.54, 12 / 2.54), dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    style_trace_axes(ax)
    ax.set_title(title, fontsize=12)
    export_figure(fig, output_dir, filename, dpi=dpi)
    plt.close(fig)
