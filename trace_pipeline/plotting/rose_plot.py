"""节理走向玫瑰花瓣图绘制。"""
from __future__ import annotations

from typing import Tuple

import numpy as np

from ..geology.angles import fold_strikes_to_semicircle
from ._helpers import new_figure, save_figure

__all__ = ["render_rose_plot"]

_ROSE_FIGSIZE_CM: Tuple[float, float] = (14, 14)
_DEFAULT_ROSE_DPI = 400
_ROSE_GRID_COLOR = "#d0d0d0"
_ROSE_BAR_COLOR = "#DC2626"
_ROSE_BAR_EDGE = "#991B1B"


def _compute_rose_histogram(
    strike_deg: np.ndarray,
    bin_width: float = 10.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """计算玫瑰图柱体的角度（弧度）、频数与柱宽（弧度）。"""
    if not (0 < bin_width <= 180):
        raise ValueError("rose bin_width 必须在 (0, 180] 范围内")

    folded = fold_strikes_to_semicircle(strike_deg)
    if not np.isfinite(folded).all():
        raise ValueError("strike_deg 包含 NaN 或 inf，无法绘制玫瑰图")
    if folded.size == 0:
        return np.array([]), np.array([]), np.array([])

    edges = np.arange(0.0, 180.0, bin_width, dtype=float)
    if edges.size == 0 or not np.isclose(edges[0], 0.0):
        edges = np.insert(edges, 0, 0.0)
    if not np.isclose(edges[-1], 180.0):
        edges = np.append(edges, 180.0)

    counts, _ = np.histogram(folded, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2.0
    widths = np.deg2rad(np.diff(edges))

    theta = np.deg2rad(np.concatenate([centers, centers + 180.0]))
    radii = np.concatenate([counts, counts])
    bar_widths = np.concatenate([widths, widths])
    return theta, radii, bar_widths


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

    fig, ax = new_figure(
        figsize_cm, dpi=dpi,
        subplot_kw={"projection": "polar"},
    )
    ax.set_facecolor("white")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    # 外圈角度标签：每 30° 一格，字号适中
    ax.set_thetagrids(np.arange(0, 360, 30), fontsize=10)

    # 径向网格线与标签
    ax.grid(
        color=_ROSE_GRID_COLOR, alpha=0.6,
        linewidth=0.6, linestyle="-",
    )

    if radii.size:
        ax.bar(
            theta, radii,
            width=width, bottom=0.0,
            color=_ROSE_BAR_COLOR, edgecolor=_ROSE_BAR_EDGE,
            linewidth=0.6, alpha=0.75, align="center",
        )
        rmax = max(1, int(radii.max()))
        ax.set_ylim(0, rmax)
        # 设置径向刻度标签
        rticks = np.arange(0, rmax + 1, max(1, rmax // 5))
        ax.set_rticks(rticks)
        ax.set_rlabel_position(45)
        ax.tick_params(axis="y", labelsize=9)
    else:
        ax.set_ylim(0, 1)
        ax.set_rticks([0, 1])

    # 极坐标外圈边框
    ax.spines["polar"].set_linewidth(0.8)
    ax.spines["polar"].set_color("black")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    return save_figure(fig, output_dir, filename, dpi=dpi)
