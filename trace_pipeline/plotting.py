"""迹线图与玫瑰花瓣图绘制。

封装 matplotlib 样式配置与两类图片导出：
  - 迹线长度图（原始 / 旋转后）
  - 节理走向玫瑰花瓣图

全局样式通过 configure_style() 配置，程序启动时调用一次。
所有绘图函数无副作用：创建新 Figure → 绘制 → 保存 → 关闭。
"""
from __future__ import annotations

import logging
import os
from typing import List, Tuple

import matplotlib
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

from .angles import fold_strikes_to_semicircle
from .transforms import segments_to_xy

logger = logging.getLogger(__name__)

# ===========================================================================
# 样式常量
# ===========================================================================

_CJK_FONT_CANDIDATES: List[str] = [
    "SimHei",
    "Microsoft YaHei",
    "Arial Unicode MS",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "sans-serif",
]

_TRACE_FIGSIZE_CM: Tuple[float, float] = (24, 12)
_ROSE_FIGSIZE_CM: Tuple[float, float] = (16, 16)

_DEFAULT_TRACE_DPI = 300
_DEFAULT_ROSE_DPI = 400

_ROSE_GRID_COLOR = "#aab7b8"
_ROSE_BAR_COLOR = "#4472c4"
_ROSE_BAR_EDGE = "#1f1f1f"
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 1.0


# ===========================================================================
# 字体配置
# ===========================================================================


def _detect_cjk_fonts() -> List[str]:
    """扫描系统已安装的 CJK 字体，返回可用字体名列表。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return [f for f in _CJK_FONT_CANDIDATES if f in available]


def configure_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示（幂等）。"""
    available_cjk = _detect_cjk_fonts()

    existing = list(matplotlib.rcParams.get("font.sans-serif", ["sans-serif"]))
    existing_filtered = [f for f in existing if f not in available_cjk]

    if available_cjk:
        font_list = available_cjk + existing_filtered
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = font_list
        logger.info("检测到 CJK 字体: %s", ", ".join(available_cjk[:3]))
    else:
        font_list = existing_filtered
        logger.warning(
            "未检测到 CJK 字体，中文标题可能无法正常显示。"
            "建议安装 SimHei / Microsoft YaHei 等中文字体。"
        )

    matplotlib.rcParams["axes.unicode_minus"] = False
    logger.debug("matplotlib 全局样式已配置")


# ===========================================================================
# 玫瑰图数据
# ===========================================================================


def _compute_rose_histogram(
    strike_deg: np.ndarray,
    bin_width: float = 10.0,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """计算玫瑰图柱体的角度（弧度）、频数与柱宽（弧度）。"""
    if not (0 < bin_width <= 180):
        raise ValueError("rose bin_width 必须在 (0, 180] 范围内")

    folded = fold_strikes_to_semicircle(strike_deg)
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


# ===========================================================================
# 绘图辅助
# ===========================================================================


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景。"""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    ax.set_facecolor("white")


def _save_figure(fig: plt.Figure, output_dir: str, filename: str, dpi: int = 300) -> str:
    """保存并关闭图形，返回完整输出路径。"""
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    try:
        fig.tight_layout(pad=1.0)
        fig.savefig(full_path, dpi=dpi, facecolor="white", bbox_inches="tight")
    finally:
        plt.close(fig)
    return full_path


def _new_figure(
    figsize_cm: Tuple[float, float],
    dpi: int = 300,
    subplot_kw: dict | None = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """创建指定厘米尺寸的图形并返回 (fig, ax)。"""
    w_inch, h_inch = figsize_cm[0] / 2.54, figsize_cm[1] / 2.54
    fig, ax = plt.subplots(
        figsize=(w_inch, h_inch),
        dpi=dpi,
        subplot_kw=subplot_kw or {},
    )
    fig.patch.set_facecolor("white")
    return fig, ax


# ===========================================================================
# 迹线图
# ===========================================================================


def render_trace_plot(
    segments: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    dpi: int = _DEFAULT_TRACE_DPI,
    figsize_cm: Tuple[float, float] = _TRACE_FIGSIZE_CM,
) -> str:
    """绘制并保存单张迹线长度图。

    Args:
        segments: (N, 4) 线段数组 [x1, y1, x2, y2]。
        title: 图表标题。
        output_dir: 输出目录。
        filename: 输出文件名。
        dpi: 分辨率。
        figsize_cm: 图表尺寸（厘米）。

    Returns:
        输出文件的完整路径。
    """
    X_plot, Y_plot = segments_to_xy(segments)
    fig, ax = _new_figure(figsize_cm, dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=_TRACE_LINE_COLOR, linewidth=_TRACE_LINE_WIDTH)
    _style_trace_axes(ax)
    ax.set_title(title, fontsize=12)
    return _save_figure(fig, output_dir, filename, dpi=dpi)


# ===========================================================================
# 玫瑰花瓣图
# ===========================================================================


def render_rose_plot(
    strike_deg: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    bin_width: float = 10.0,
    dpi: int = _DEFAULT_ROSE_DPI,
    figsize_cm: Tuple[float, float] = _ROSE_FIGSIZE_CM,
) -> str:
    """绘制并保存节理走向玫瑰花瓣图。

    Returns:
        输出文件的完整路径。
    """
    theta, radii, width = _compute_rose_histogram(strike_deg, bin_width=bin_width)

    fig, ax = _new_figure(
        figsize_cm, dpi=dpi,
        subplot_kw={"projection": "polar"},
    )
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 30))
    ax.grid(
        color=_ROSE_GRID_COLOR, alpha=0.7,
        linewidth=0.8, linestyle="-",
    )

    if radii.size:
        ax.bar(
            theta, radii,
            width=width, bottom=0.0,
            color=_ROSE_BAR_COLOR, edgecolor=_ROSE_BAR_EDGE,
            linewidth=0.8, alpha=0.85, align="center",
        )
        ax.set_ylim(0, max(1, int(radii.max())))
    else:
        ax.set_ylim(0, 1)

    ax.set_title(title, fontsize=12, pad=18)
    return _save_figure(fig, output_dir, filename, dpi=dpi)


__all__ = [
    "configure_style",
    "render_rose_plot",
    "render_trace_plot",
]