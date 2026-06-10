"""节理走向玫瑰花瓣图绘制。"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from ..geology.angles import fold_strikes_to_semicircle
from ._helpers import new_figure, save_figure
from .style import apply_axis_text_fonts, configure_style, heading_font_kwargs

if TYPE_CHECKING:
    from matplotlib.projections.polar import PolarAxes

__all__ = ["render_rose_plot"]

_ROSE_FIGSIZE_CM: tuple[float, float] = (12, 12)
_DEFAULT_ROSE_DPI = 400
_ROSE_GRID_COLOR = "#d9d9d9"
_ROSE_BAR_COLOR = "#C94C4C"
_ROSE_BAR_EDGE = "#7A1F1F"


def _draw_rose_axes(
    polar_ax: PolarAxes,
    theta: np.ndarray,
    radii: np.ndarray,
    bar_widths: np.ndarray,
    *,
    bar_color: str,
    bar_edge: str,
    grid_color: str,
) -> None:
    """在极坐标轴上绘制玫瑰花瓣(柱体+网格+边框+刻度)。

    供 render_rose_plot 与 preview_plot.render_preview_rose 共享,
    消除两处约 30 行重复的极坐标绘制逻辑。
    """
    polar_ax.set_facecolor("white")
    polar_ax.set_theta_zero_location("N")
    polar_ax.set_theta_direction(-1)
    polar_ax.set_thetagrids(np.arange(0, 360, 30), fontsize=8.6)
    polar_ax.grid(color=grid_color, alpha=0.62, linewidth=0.45, linestyle="-")

    if radii.size:
        polar_ax.bar(
            theta,
            radii,
            width=bar_widths,
            bottom=0.0,
            color=bar_color,
            edgecolor=bar_edge,
            linewidth=0.45,
            alpha=0.68,
            align="center",
        )
        rmax = max(1, math.ceil(radii.max()))
        polar_ax.set_ylim(0, rmax)
        rticks = np.arange(0, rmax + 1, max(1, rmax // 5))
        polar_ax.set_rticks(rticks)
        polar_ax.set_rlabel_position(45)
        polar_ax.tick_params(axis="y", labelsize=8.0, pad=2)
    else:
        polar_ax.set_ylim(0, 1)
        polar_ax.set_rticks([0, 1])
        polar_ax.tick_params(axis="y", labelsize=8.0, pad=2)

    polar_ax.spines["polar"].set_linewidth(0.7)
    polar_ax.spines["polar"].set_color("black")
    apply_axis_text_fonts(polar_ax)
    polar_ax.set_title("")


def _compute_rose_histogram(
    strike_deg: np.ndarray,
    bin_width: float = 10.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        edges = np.insert(edges, 0, 0.0)  # type: ignore[assignment]
    if not np.isclose(edges[-1], 180.0):
        edges = np.append(edges, 180.0)  # type: ignore[assignment]

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
    figsize_cm: tuple[float, float] = _ROSE_FIGSIZE_CM,
) -> str:
    """绘制并保存节理走向玫瑰花瓣图。

    Returns:
        输出文件的完整路径。
    """
    configure_style()
    theta, radii, bar_widths = _compute_rose_histogram(strike_deg, bin_width=bin_width)

    fig, ax = new_figure(
        figsize_cm,
        dpi=dpi,
        subplot_kw={"projection": "polar"},
    )
    polar_ax: PolarAxes = ax  # type: ignore[assignment]
    _draw_rose_axes(
        polar_ax,
        theta,
        radii,
        bar_widths,
        bar_color=_ROSE_BAR_COLOR,
        bar_edge=_ROSE_BAR_EDGE,
        grid_color=_ROSE_GRID_COLOR,
    )
    fig.suptitle(title, y=0.03, **heading_font_kwargs(fontsize=10.8, fontweight="bold"))
    return save_figure(fig, output_dir, filename, dpi=dpi, pad_inches=0.08)
