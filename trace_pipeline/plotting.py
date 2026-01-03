"""迹线绘图工具。

本模块封装了绘制迹线图所需的样式配置、数据转换和导出功能：
- configure_plotting_style: 配置 matplotlib 中文字体与符号
- build_nan_lines: 将线段端点数组转换为带 NaN 分隔的一维坐标序列，便于一次性绘制多段不连续线
- style_trace_axes: 统一坐标轴样式（等比例、隐藏刻度等）
- export_figure: 将 Figure 导出为图片文件
- render_trace_plot: 根据 X/Y 序列生成单张图片并保存
"""
from __future__ import annotations

import os
from typing import Tuple
import matplotlib.pyplot as plt
import numpy as np

# 允许图形与控制台输出展示中文
def configure_plotting_style():
    """配置 matplotlib 绘图样式（字体等）。"""
    # 设置中文字体优先列表，通常优先使用系统自带的中文字体以保证中文可见
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
    # 输入 XY 形状为 (N,4)，每行表示 [x1,y1,x2,y2]
    n = XY.shape[0]
    # 将每条线的起点 x、终点 x、以及一个 NaN 组合为列，然后展开为一维序列
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    """设置迹线图的坐标轴样式（等比例、隐藏刻度、白色背景）。"""
    # 等比例显示，确保真实长度关系
    ax.set_aspect("equal")
    # 隐藏刻度，使图片更像示意图/图样
    ax.set_xticks([])
    ax.set_yticks([])
    # 设置边框线宽以保持清晰
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    # 设置图形与画布背景为白色，导出时保持一致
    ax.set_facecolor("white")
    ax.get_figure().patch.set_facecolor("white")
    return ax


def export_figure(fig: plt.Figure, output_dir: str, filename: str, dpi: int = 300) -> str:
    """导出图片到输出目录并返回完整路径。"""

    # 确保目录存在再导出，返回实际保存位置
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    # 紧凑布局避免标签或标题被裁剪
    fig.tight_layout()
    # 指定 facecolor 以避免透明背景在某些查看器中出现异常
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

    # 建立大尺寸画布（单位为英寸，这里将厘米转换为英寸以便控制输出分辨率）
    fig, ax = plt.subplots(figsize=(24 / 2.54, 12 / 2.54), dpi=dpi)
    # 绘制黑色细线表示所有线段（X_plot/Y_plot 已包含 NaN 分隔）
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    style_trace_axes(ax)
    # 标题使用较小字号以便在高分辨率图像中不占用过多空间
    ax.set_title(title, fontsize=12)
    export_figure(fig, output_dir, filename, dpi=dpi)
    # 关闭图像释放内存
    plt.close(fig)
