"""迹线长度图绘制。"""
from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle

from ._helpers import new_figure, save_figure
from .style import configure_style, text_font_kwargs

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = ["CircleWindowOverlay", "ConvexHullOverlay", "NodeOverlay", "render_trace_plot", "segments_to_xy"]

_DEFAULT_TRACE_DPI = 300
_TARGET_SCALE_CM_PER_METER: float = 0.35
_MIN_FIGSIZE_CM: tuple[float, float] = (12.0, 8.0)
_MAX_FIGSIZE_CM: tuple[float, float] = (36.0, 25.0)
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 0.85
_ANNOTATION_LINE_WIDTH = 0.75
_ANNOTATION_ZORDER = 12
_MIN_DATA_SPAN = 1.0
_EPS = 1e-9

# ── 迹线置顶 ─────────────────────────────────────────────
_TRACE_ZORDER = 10

# ── 凸包 ─────────────────────────────────────────────────
_HULL_LINE_COLOR = "#1565C0"
_HULL_FILL_COLOR = "#1565C0"
_HULL_FILL_ALPHA = 0.08
_HULL_LINE_WIDTH = 0.8
_HULL_LINE_STYLE = "--"
_HULL_ZORDER = 2

# ── 圆窗 ─────────────────────────────────────────────────
_CIRCLE_WINDOW_LINE_COLOR = "#E65100"
_CIRCLE_WINDOW_FILL_COLOR = "#E65100"
_CIRCLE_WINDOW_FILL_ALPHA = 0.08
_CIRCLE_WINDOW_LINE_WIDTH = 0.8
_CIRCLE_WINDOW_LINE_STYLE = "--"
_CIRCLE_WINDOW_ZORDER = 2

_FRAME_AXES_BOUNDS = (0.035, 0.055, 0.93, 0.86)
_TRACE_AXES_BOUNDS = (0.065, 0.205, 0.57, 0.645)
_STATS_AXES_BOUNDS = (0.66, 0.155, 0.285, 0.61)
_COMPASS_AXES_BOUNDS = (0.76, 0.765, 0.12, 0.095)
_SCALE_AXES_BOUNDS = (0.065, 0.075, 0.57, 0.09)
_LEGEND_AXES_BOUNDS = (0.66, 0.065, 0.285, 0.075)
_MAIN_AXES_FULL = _TRACE_AXES_BOUNDS

# ── 动态布局常量 ─────────────────────────────────────────
_FRAME_BOTTOM = 0.055
_FRAME_LEFT = 0.035
_FRAME_WIDTH = 0.93
_COMPASS_W = 0.12
_COMPASS_H = 0.095
_STATS_W = 0.285
_STATS_H = 0.46
_LEGEND_W = 0.285
_LEGEND_H = 0.14
_LEGEND_BOTTOM_MARGIN = 0.010
_HARD_GAP = 0.020
_SINGLE_FRAME_TOP = 0.900
_DOUBLE_FRAME_TOP = 0.855

_UNIT_PLACEHOLDERS: tuple[tuple[str, str], ...] = (
    ("m⁻²", "__TRACE_UNIT_M2_INV__"),
    ("m−2", "__TRACE_UNIT_M2_INV__"),
    ("m^-2", "__TRACE_UNIT_M2_INV__"),
    ("m**-2", "__TRACE_UNIT_M2_INV__"),
    ("m⁻¹", "__TRACE_UNIT_M_INV__"),
    ("m−1", "__TRACE_UNIT_M_INV__"),
    ("m^-1", "__TRACE_UNIT_M_INV__"),
    ("m**-1", "__TRACE_UNIT_M_INV__"),
    ("m²", "__TRACE_UNIT_M2__"),
    ("m^2", "__TRACE_UNIT_M2__"),
    ("m**2", "__TRACE_UNIT_M2__"),
)

_UNIT_MATH_TEXT = {
    "__TRACE_UNIT_M2_INV__": r"$\mathrm{m}^{-2}$",
    "__TRACE_UNIT_M_INV__": r"$\mathrm{m}^{-1}$",
    "__TRACE_UNIT_M2__": r"$\mathrm{m}^{2}$",
    "__TRACE_UNIT_CM__": r"$\mathrm{cm}$",
    "__TRACE_UNIT_M__": r"$\mathrm{m}$",
}


@dataclass(frozen=True)
class CircleWindowOverlay:
    """绘图层使用的圆窗辅助线数据。"""

    center_x: float
    center_y: float
    radius: float


@dataclass(frozen=True)
class ConvexHullOverlay:
    """绘图层使用的凸包多边形数据。"""

    vertices: np.ndarray  # (N, 2) 按顺序的凸包顶点


@dataclass(frozen=True)
class NodeOverlay:
    """绘图层使用的节点覆盖层数据。"""

    x: float
    y: float
    node_type: str  # I/Y/X/overlap/multi
    node_id: int
    degree: int


@dataclass(frozen=True)
class TracePlotLayout:
    """迹线图布局比例参数（所有值为相对比例）。"""

    pad_data_ratio: float = 0.04
    pad_base_ratio: float = 0.08
    left_pad_ratio: float = 0.14
    bottom_pad_ratio: float = 0.16
    top_pad_ratio: float = 0.12
    tick_pad_ratio: float = 0.14
    tick_base_ratio: float = 0.022
    arrow_rel_x: float = 0.86
    arrow_rel_y: float = 0.86
    arrow_rel_len: float = 0.06
    legend_rel_x: float = 0.02
    legend_rel_y: float = 0.02
    stats_box_rel_x0: float = 0.02
    stats_box_rel_x1: float = 0.45
    stats_box_rel_y0: float = 0.48
    stats_box_rel_y1: float = 0.98
    scale_bar_y_offset_ratio: float = 0.18
    # 自动避让相关（auto_placement=True 时启用）
    auto_placement: bool = True
    placement_margin: float = 0.015
    legend_size_w: float = 0.20
    legend_size_h: float = 0.11
    stats_size_w: float = 0.43
    stats_size_h_min: float = 0.50
    stats_size_h_max: float = 0.50
    scale_size_w: float = 0.26
    scale_size_h: float = 0.07
    compass_rect: tuple[float, float, float, float] = (0.80, 0.80, 0.94, 0.94)


_DEFAULT_LAYOUT = TracePlotLayout()


def _choose_scale_length(base_span: float) -> float:
    """根据数据跨度自适应选择规整比例尺长度（1/2/5 × 10ⁿ 序列）。"""
    target = base_span / 5.0
    if target <= 0.0:
        return 1.0
    exponent = math.floor(math.log10(target))
    base = target / (10.0 ** exponent)
    if base <= 1.0:
        scale = 1.0
    elif base <= 2.0:
        scale = 2.0
    elif base <= 5.0:
        scale = 5.0
    else:
        scale = 10.0
    return scale * (10.0 ** exponent)


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


def segments_to_xy(segments: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """将 (N, 4) 线段数组转为带 NaN 分隔的一维 X/Y 序列。

    NaN 作为线段间分隔符，使 matplotlib 的 line plot 自动断开各线段。
    """
    seg_arr = np.asarray(segments, dtype=float)
    if seg_arr.ndim != 2 or seg_arr.shape[1] != 4:
        raise ValueError(f"segments 必须为 (N,4) 形状，当前 {seg_arr.shape}")
    n_segments = seg_arr.shape[0]
    if n_segments == 0:
        return np.array([]), np.array([])

    x_values = np.column_stack([seg_arr[:, 0], seg_arr[:, 2], np.full((n_segments,), np.nan)]).ravel()
    y_values = np.column_stack([seg_arr[:, 1], seg_arr[:, 3], np.full((n_segments,), np.nan)]).ravel()
    return x_values, y_values


def _valid_circles(
    circle_windows: Sequence[CircleWindowOverlay] | None,
) -> list[CircleWindowOverlay]:
    """返回几何有效的圆窗列表（有限坐标且正半径）。"""
    return [
        cw for cw in (circle_windows or ())
        if all(math.isfinite(v) for v in (cw.center_x, cw.center_y, cw.radius)) and cw.radius > 0.0
    ]


def _circle_extents(circles: list[CircleWindowOverlay]) -> tuple[np.ndarray, np.ndarray]:
    """计算所有有效圆窗的 x/y 坐标极值（圆心 ± 半径）。"""
    if not circles:
        return np.array([], dtype=float), np.array([], dtype=float)
    circle_xs = np.array(
        [x for c in circles for x in (c.center_x - c.radius, c.center_x + c.radius)],
        dtype=float,
    )
    circle_ys = np.array(
        [y for c in circles for y in (c.center_y - c.radius, c.center_y + c.radius)],
        dtype=float,
    )
    return circle_xs, circle_ys


def _data_bounds(
    segments: np.ndarray,
    circle_windows: Sequence[CircleWindowOverlay] | None = None,
    hull_overlay: ConvexHullOverlay | None = None,
    node_overlays: Sequence[NodeOverlay] | None = None,
) -> tuple[float, float, float, float]:
    circles = _valid_circles(circle_windows)
    circle_xs, circle_ys = _circle_extents(circles)
    if segments.size == 0:
        if not circles:
            return 0.0, 1.0, 0.0, 1.0
        return float(circle_xs.min()), float(circle_xs.max()), float(circle_ys.min()), float(circle_ys.max())

    seg_xs = segments[:, [0, 2]].ravel()
    seg_ys = segments[:, [1, 3]].ravel()
    if not np.isfinite(seg_xs).all() or not np.isfinite(seg_ys).all():
        raise ValueError("segments 包含 NaN 或 inf，无法绘制迹线图")

    if circles:
        seg_xs = np.concatenate([seg_xs, circle_xs])
        seg_ys = np.concatenate([seg_ys, circle_ys])

    if hull_overlay is not None and hull_overlay.vertices.size > 0:
        hull_vertices = np.asarray(hull_overlay.vertices, dtype=float)
        seg_xs = np.concatenate([seg_xs, hull_vertices[:, 0]])
        seg_ys = np.concatenate([seg_ys, hull_vertices[:, 1]])

    if node_overlays:
        node_xs = np.array([n.x for n in node_overlays], dtype=float)
        node_ys = np.array([n.y for n in node_overlays], dtype=float)
        seg_xs = np.concatenate([seg_xs, node_xs])
        seg_ys = np.concatenate([seg_ys, node_ys])

    return float(seg_xs.min()), float(seg_xs.max()), float(seg_ys.min()), float(seg_ys.max())


def _format_scale_label(length: float) -> str:
    if length >= 1.0:
        return f"{length:g} $\\mathrm{{m}}$"
    return f"{length * 100:g} $\\mathrm{{cm}}$"


def _mathtext_units(text: str) -> str:
    """将普通单位文本规范为 mathtext，保证英文单位与上标使用 Times New Roman。"""
    parts = text.split("$")
    for idx in range(0, len(parts), 2):
        segment = parts[idx]
        for source, placeholder in _UNIT_PLACEHOLDERS:
            segment = segment.replace(source, placeholder)
        segment = re.sub(r"(?<![A-Za-z\\])cm(?![A-Za-z])", "__TRACE_UNIT_CM__", segment)
        segment = re.sub(r"(?<![A-Za-z\\])m(?![A-Za-z])", "__TRACE_UNIT_M__", segment)
        for placeholder, math_text in _UNIT_MATH_TEXT.items():
            segment = segment.replace(placeholder, math_text)
        parts[idx] = segment
    return "$".join(parts)


def _build_decoration_layout(
    segments: np.ndarray,
    circle_windows: Sequence[CircleWindowOverlay] | None = None,
    hull_overlay: ConvexHullOverlay | None = None,
    node_overlays: Sequence[NodeOverlay] | None = None,
) -> _DecorationLayout:
    x_min, x_max, y_min, y_max = _data_bounds(
        segments, circle_windows=circle_windows, hull_overlay=hull_overlay, node_overlays=node_overlays
    )
    x_span = max(x_max - x_min, _MIN_DATA_SPAN)
    y_span = max(y_max - y_min, _MIN_DATA_SPAN)
    base_span = max(x_span, y_span, _MIN_DATA_SPAN)
    scale_length = _choose_scale_length(base_span)
    right_pad = max(
        x_span * _DEFAULT_LAYOUT.pad_data_ratio,
        base_span * _DEFAULT_LAYOUT.pad_data_ratio,
        max(0.0, scale_length - x_span + x_span * 0.05),
    )

    return _DecorationLayout(
        data_x_min=x_min,
        data_x_max=x_max,
        data_y_min=y_min,
        data_y_max=y_max,
        x_span=x_span,
        y_span=y_span,
        base_span=base_span,
        left_pad=max(x_span * _DEFAULT_LAYOUT.left_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio),
        right_pad=right_pad,
        bottom_pad=max(y_span * _DEFAULT_LAYOUT.bottom_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio),
        top_pad=max(y_span * _DEFAULT_LAYOUT.top_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio),
        scale_length=scale_length,
    )


def _apply_decoration_limits(ax: plt.Axes, layout: _DecorationLayout) -> None:
    ax.set_xlim(layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad)
    ax.set_ylim(layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad)


def _decoration_limits(layout: _DecorationLayout) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        (layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad),
        (layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad),
    )


def _add_scale_bar(
    ax: plt.Axes,
    layout: _DecorationLayout,
    *,
    data_x0: float | None = None,
    data_y: float | None = None,
) -> None:
    """在主图区内绘制基于真实数据坐标的比例尺。

    若未提供 ``data_x0`` / ``data_y``，则回退到原左下角硬编码位置。
    """
    x0 = layout.data_x_min + layout.base_span * 0.03 if data_x0 is None else data_x0
    x1 = x0 + layout.scale_length
    if data_y is None:
        y = layout.data_y_min + layout.base_span * _DEFAULT_LAYOUT.scale_bar_y_offset_ratio
    else:
        y = data_y
    tick = min(layout.bottom_pad * _DEFAULT_LAYOUT.tick_pad_ratio, layout.base_span * _DEFAULT_LAYOUT.tick_base_ratio)

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
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
        **text_font_kwargs(fontsize=7.2, color="black"),
    )


def _add_scale_bar_band(
    ax: plt.Axes,
    layout: _DecorationLayout,
    xlim: tuple[float, float],
) -> None:
    """在独立比例尺带中绘制与数据轴同尺度的比例尺。"""
    ax.set_xlim(*xlim)
    ax.set_ylim(0.0, 1.0)
    ax.set_axis_off()

    x_span = xlim[1] - xlim[0]
    x0 = xlim[0] + x_span * 0.04
    if x0 + layout.scale_length > xlim[1]:
        x0 = xlim[1] - layout.scale_length - x_span * 0.04
    x1 = x0 + layout.scale_length
    y = 0.62
    tick = 0.17

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
        y - tick * 0.85,
        _format_scale_label(layout.scale_length),
        ha="center",
        va="top",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
        **text_font_kwargs(fontsize=7.2, color="black"),
    )


def _add_north_arrow(
    ax: plt.Axes,
    north_angle_deg: float,
    *,
    center: tuple[float, float] | None = None,
    arrow_len: float | None = None,
) -> None:
    """在主图右上角绘制指北针（transAxes 坐标，不遮挡数据区）。"""
    if not math.isfinite(north_angle_deg):
        logger.warning("north_angle_deg 非有限值 (%s)，回退到 90.0°", north_angle_deg)
        north_angle_deg = 90.0

    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
    arrow_len = _DEFAULT_LAYOUT.arrow_rel_len if arrow_len is None else arrow_len
    label_gap = arrow_len * 0.25

    if center is None:
        center_x = _DEFAULT_LAYOUT.arrow_rel_x
        center_y = _DEFAULT_LAYOUT.arrow_rel_y
    else:
        center_x, center_y = center
    base_x = center_x - arrow_len * dx * 0.50
    base_y = center_y - arrow_len * dy * 0.50
    tip_x = center_x + arrow_len * dx * 0.50
    tip_y = center_y + arrow_len * dy * 0.50
    label_x = tip_x + label_gap * dx
    label_y = tip_y + label_gap * dy

    ax.annotate(
        "",
        xy=(tip_x, tip_y),
        xytext=(base_x, base_y),
        xycoords=ax.transAxes,
        textcoords=ax.transAxes,
        arrowprops=dict(
            arrowstyle="->",
            color="black",
            lw=0.85,
            mutation_scale=11,
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
        transform=ax.transAxes,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
        **text_font_kwargs(fontsize=9.2, fontweight="bold", color="black"),
    )


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景、完整边框。"""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    # 论文风格：完整四边框
    for spine in ax.spines.values():
        spine.set_linewidth(0.75)
        spine.set_color("black")
    ax.set_facecolor("white")


def _style_trace_data_axes(ax: plt.Axes) -> None:
    """设置外框内的数据轴，避免数据区再出现第二道边框。"""
    _style_trace_axes(ax)
    for spine in ax.spines.values():
        spine.set_visible(False)


def _resolve_layout(title: str) -> dict[str, tuple[float, float, float, float]]:
    """根据标题行数动态解析各轴在 figure 中的位置。

    单行标题外框顶边不高于 0.900；双行标题外框顶边不高于 0.875。
    统计框、图例、指北针之间保留硬间距，全部落在 frame 内部。
    """
    title_lines = title.count("\n") + 1 if title else 1
    frame_top = _DOUBLE_FRAME_TOP if title_lines >= 2 else _SINGLE_FRAME_TOP
    frame_h = frame_top - _FRAME_BOTTOM

    # 从 frame 顶边向下排布
    compass_y1 = frame_top - _LEGEND_BOTTOM_MARGIN
    compass_y0 = compass_y1 - _COMPASS_H

    stats_y1 = compass_y0 - _HARD_GAP
    stats_y0 = stats_y1 - _STATS_H

    legend_y1 = stats_y0 - _HARD_GAP
    legend_y0 = legend_y1 - _LEGEND_H

    # 指北针水平居中于右侧信息区
    info_left = _STATS_AXES_BOUNDS[0]  # 0.66
    info_right = info_left + _STATS_W  # 0.945
    compass_x0 = (info_left + info_right - _COMPASS_W) / 2.0  # ~0.7425

    # 数据轴保持原样，但确保不超出 frame
    data_bounds = _TRACE_AXES_BOUNDS
    scale_bounds = _SCALE_AXES_BOUNDS

    return {
        "trace_outer_frame": (_FRAME_LEFT, _FRAME_BOTTOM, _FRAME_WIDTH, frame_h),
        "trace_data": data_bounds,
        "trace_statistics": (info_left, stats_y0, _STATS_W, _STATS_H),
        "trace_legend": (info_left, legend_y0, _LEGEND_W, _LEGEND_H),
        "trace_compass": (compass_x0, compass_y0, _COMPASS_W, _COMPASS_H),
        "trace_scale": scale_bounds,
    }


def _add_outer_frame(fig: plt.Figure, bounds: tuple[float, float, float, float]) -> plt.Axes:
    frame_ax = fig.add_axes(bounds, label="trace_outer_frame")
    frame_ax.set_xlim(0.0, 1.0)
    frame_ax.set_ylim(0.0, 1.0)
    frame_ax.set_xticks([])
    frame_ax.set_yticks([])
    frame_ax.patch.set_alpha(0.0)
    for spine in frame_ax.spines.values():
        spine.set_linewidth(0.75)
        spine.set_color("black")
    frame_ax.set_zorder(0)
    return frame_ax


def _blank_panel_axes(fig: plt.Figure, bounds: tuple[float, float, float, float], label: str) -> plt.Axes:
    ax = fig.add_axes(bounds, label=label)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(False)
    ax.set_facecolor("none")
    return ax


def _compact_statistics_label(label: str) -> str:
    replacements = {
        "平均迹线长度": "平均迹长",
        "I/II/III型裂隙数": "I/II/III型数",
        "线密度（$P_{10}$）": "P10 线密度",
        "线密度（P10）": "P10 线密度",
        "面密度（$P_{20}$）": "P20 面密度",
        "面密度（P20）": "P20 面密度",
        "面累计长度密度（$P_{21}$）": "P21 长度密度",
        "面累计长度密度（P21）": "P21 长度密度",
        "测线走向": "测线走向",
        "测线长度": "测线长度",
        "露头面积": "露头面积",
    }
    for source, target in replacements.items():
        label = label.replace(source, target)
    return label


def _split_statistics_line(line: str) -> tuple[str, str]:
    text = str(line).strip()
    for separator in ("：", ":"):
        if separator in text:
            label, value = text.split(separator, 1)
            return _compact_statistics_label(label.strip()), _mathtext_units(value.strip())
    return _compact_statistics_label(text), ""


def _statistics_font_size(row_count: int) -> float:
    """按统计行数收缩字号，保证 PNG 面板内不发生纵向重叠。"""
    if row_count <= 8:
        return 6.8
    if row_count <= 10:
        return 5.8
    if row_count <= 12:
        return 5.5
    if row_count <= 18:
        return 5.1
    return 4.7


def _add_statistics_box(
    ax: plt.Axes,
    statistics_lines: Sequence[str] | None,
    *,
    rect: tuple[float, float, float, float] | None = None,
) -> None:
    """在主图内绘制统计信息框（transAxes 坐标，半透明背景）。

    ``rect`` 给出 (x0, y0, x1, y1) 轴坐标矩形；若为 None 则回退到原左上区硬编码位置。
    """
    if not statistics_lines:
        return
    rows = [_split_statistics_line(line) for line in statistics_lines]
    if rect is None:
        panel_x0 = _DEFAULT_LAYOUT.stats_box_rel_x0
        panel_x1 = _DEFAULT_LAYOUT.stats_box_rel_x1
        panel_y0 = _DEFAULT_LAYOUT.stats_box_rel_y0
        panel_y1 = _DEFAULT_LAYOUT.stats_box_rel_y1
    else:
        panel_x0, panel_y0, panel_x1, panel_y1 = rect
    panel_width = panel_x1 - panel_x0
    panel_height = panel_y1 - panel_y0
    # 行步长按 panel_height 与原版 0.50 的比例缩放，保持与原版一致的视觉密度
    height_scale = panel_height / 0.50
    x_label = panel_x0 + panel_width * 0.06
    x_value = panel_x1 - panel_width * 0.04
    title_y = panel_y1 - 0.045 * height_scale
    rule_y = panel_y1 - 0.080 * height_scale
    first_row_y = panel_y1 - 0.120 * height_scale
    bottom_y = panel_y0 + 0.045 * height_scale
    row_step = (first_row_y - bottom_y) / max(len(rows) - 1, 1)
    font_size = _statistics_font_size(len(rows))

    ax.add_patch(Rectangle(
        (panel_x0, panel_y0),
        panel_width,
        panel_y1 - panel_y0,
        facecolor="white",
        edgecolor="0.68",
        linewidth=0.6,
        alpha=0.94,
        transform=ax.transAxes,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER - 0.5,
    ))
    ax.text(
        x_label,
        title_y,
        "统计信息",
        ha="left",
        va="center",
        transform=ax.transAxes,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER + 1,
        **text_font_kwargs(fontsize=7.2, fontweight="bold", color="black"),
    )
    ax.plot(
        [x_label, x_value],
        [rule_y, rule_y],
        color="0.42",
        linewidth=0.6,
        transform=ax.transAxes,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
    )
    for index, (label, value) in enumerate(rows):
        y = first_row_y - row_step * index
        ax.text(
            x_label,
            y,
            label,
            ha="left",
            va="center",
            transform=ax.transAxes,
            clip_on=True,
            zorder=_ANNOTATION_ZORDER + 1,
            **text_font_kwargs(fontsize=font_size, color="0.20"),
        )
        ax.text(
            x_value,
            y,
            value,
            ha="right",
            va="center",
            transform=ax.transAxes,
            clip_on=True,
            zorder=_ANNOTATION_ZORDER + 1,
            **text_font_kwargs(fontsize=font_size, color="black"),
        )


def _add_circle_window_overlays(
    ax: plt.Axes,
    valid_circles: list[CircleWindowOverlay],
) -> None:
    for circle in valid_circles:
        patch = Circle(
            (circle.center_x, circle.center_y),
            circle.radius,
            fill=True,
            facecolor=_CIRCLE_WINDOW_FILL_COLOR,
            alpha=_CIRCLE_WINDOW_FILL_ALPHA,
            edgecolor=_CIRCLE_WINDOW_LINE_COLOR,
            linewidth=_CIRCLE_WINDOW_LINE_WIDTH,
            linestyle=_CIRCLE_WINDOW_LINE_STYLE,
            zorder=_CIRCLE_WINDOW_ZORDER,
        )
        ax.add_patch(patch)


def _add_convex_hull_overlay(ax: plt.Axes, hull_overlay: ConvexHullOverlay) -> None:
    """绘制凸包多边形（蓝色虚线框+浅蓝填充）。"""
    vertices = np.asarray(hull_overlay.vertices, dtype=float)
    if vertices.shape[0] < 3:
        return
    patch = Polygon(
        vertices,
        fill=True,
        facecolor=_HULL_FILL_COLOR,
        alpha=_HULL_FILL_ALPHA,
        edgecolor=_HULL_LINE_COLOR,
        linewidth=_HULL_LINE_WIDTH,
        linestyle=_HULL_LINE_STYLE,
        zorder=_HULL_ZORDER,
    )
    ax.add_patch(patch)


_NODE_MARKER_STYLE: dict[str, dict[str, object]] = {
    "I": {"marker": "o", "markerfacecolor": "#4CAF50", "markeredgecolor": "black", "markeredgewidth": 0.8},
    "Y": {"marker": "^", "markerfacecolor": "#F44336", "markeredgecolor": "black", "markeredgewidth": 0.8},
    "X": {"marker": "X", "markerfacecolor": "#2196F3", "markeredgecolor": "black", "markeredgewidth": 0.8},
}


def _add_node_overlays(
    ax: plt.Axes,
    node_overlays: Sequence[NodeOverlay],
    label_mode: str = "type",
) -> None:
    """在数据轴上绘制节点符号（不标注文字）。"""
    if not node_overlays or label_mode == "none":
        return
    for node in node_overlays:
        style = _NODE_MARKER_STYLE.get(node.node_type, _NODE_MARKER_STYLE["I"])
        ax.plot(
            node.x,
            node.y,
            linestyle="none",
            markersize=4,
            zorder=_TRACE_ZORDER + 2,
            **style,
        )


def _add_legend(
    ax: plt.Axes,
    area_source: str,
    has_hull: bool,
    has_circles: bool,
    has_nodes: bool = False,
    node_overlays: Sequence[NodeOverlay] | None = None,
    *,
    anchor_x: float | None = None,
    anchor_y: float | None = None,
    loc: str | None = None,
) -> None:
    """在独立信息区中绘制固定尺寸图例，避免 Matplotlib legend 自动越界。"""
    _ = (anchor_x, anchor_y, loc)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_axis_off()

    items: list[tuple[str, str]] = [("trace", "迹线")]
    if has_hull and area_source == "hull":
        items.append(("hull", "面积: 凸包"))
    elif has_hull and area_source == "hull_buffered":
        items.append(("hull", "面积: 缓冲凸包"))
    elif area_source == "measured":
        items.append(("measured", "面积: 实测"))
    elif has_circles and area_source in ("window", "window_equivalent"):
        items.append(("circle", "面积: 圆窗"))

    # 节点类型图例：只展示存在的类型
    if has_nodes and node_overlays:
        type_counts: dict[str, int] = {}
        for n in node_overlays:
            type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1
        type_labels = {
            "I": "孤立端点 (I)",
            "Y": "三叉节点 (Y)",
            "X": "交叉节点 (X)",
        }
        for key in ("I", "Y", "X"):
            if key in type_counts:
                items.append((f"node_{key}", f"{type_labels[key]} — {type_counts[key]}"))

    ax.add_patch(
        Rectangle(
            (0.02, 0.06),
            0.96,
            0.88,
            facecolor="white",
            edgecolor="0.68",
            linewidth=0.6,
            alpha=0.94,
            transform=ax.transAxes,
            clip_on=True,
            zorder=_ANNOTATION_ZORDER,
        )
    )

    n_items = len(items)
    if n_items == 1:
        y_positions = (0.50,)
    else:
        y_positions = tuple(0.88 - i * (0.76 / (n_items - 1)) for i in range(n_items))
    icon_h = 0.12
    icon_half = icon_h / 2.0
    for (kind, label), y in zip(items, y_positions, strict=False):
        if kind == "trace":
            ax.plot(
                [0.08, 0.24],
                [y, y],
                color=_TRACE_LINE_COLOR,
                linewidth=_TRACE_LINE_WIDTH,
                transform=ax.transAxes,
                clip_on=True,
                zorder=_ANNOTATION_ZORDER + 1,
            )
        elif kind == "hull":
            ax.add_patch(
                Rectangle(
                    (0.08, y - icon_half),
                    0.16,
                    icon_h,
                    facecolor=_HULL_FILL_COLOR,
                    alpha=_HULL_FILL_ALPHA,
                    edgecolor=_HULL_LINE_COLOR,
                    linewidth=_HULL_LINE_WIDTH,
                    linestyle=_HULL_LINE_STYLE,
                    transform=ax.transAxes,
                    clip_on=True,
                    zorder=_ANNOTATION_ZORDER + 1,
                )
            )
        elif kind == "circle":
            ax.add_patch(
                Rectangle(
                    (0.08, y - icon_half),
                    0.16,
                    icon_h,
                    facecolor=_CIRCLE_WINDOW_FILL_COLOR,
                    alpha=_CIRCLE_WINDOW_FILL_ALPHA,
                    edgecolor=_CIRCLE_WINDOW_LINE_COLOR,
                    linewidth=_CIRCLE_WINDOW_LINE_WIDTH,
                    linestyle=_CIRCLE_WINDOW_LINE_STYLE,
                    transform=ax.transAxes,
                    clip_on=True,
                    zorder=_ANNOTATION_ZORDER + 1,
                )
            )
        elif kind.startswith("node_"):
            node_type = kind.replace("node_", "")
            style = _NODE_MARKER_STYLE.get(node_type, _NODE_MARKER_STYLE["I"])
            ax.plot(
                0.16,
                y,
                linestyle="none",
                markersize=3.5,
                transform=ax.transAxes,
                clip_on=True,
                zorder=_ANNOTATION_ZORDER + 1,
                **style,
            )
        else:
            ax.plot(
                [0.08, 0.24],
                [y, y],
                color="0.55",
                linewidth=0.65,
                transform=ax.transAxes,
                clip_on=True,
                zorder=_ANNOTATION_ZORDER + 1,
            )
        ax.text(
            0.31,
            y,
            label,
            ha="left",
            va="center",
            transform=ax.transAxes,
            clip_on=True,
            zorder=_ANNOTATION_ZORDER + 1,
            **text_font_kwargs(fontsize=5.8, color="black"),
        )


def _compute_adaptive_figsize(layout: _DecorationLayout) -> tuple[float, float]:
    """根据数据范围自适应计算 figure 尺寸，使 1m 物理长度尽量一致。

    目标：数据跨度 50m 时 figure 短边约 25cm。
    结果裁剪到 [_MIN_FIGSIZE_CM, _MAX_FIGSIZE_CM] 区间。
    """
    target = _TARGET_SCALE_CM_PER_METER
    xlim, ylim = _decoration_limits(layout)
    x_range = max(xlim[1] - xlim[0], _MIN_DATA_SPAN)
    y_range = max(ylim[1] - ylim[0], _MIN_DATA_SPAN)
    # 数据轴物理尺寸 = 数据范围 × 目标比例尺
    # figure 尺寸 = axes 尺寸 / axes 占 figure 的比例
    fig_w = x_range * target / _TRACE_AXES_BOUNDS[2]
    fig_h = y_range * target / _TRACE_AXES_BOUNDS[3]

    min_w, min_h = _MIN_FIGSIZE_CM
    max_w, max_h = _MAX_FIGSIZE_CM

    fig_w = max(min_w, min(fig_w, max_w))
    fig_h = max(min_h, min(fig_h, max_h))
    return (fig_w, fig_h)


def render_trace_plot(
    segments: np.ndarray,
    title: str,
    output_dir: str,
    filename: str,
    dpi: int = _DEFAULT_TRACE_DPI,
    figsize_cm: tuple[float, float] | None = None,
    north_angle_deg: float = 90.0,
    statistics_lines: Sequence[str] | None = None,
    circle_windows: Sequence[CircleWindowOverlay] | None = None,
    hull_overlay: ConvexHullOverlay | None = None,
    area_source: str = "",
    node_overlays: Sequence[NodeOverlay] | None = None,
    node_label_mode: str = "type",
    *,
    include_trace: bool = True,
    include_hull: bool = True,
    include_circles: bool = True,
    include_nodes: bool = True,
    include_decorations: bool = True,
    background_color: str = "white",
) -> str:
    """绘制并保存单张迹线长度图。

    ``figsize_cm`` 为 ``None`` 时，figure 尺寸会根据数据范围自适应，
    确保不同图之间 1m 的物理长度尽量一致，面积具有可比性。

    新增图层控制参数（``include_*``）与背景透明支持，便于生成
    可叠加的独立视觉层 PNG。

    Returns:
        输出文件的完整路径。
    """
    configure_style()
    arr = np.asarray(segments, dtype=float)
    valid_circles = _valid_circles(circle_windows)
    x_plot, y_plot = segments_to_xy(arr)
    selected_hull = (
        hull_overlay
        if area_source in {"hull", "hull_buffered"}
        and hull_overlay is not None
        and hull_overlay.vertices.size > 0
        else None
    )
    selected_circles = valid_circles if area_source in {"window", "window_equivalent"} else []
    has_hull = selected_hull is not None
    has_circles = bool(selected_circles)
    has_nodes = bool(node_overlays)
    layout = _build_decoration_layout(
        arr,
        circle_windows=selected_circles,
        hull_overlay=selected_hull,
        node_overlays=node_overlays,
    )
    effective_figsize = figsize_cm if figsize_cm is not None else _compute_adaptive_figsize(layout)
    fig, ax = new_figure(effective_figsize, dpi=dpi)
    ax.remove()

    # 背景透明支持
    if background_color.lower() in ("none", "transparent"):
        fig.patch.set_alpha(0.0)
    else:
        fig.patch.set_facecolor(background_color)

    layout_bounds = _resolve_layout(title)

    if include_decorations:
        _add_outer_frame(fig, layout_bounds["trace_outer_frame"])

    ax = fig.add_axes(layout_bounds["trace_data"], label="trace_data")

    # 1. 底层：凸包或圆窗（二选一）
    if include_hull and selected_hull is not None:
        _add_convex_hull_overlay(ax, selected_hull)
    elif include_circles and has_circles:
        _add_circle_window_overlays(ax, selected_circles)

    # 2. 顶层：迹线
    if include_trace:
        ax.plot(
            x_plot, y_plot, "-",
            color=_TRACE_LINE_COLOR,
            linewidth=_TRACE_LINE_WIDTH,
            zorder=_TRACE_ZORDER,
        )

    # 2.5 节点覆盖层
    if include_nodes and node_overlays:
        _add_node_overlays(ax, node_overlays, label_mode=node_label_mode)

    _style_trace_data_axes(ax)
    _apply_decoration_limits(ax, layout)

    if include_decorations:
        # 3. 装饰元素放入同一外框内的独立信息区，不再覆盖数据轴。
        xlim, _ylim = _decoration_limits(layout)
        compass_ax = _blank_panel_axes(fig, layout_bounds["trace_compass"], "trace_compass")
        _add_north_arrow(compass_ax, north_angle_deg, center=(0.50, 0.46), arrow_len=0.38)

        scale_ax = _blank_panel_axes(fig, layout_bounds["trace_scale"], "trace_scale")
        _add_scale_bar_band(scale_ax, layout, xlim)

        legend_ax = _blank_panel_axes(fig, layout_bounds["trace_legend"], "trace_legend")
        _add_legend(
            legend_ax,
            area_source,
            has_hull,
            has_circles,
            has_nodes=has_nodes,
            node_overlays=node_overlays,
            anchor_x=0.02,
            anchor_y=0.50,
            loc="center left",
        )

        stats_ax = _blank_panel_axes(fig, layout_bounds["trace_statistics"], "trace_statistics")
        _add_statistics_box(stats_ax, statistics_lines, rect=(0.02, 0.02, 0.98, 0.98))

        fig.suptitle(title, y=0.965, **text_font_kwargs(fontsize=10.4, fontweight="bold"))

    return save_figure(fig, output_dir, filename, dpi=dpi, pad_inches=0.0, bbox_inches=None)
