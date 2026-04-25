"""迹线绘图与玫瑰花瓣图。

本模块封装 matplotlib 的样式配置与两类图片的导出：
- 迹线长度图（原始/旋转后）
- 节理走向玫瑰花瓣图
"""
from __future__ import annotations

import os
from typing import Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# 全局样式
# ---------------------------------------------------------------------------

# 中文字体候选列表（按优先级）
_CJK_FONT_CANDIDATES = [
    "SimHei",
    "Microsoft YaHei",
    "Arial Unicode MS",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
    "sans-serif",
]


def configure_plotting_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示。

    注意：此函数修改全局 rcParams，应在程序启动时调用一次。
    """
    matplotlib.rcParams["font.sans-serif"] = _CJK_FONT_CANDIDATES
    matplotlib.rcParams["axes.unicode_minus"] = False


# ---------------------------------------------------------------------------
# 数据转换
# ---------------------------------------------------------------------------


def build_nan_lines(XY: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """将 (N,4) 线段数组转为带 NaN 分隔的一维 X/Y 序列。"""
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


# ---------------------------------------------------------------------------
# 玫瑰图数据
# ---------------------------------------------------------------------------


def _fold_strike_angles(strike_deg: np.ndarray) -> np.ndarray:
    """将走向角折叠到 [0, 180)。"""
    folded = np.mod(np.asarray(strike_deg, dtype=float), 180.0)
    folded[np.isclose(folded, 180.0)] = 0.0
    return folded


def _compute_rose_histogram(
    strike_deg: np.ndarray,
    bin_width: float = 10.0,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """计算玫瑰图柱体的角度（弧度）、频数与柱宽（弧度）。"""
    if not (0 < bin_width <= 180):
        raise ValueError("rose bin_width 必须在 (0, 180] 范围内")

    folded = _fold_strike_angles(strike_deg)
    if folded.size == 0:
        return np.array([]), np.array([]), np.deg2rad(bin_width)

    bin_count = max(1, int(round(180.0 / bin_width)))
    edges = np.linspace(0.0, 180.0, num=bin_count + 1)
    counts, _ = np.histogram(folded, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2.0

    theta = np.deg2rad(np.concatenate([centers, centers + 180.0]))
    radii = np.concatenate([counts, counts])
    width = np.deg2rad(edges[1] - edges[0])
    return theta, radii, width


# ---------------------------------------------------------------------------
# 公共绘图辅助
# ---------------------------------------------------------------------------


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景。"""
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    ax.set_facecolor("white")


def _export_figure(
    fig: plt.Figure,
    output_dir: str,
    filename: str,
    dpi: int = 300,
) -> str:
    """保存并关闭图形，返回完整输出路径。"""
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(full_path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return full_path


def _new_figure(
    figsize_cm: Tuple[float, float],
    dpi: int = 300,
    subplot_kw: dict | None = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """创建指定厘米尺寸的图形并返回 (fig, ax)。"""
    w_inch, h_inch = figsize_cm[0] / 2.54, figsize_cm[1] / 2.54
    fig, ax = plt.subplots(figsize=(w_inch, h_inch), dpi=dpi, subplot_kw=subplot_kw or {})
    fig.patch.set_facecolor("white")
    return fig, ax


# ---------------------------------------------------------------------------
# 迹线图
# ---------------------------------------------------------------------------


def render_trace_plot(
    X_plot: np.ndarray,
    Y_plot: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    dpi: int = 300,
) -> None:
    """绘制并保存单张迹线长度图。"""
    fig, ax = _new_figure((24, 12), dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    _style_trace_axes(ax)
    ax.set_title(title, fontsize=12)
    _export_figure(fig, output_dir, filename, dpi=dpi)


# ---------------------------------------------------------------------------
# 玫瑰花瓣图
# ---------------------------------------------------------------------------


def render_rose_plot(
    strike_deg: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    bin_width: float = 10.0,
    dpi: int = 300,
) -> None:
    """绘制并保存节理走向玫瑰花瓣图。"""
    theta, radii, width = _compute_rose_histogram(strike_deg, bin_width=bin_width)

    fig, ax = _new_figure((16, 16), dpi=dpi, subplot_kw={"projection": "polar"})
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 30))
    ax.grid(color="#aab7b8", alpha=0.7, linewidth=0.8)

    if radii.size:
        ax.bar(
            theta, radii,
            width=width, bottom=0.0,
            color="#4472c4", edgecolor="#1f1f1f",
            linewidth=0.8, alpha=0.85, align="center",
        )
        ax.set_ylim(0, max(1, int(radii.max())))
    else:
        ax.set_ylim(0, 1)

    ax.set_title(title, fontsize=12, pad=18)
    _export_figure(fig, output_dir, filename, dpi=dpi)
