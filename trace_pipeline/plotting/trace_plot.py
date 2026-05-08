"""迹线长度图绘制。"""
from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from ._helpers import new_figure, save_figure

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = ["render_trace_plot", "segments_to_xy"]

_TRACE_FIGSIZE_CM: tuple[float, float] = (20, 14)
_DEFAULT_TRACE_DPI = 300
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 1.0
_ANNOTATION_LINE_WIDTH = 1.0
_ANNOTATION_ZORDER = 5
_MIN_DATA_SPAN = 1.0


@dataclass(frozen=True)
class TracePlotLayout:
    """迹线图布局比例参数（所有值为相对比例）。"""

    pad_data_ratio: float = 0.04
    pad_base_ratio: float = 0.08
    left_pad_ratio: float = 0.14
    bottom_pad_ratio: float = 0.16
    top_pad_ratio: float = 0.12
    panel_x_ratio: float = 0.68
    panel_base_ratio: float = 0.54
    panel_scale_multiplier: float = 2.0
    panel_inset_ratio: float = 0.08
    panel_bottom_ratio: float = 0.06
    panel_top_ratio: float = 0.04
    scale_bar_y_ratio: float = 0.76
    scale_bar_bottom_ratio: float = 0.42
    tick_pad_ratio: float = 0.14
    tick_base_ratio: float = 0.022
    arrow_max_width_ratio: float = 0.38
    arrow_max_height_ratio: float = 0.13
    arrow_base_ratio: float = 0.11
    arrow_y_center_ratio: float = 0.91
    arrow_y_low_ratio: float = 0.82
    arrow_y_high_ratio: float = 0.98
    stats_text_x_inset: float = 0.04
    stats_text_y_inset: float = 0.04
    fixed_scale_length: float = 5.0


_DEFAULT_LAYOUT = TracePlotLayout()

# 模块级别名（向后兼容内部引用）
_PAD_DATA_RATIO = _DEFAULT_LAYOUT.pad_data_ratio
_PAD_BASE_RATIO = _DEFAULT_LAYOUT.pad_base_ratio
_LEFT_PAD_RATIO = _DEFAULT_LAYOUT.left_pad_ratio
_BOTTOM_PAD_RATIO = _DEFAULT_LAYOUT.bottom_pad_ratio
_TOP_PAD_RATIO = _DEFAULT_LAYOUT.top_pad_ratio
_PANEL_X_RATIO = _DEFAULT_LAYOUT.panel_x_ratio
_PANEL_BASE_RATIO = _DEFAULT_LAYOUT.panel_base_ratio
_PANEL_SCALE_MULTIPLIER = _DEFAULT_LAYOUT.panel_scale_multiplier
_PANEL_INSET_RATIO = _DEFAULT_LAYOUT.panel_inset_ratio
_PANEL_BOTTOM_RATIO = _DEFAULT_LAYOUT.panel_bottom_ratio
_PANEL_TOP_RATIO = _DEFAULT_LAYOUT.panel_top_ratio
_SCALE_BAR_Y_RATIO = _DEFAULT_LAYOUT.scale_bar_y_ratio
_SCALE_BAR_BOTTOM_RATIO = _DEFAULT_LAYOUT.scale_bar_bottom_ratio
_TICK_PAD_RATIO = _DEFAULT_LAYOUT.tick_pad_ratio
_TICK_BASE_RATIO = _DEFAULT_LAYOUT.tick_base_ratio
_ARROW_MAX_WIDTH_RATIO = _DEFAULT_LAYOUT.arrow_max_width_ratio
_ARROW_MAX_HEIGHT_RATIO = _DEFAULT_LAYOUT.arrow_max_height_ratio
_ARROW_BASE_RATIO = _DEFAULT_LAYOUT.arrow_base_ratio
_ARROW_Y_CENTER_RATIO = _DEFAULT_LAYOUT.arrow_y_center_ratio
_ARROW_Y_LOW_RATIO = _DEFAULT_LAYOUT.arrow_y_low_ratio
_ARROW_Y_HIGH_RATIO = _DEFAULT_LAYOUT.arrow_y_high_ratio
_STATS_TEXT_X_INSET = _DEFAULT_LAYOUT.stats_text_x_inset
_STATS_TEXT_Y_INSET = _DEFAULT_LAYOUT.stats_text_y_inset
_FIXED_SCALE_LENGTH = _DEFAULT_LAYOUT.fixed_scale_length


def _auto_scale_length(data_span: float) -> float:
    """固定比例尺长度为 5m（与论文一致）。"""
    return _FIXED_SCALE_LENGTH


class _DecorationLayout(NamedTuple):
    data_x_min: float
    data_x_max: float
    data_y_min: float
    data_y_max: float
    x_span: float
    y_span: float
    base_span: float
    left_pad: float
    right_pad: float
    bottom_pad: float
    top_pad: float
    scale_length: float
    has_annotation_panel: bool


def segments_to_xy(segments: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """将 (N, 4) 线段数组转为带 NaN 分隔的一维 X/Y 序列。

    NaN 作为线段间分隔符，使 matplotlib 的 line plot 自动断开各线段。
    """
    arr = np.asarray(segments, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"segments 必须为 (N,4) 形状，当前 {arr.shape}")
    n = arr.shape[0]
    if n == 0:
        return np.array([]), np.array([])

    X = np.column_stack([arr[:, 0], arr[:, 2], np.full((n,), np.nan)]).ravel()
    Y = np.column_stack([arr[:, 1], arr[:, 3], np.full((n,), np.nan)]).ravel()
    return X, Y


def _data_bounds(segments: np.ndarray) -> tuple[float, float, float, float]:
    if segments.size == 0:
        return 0.0, 1.0, 0.0, 1.0

    xs = segments[:, [0, 2]].ravel()
    ys = segments[:, [1, 3]].ravel()
    if not np.isfinite(xs).all() or not np.isfinite(ys).all():
        raise ValueError("segments 包含 NaN 或 inf，无法绘制迹线图")

    return float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())


def _format_scale_label(length: float) -> str:
    if length >= 1.0:
        return f"{length:g} m"
    return f"{length * 100:g} cm"


def _build_decoration_layout(
    segments: np.ndarray,
    has_annotation_panel: bool = False,
) -> _DecorationLayout:
    x_min, x_max, y_min, y_max = _data_bounds(segments)
    x_span = max(x_max - x_min, _MIN_DATA_SPAN)
    y_span = max(y_max - y_min, _MIN_DATA_SPAN)
    base_span = max(x_span, y_span, _MIN_DATA_SPAN)
    scale_length = _auto_scale_length(base_span)
    right_pad = max(
        x_span * _PAD_DATA_RATIO,
        base_span * _PAD_DATA_RATIO,
        max(0.0, scale_length - x_span + x_span * 0.05),
    )
    if has_annotation_panel:
        right_pad = max(x_span * _PANEL_X_RATIO, base_span * _PANEL_BASE_RATIO, scale_length * _PANEL_SCALE_MULTIPLIER)

    return _DecorationLayout(
        data_x_min=x_min,
        data_x_max=x_max,
        data_y_min=y_min,
        data_y_max=y_max,
        x_span=x_span,
        y_span=y_span,
        base_span=base_span,
        left_pad=max(x_span * _LEFT_PAD_RATIO, base_span * _PAD_BASE_RATIO),
        right_pad=right_pad,
        bottom_pad=max(y_span * _BOTTOM_PAD_RATIO, base_span * _PAD_BASE_RATIO),
        top_pad=max(y_span * _TOP_PAD_RATIO, base_span * _PAD_BASE_RATIO),
        scale_length=scale_length,
        has_annotation_panel=has_annotation_panel,
    )


def _apply_decoration_limits(ax: plt.Axes, layout: _DecorationLayout) -> None:
    ax.set_xlim(layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad)
    ax.set_ylim(layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad)


def _add_scale_bar(ax: plt.Axes, layout: _DecorationLayout, is_panel: bool = False) -> None:
    if is_panel:
        panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
        panel_width = panel_x1 - panel_x0
        scale_length = layout.scale_length
        x0 = panel_x0 + (panel_width - scale_length) / 2.0
        x1 = x0 + scale_length
        y = panel_y0 + (panel_y1 - panel_y0) * _SCALE_BAR_Y_RATIO
    else:
        x0 = layout.data_x_min + max(layout.x_span * 0.03, layout.base_span * 0.01)
        x1 = x0 + layout.scale_length
        y = layout.data_y_min - layout.bottom_pad * _SCALE_BAR_BOTTOM_RATIO

    tick = min(layout.bottom_pad * _TICK_PAD_RATIO, layout.base_span * _TICK_BASE_RATIO)

    ax.plot(
        [x0, x1],
        [y, y],
        color="black",
        linewidth=_ANNOTATION_LINE_WIDTH,
        solid_capstyle="butt",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )
    ax.plot(
        [x0, x0],
        [y - tick, y + tick],
        color="black",
        linewidth=_ANNOTATION_LINE_WIDTH,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )
    ax.plot(
        [x1, x1],
        [y - tick, y + tick],
        color="black",
        linewidth=_ANNOTATION_LINE_WIDTH,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )
    ax.text(
        (x0 + x1) / 2.0,
        y - tick * 1.45,
        _format_scale_label(layout.scale_length),
        ha="center",
        va="top",
        fontsize=10,
        color="black",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )


def _axis_bounds(layout: _DecorationLayout) -> tuple[float, float, float, float]:
    return (
        layout.data_x_min - layout.left_pad,
        layout.data_x_max + layout.right_pad,
        layout.data_y_min - layout.bottom_pad,
        layout.data_y_max + layout.top_pad,
    )


def _panel_bounds(layout: _DecorationLayout) -> tuple[float, float, float, float]:
    x_low, x_high, y_low, y_high = _axis_bounds(layout)
    return (
        layout.data_x_max + layout.right_pad * _PANEL_INSET_RATIO,
        x_high - layout.right_pad * _PANEL_INSET_RATIO,
        y_low + (y_high - y_low) * _PANEL_BOTTOM_RATIO,
        y_high - (y_high - y_low) * _PANEL_TOP_RATIO,
    )


def _shift_into_bounds(
    xs: Sequence[float],
    ys: Sequence[float],
    x_low: float,
    x_high: float,
    y_low: float,
    y_high: float,
) -> tuple[float, float]:
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    shift_x = max(0.0, x_low - min_x) - max(0.0, max_x - x_high)
    shift_y = max(0.0, y_low - min_y) - max(0.0, max_y - y_high)
    return shift_x, shift_y


def _add_north_arrow(
    ax: plt.Axes,
    layout: _DecorationLayout,
    north_angle_deg: float,
    is_panel: bool = False,
) -> None:
    if not math.isfinite(north_angle_deg):
        logger.warning("north_angle_deg 非有限值 (%s)，回退到 90.0°", north_angle_deg)
        north_angle_deg = 90.0

    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)

    if is_panel:
        panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
        arrow_len = min(
            (panel_x1 - panel_x0) * _ARROW_MAX_WIDTH_RATIO,
            (panel_y1 - panel_y0) * _ARROW_MAX_HEIGHT_RATIO,
            layout.base_span * _ARROW_BASE_RATIO,
        )
        label_gap = arrow_len * 0.25
        center_x = (panel_x0 + panel_x1) / 2.0
        center_y = panel_y0 + (panel_y1 - panel_y0) * _ARROW_Y_CENTER_RATIO

        base_x = center_x - arrow_len * dx * 0.50
        base_y = center_y - arrow_len * dy * 0.50
        tip_x = center_x + arrow_len * dx * 0.50
        tip_y = center_y + arrow_len * dy * 0.50
        label_x = tip_x + label_gap * dx
        label_y = tip_y + label_gap * dy

        shift_x, shift_y = _shift_into_bounds(
            [base_x, tip_x, label_x],
            [base_y, tip_y, label_y],
            panel_x0,
            panel_x1,
            panel_y0 + (panel_y1 - panel_y0) * _ARROW_Y_LOW_RATIO,
            panel_y0 + (panel_y1 - panel_y0) * _ARROW_Y_HIGH_RATIO,
        )
        base_x += shift_x
        tip_x += shift_x
        label_x += shift_x
        base_y += shift_y
        tip_y += shift_y
        label_y += shift_y
    else:
        arrow_len = min(layout.left_pad * 0.50, layout.top_pad * 0.50, layout.base_span * 0.09)
        label_gap = arrow_len * 0.25

        base_x = layout.data_x_min - layout.left_pad * 0.52
        base_y = layout.data_y_max + layout.top_pad * 0.32
        tip_x = base_x + arrow_len * dx
        tip_y = base_y + arrow_len * dy
        label_x = tip_x + label_gap * dx
        label_y = tip_y + label_gap * dy

        x_low = layout.data_x_min - layout.left_pad
        x_high = layout.data_x_max + layout.right_pad
        y_low = layout.data_y_min - layout.bottom_pad
        y_high = layout.data_y_max + layout.top_pad
        inset = layout.base_span * 0.05

        min_x = min(base_x, tip_x, label_x)
        max_x = max(base_x, tip_x, label_x)
        min_y = min(base_y, tip_y, label_y)
        max_y = max(base_y, tip_y, label_y)
        shift_x = max(0.0, x_low + inset - min_x) - max(0.0, max_x - (x_high - inset))
        shift_y = max(0.0, y_low + inset - min_y) - max(0.0, max_y - (y_high - inset))

        base_x += shift_x
        tip_x += shift_x
        label_x += shift_x
        base_y += shift_y
        tip_y += shift_y
        label_y += shift_y

    ax.annotate(
        "",
        xy=(tip_x, tip_y),
        xytext=(base_x, base_y),
        arrowprops=dict(
            arrowstyle="->",
            color="black",
            lw=1.2,
            mutation_scale=14,
        ),
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )
    ax.text(
        label_x,
        label_y,
        "N",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="black",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景、完整边框。"""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    # 论文风格：完整四边框
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("black")
    ax.set_facecolor("white")


def _add_statistics_box(
    ax: plt.Axes,
    layout: _DecorationLayout,
    statistics_lines: Sequence[str] | None,
) -> None:
    if not statistics_lines:
        return
    panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
    panel_width = panel_x1 - panel_x0
    panel_height = panel_y1 - panel_y0
    ax.text(
        panel_x1 - panel_width * _STATS_TEXT_X_INSET,
        panel_y0 + panel_height * _STATS_TEXT_Y_INSET,
        "\n".join(str(line) for line in statistics_lines),
        ha="right",
        va="bottom",
        fontsize=8.0,
        linespacing=1.18,
        color="black",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER + 1,
    )


def render_trace_plot(
    segments: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    dpi: int = _DEFAULT_TRACE_DPI,
    figsize_cm: tuple[float, float] = _TRACE_FIGSIZE_CM,
    north_angle_deg: float = 90.0,
    statistics_lines: Sequence[str] | None = None,
) -> str:
    """绘制并保存单张迹线长度图。

    Returns:
        输出文件的完整路径。
    """
    arr = np.asarray(segments, dtype=float)
    X_plot, Y_plot = segments_to_xy(arr)
    has_annotation_panel = bool(statistics_lines)
    layout = _build_decoration_layout(arr, has_annotation_panel=has_annotation_panel)
    fig, ax = new_figure(figsize_cm, dpi=dpi)
    ax.plot(X_plot, Y_plot, "-", color=_TRACE_LINE_COLOR, linewidth=_TRACE_LINE_WIDTH)
    _style_trace_axes(ax)
    _apply_decoration_limits(ax, layout)
    if has_annotation_panel:
        _add_statistics_box(ax, layout, statistics_lines)
        _add_north_arrow(ax, layout, north_angle_deg, is_panel=True)
        _add_scale_bar(ax, layout, is_panel=True)
    else:
        _add_north_arrow(ax, layout, north_angle_deg, is_panel=False)
        _add_scale_bar(ax, layout, is_panel=False)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    return save_figure(fig, output_dir, filename, dpi=dpi)
