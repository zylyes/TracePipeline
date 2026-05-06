"""迹线长度图绘制。"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, NamedTuple, Sequence, Tuple

from ._helpers import new_figure, save_figure

import numpy as np

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = ["render_trace_plot", "segments_to_xy"]

_TRACE_FIGSIZE_CM: Tuple[float, float] = (20, 14)
_DEFAULT_TRACE_DPI = 300
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 1.0
_ANNOTATION_LINE_WIDTH = 1.0
_ANNOTATION_ZORDER = 5
_MIN_DATA_SPAN = 1.0
_FIXED_SCALE_LENGTH = 5.0


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


def segments_to_xy(segments: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
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


def _data_bounds(segments: np.ndarray) -> Tuple[float, float, float, float]:
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
    scale_length = _FIXED_SCALE_LENGTH
    right_pad = max(
        x_span * 0.04,
        base_span * 0.04,
        max(0.0, scale_length - x_span + x_span * 0.05),
    )
    if has_annotation_panel:
        right_pad = max(x_span * 0.68, base_span * 0.54, scale_length * 2.00)

    return _DecorationLayout(
        data_x_min=x_min,
        data_x_max=x_max,
        data_y_min=y_min,
        data_y_max=y_max,
        x_span=x_span,
        y_span=y_span,
        base_span=base_span,
        left_pad=max(x_span * 0.14, base_span * 0.08),
        right_pad=right_pad,
        bottom_pad=max(y_span * 0.16, base_span * 0.08),
        top_pad=max(y_span * 0.12, base_span * 0.08),
        scale_length=scale_length,
        has_annotation_panel=has_annotation_panel,
    )


def _apply_decoration_limits(ax: plt.Axes, layout: _DecorationLayout) -> None:
    ax.set_xlim(layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad)
    ax.set_ylim(layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad)


def _add_scale_bar(ax: plt.Axes, layout: _DecorationLayout) -> None:
    x0 = layout.data_x_min + max(layout.x_span * 0.03, layout.base_span * 0.01)
    x1 = x0 + layout.scale_length
    y = layout.data_y_min - layout.bottom_pad * 0.42
    tick = min(layout.bottom_pad * 0.14, layout.base_span * 0.022)

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


def _axis_bounds(layout: _DecorationLayout) -> Tuple[float, float, float, float]:
    return (
        layout.data_x_min - layout.left_pad,
        layout.data_x_max + layout.right_pad,
        layout.data_y_min - layout.bottom_pad,
        layout.data_y_max + layout.top_pad,
    )


def _panel_bounds(layout: _DecorationLayout) -> Tuple[float, float, float, float]:
    x_low, x_high, y_low, y_high = _axis_bounds(layout)
    return (
        layout.data_x_max + layout.right_pad * 0.08,
        x_high - layout.right_pad * 0.08,
        y_low + (y_high - y_low) * 0.06,
        y_high - (y_high - y_low) * 0.04,
    )


def _shift_into_bounds(
    xs: Sequence[float],
    ys: Sequence[float],
    x_low: float,
    x_high: float,
    y_low: float,
    y_high: float,
) -> Tuple[float, float]:
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    shift_x = max(0.0, x_low - min_x) - max(0.0, max_x - x_high)
    shift_y = max(0.0, y_low - min_y) - max(0.0, max_y - y_high)
    return shift_x, shift_y


def _add_panel_scale_bar(ax: plt.Axes, layout: _DecorationLayout) -> None:
    panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
    panel_width = panel_x1 - panel_x0
    scale_length = layout.scale_length
    x0 = panel_x0 + (panel_width - scale_length) / 2.0
    x1 = x0 + scale_length
    y = panel_y0 + (panel_y1 - panel_y0) * 0.76
    tick = min(layout.bottom_pad * 0.14, layout.base_span * 0.022)

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
        _format_scale_label(scale_length),
        ha="center",
        va="top",
        fontsize=10,
        color="black",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )


def _add_direction_marker(
    ax: plt.Axes,
    layout: _DecorationLayout,
    north_angle_deg: float,
) -> None:
    if not math.isfinite(north_angle_deg):
        north_angle_deg = 90.0

    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
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

    # 绘制更精致的指北针
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


def _add_panel_direction_marker(
    ax: plt.Axes,
    layout: _DecorationLayout,
    north_angle_deg: float,
) -> None:
    if not math.isfinite(north_angle_deg):
        north_angle_deg = 90.0

    panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
    arrow_len = min(
        (panel_x1 - panel_x0) * 0.38,
        (panel_y1 - panel_y0) * 0.13,
        layout.base_span * 0.11,
    )
    label_gap = arrow_len * 0.25
    center_x = (panel_x0 + panel_x1) / 2.0
    center_y = panel_y0 + (panel_y1 - panel_y0) * 0.91

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
        panel_y0 + (panel_y1 - panel_y0) * 0.82,
        panel_y0 + (panel_y1 - panel_y0) * 0.98,
    )
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
        panel_x1 - panel_width * 0.04,
        panel_y0 + panel_height * 0.04,
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
    figsize_cm: Tuple[float, float] = _TRACE_FIGSIZE_CM,
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
        _add_panel_direction_marker(ax, layout, north_angle_deg)
        _add_panel_scale_bar(ax, layout)
    else:
        _add_direction_marker(ax, layout, north_angle_deg)
        _add_scale_bar(ax, layout)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    return save_figure(fig, output_dir, filename, dpi=dpi)
