"""迹线长度图绘制。"""
from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle

from ._decoration_layout import resolve_decoration_positions
from ._helpers import new_figure, save_figure
from .style import configure_style, text_font_kwargs

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = ["CircleWindowOverlay", "ConvexHullOverlay", "render_trace_plot", "segments_to_xy"]

_DEFAULT_TRACE_DPI = 300
_TARGET_SCALE_CM_PER_METER: float = 0.35
_MIN_FIGSIZE_CM: tuple[float, float] = (12.0, 8.0)
_MAX_FIGSIZE_CM: tuple[float, float] = (30.0, 25.0)
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 1.2
_ANNOTATION_LINE_WIDTH = 1.0
_ANNOTATION_ZORDER = 12
_MIN_DATA_SPAN = 1.0
_EPS = 1e-9

# ── 迹线置顶 ─────────────────────────────────────────────
_TRACE_ZORDER = 10

# ── 凸包 ─────────────────────────────────────────────────
_HULL_LINE_COLOR = "#1565C0"
_HULL_FILL_COLOR = "#1565C0"
_HULL_FILL_ALPHA = 0.12
_HULL_LINE_WIDTH = 1.2
_HULL_LINE_STYLE = "--"
_HULL_ZORDER = 2

# ── 圆窗 ─────────────────────────────────────────────────
_CIRCLE_WINDOW_LINE_COLOR = "#E65100"
_CIRCLE_WINDOW_FILL_COLOR = "#E65100"
_CIRCLE_WINDOW_FILL_ALPHA = 0.12
_CIRCLE_WINDOW_LINE_WIDTH = 1.2
_CIRCLE_WINDOW_LINE_STYLE = "--"
_CIRCLE_WINDOW_ZORDER = 2

_MAIN_AXES_FULL = (0.075, 0.10, 0.85, 0.78)


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

    return float(seg_xs.min()), float(seg_xs.max()), float(seg_ys.min()), float(seg_ys.max())


def _format_scale_label(length: float) -> str:
    if length >= 1.0:
        return f"{length:g} m"
    return f"{length * 100:g} cm"


def _build_decoration_layout(
    segments: np.ndarray,
    circle_windows: Sequence[CircleWindowOverlay] | None = None,
    hull_overlay: ConvexHullOverlay | None = None,
) -> _DecorationLayout:
    x_min, x_max, y_min, y_max = _data_bounds(
        segments, circle_windows=circle_windows, hull_overlay=hull_overlay
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
    if data_x0 is None:
        x0 = layout.data_x_min + layout.base_span * 0.03
    else:
        x0 = data_x0
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
        **text_font_kwargs(fontsize=9, color="black"),
    )


def _add_north_arrow(ax: plt.Axes, north_angle_deg: float) -> None:
    """在主图右上角绘制指北针（transAxes 坐标，不遮挡数据区）。"""
    if not math.isfinite(north_angle_deg):
        logger.warning("north_angle_deg 非有限值 (%s)，回退到 90.0°", north_angle_deg)
        north_angle_deg = 90.0

    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
    arrow_len = _DEFAULT_LAYOUT.arrow_rel_len
    label_gap = arrow_len * 0.25

    center_x = _DEFAULT_LAYOUT.arrow_rel_x
    center_y = _DEFAULT_LAYOUT.arrow_rel_y
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
        transform=ax.transAxes,
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
        **text_font_kwargs(fontsize=11, fontweight="bold", color="black"),
    )


def _style_trace_axes(ax: plt.Axes) -> None:
    """设置迹线图坐标轴：等比例、无刻度、白色背景、完整边框。"""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    # 论文风格：完整四边框
    for spine in ax.spines.values():
        spine.set_linewidth(1.0)
        spine.set_color("black")
    ax.set_facecolor("white")


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
            return _compact_statistics_label(label.strip()), value.strip()
    return text, ""


def _statistics_font_size(row_count: int) -> float:
    """按统计行数收缩字号，保证 PNG 面板内不发生纵向重叠。"""
    if row_count <= 8:
        return 7.6
    if row_count <= 10:
        return 7.0
    if row_count <= 12:
        return 6.3
    return 5.8


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
        edgecolor="0.72",
        linewidth=0.8,
        alpha=0.92,
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
        **text_font_kwargs(fontsize=8.3, fontweight="bold", color="black"),
    )
    ax.plot(
        [x_label, x_value],
        [rule_y, rule_y],
        color="0.35",
        linewidth=0.8,
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
            **text_font_kwargs(fontsize=font_size, color="0.18"),
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


def _add_legend(
    ax: plt.Axes,
    area_source: str,
    has_hull: bool,
    has_circles: bool,
    *,
    anchor_x: float | None = None,
    anchor_y: float | None = None,
    loc: str | None = None,
) -> None:
    """在主图内绘制动态图例（transAxes 坐标，不占用数据区）。

    若未提供 ``anchor_x`` / ``anchor_y`` / ``loc``，则回退到原左下角硬编码位置。
    """
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D

    if anchor_x is None:
        anchor_x = _DEFAULT_LAYOUT.legend_rel_x
    if anchor_y is None:
        anchor_y = _DEFAULT_LAYOUT.legend_rel_y
    if loc is None:
        loc = "lower left"

    handles: list[object] = []
    # 迹线（始终显示）
    handles.append(
        Line2D([0], [0], color=_TRACE_LINE_COLOR, linewidth=_TRACE_LINE_WIDTH, label="迹线")
    )
    # 凸包/圆窗（二选一），标签与统计框来源一致
    if has_hull and area_source == "hull":
        label = "露头面积（凸包）"
    elif has_hull and area_source == "hull_buffered":
        label = "露头面积（缓冲凸包）"
    elif area_source == "measured":
        label = "实测面积（表格来源）"
    elif has_circles and area_source in ("window", "window_equivalent"):
        label = "露头面积（圆窗等效）"
    else:
        label = ""

    if label:
        if has_hull and area_source in ("hull", "hull_buffered", "measured"):
            handles.append(
                mpatches.Patch(
                    facecolor=_HULL_FILL_COLOR,
                    alpha=_HULL_FILL_ALPHA,
                    edgecolor=_HULL_LINE_COLOR,
                    linewidth=_HULL_LINE_WIDTH,
                    linestyle=_HULL_LINE_STYLE,
                    label=label,
                )
            )
        elif area_source == "measured":
            handles.append(
                Line2D(
                    [0],
                    [0],
                    color="none",
                    linewidth=0,
                    label=label,
                )
            )
        elif has_circles and area_source in ("window", "window_equivalent"):
            handles.append(
                mpatches.Patch(
                    facecolor=_CIRCLE_WINDOW_FILL_COLOR,
                    alpha=_CIRCLE_WINDOW_FILL_ALPHA,
                    edgecolor=_CIRCLE_WINDOW_LINE_COLOR,
                    linewidth=_CIRCLE_WINDOW_LINE_WIDTH,
                    linestyle=_CIRCLE_WINDOW_LINE_STYLE,
                    label=label,
                )
            )

    if handles:
        legend = ax.legend(
            handles=handles,
            frameon=True,
            fontsize=9,
            edgecolor="0.72",
            facecolor="white",
            framealpha=0.92,
            loc=loc,
            bbox_to_anchor=(anchor_x, anchor_y),
            borderpad=0.45,
            handlelength=1.6,
            handletextpad=0.7,
        )
        if legend is not None:
            legend.set_zorder(_ANNOTATION_ZORDER + 2)


def _compute_adaptive_figsize(layout: _DecorationLayout) -> tuple[float, float]:
    """根据数据范围自适应计算 figure 尺寸，使 1m 物理长度尽量一致。

    目标：数据跨度 50m 时 figure 短边约 25cm。
    结果裁剪到 [_MIN_FIGSIZE_CM, _MAX_FIGSIZE_CM] 区间。
    """
    target = _TARGET_SCALE_CM_PER_METER
    # axes 物理尺寸 = 数据范围 × 目标比例尺
    # figure 尺寸 = axes 尺寸 / axes 占 figure 的比例
    fig_w = layout.x_span * target / _MAIN_AXES_FULL[2]
    fig_h = layout.y_span * target / _MAIN_AXES_FULL[3]

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
) -> str:
    """绘制并保存单张迹线长度图。

    ``figsize_cm`` 为 ``None`` 时，figure 尺寸会根据数据范围自适应，
    确保不同图之间 1m 的物理长度尽量一致，面积具有可比性。

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
    layout = _build_decoration_layout(
        arr,
        circle_windows=selected_circles,
        hull_overlay=selected_hull,
    )
    effective_figsize = figsize_cm if figsize_cm is not None else _compute_adaptive_figsize(layout)
    fig, ax = new_figure(effective_figsize, dpi=dpi)
    ax.set_position(_MAIN_AXES_FULL)

    # 1. 底层：凸包或圆窗（二选一）
    if selected_hull is not None:
        _add_convex_hull_overlay(ax, selected_hull)
    elif has_circles:
        _add_circle_window_overlays(ax, selected_circles)

    # 2. 顶层：迹线
    ax.plot(
        x_plot, y_plot, "-",
        color=_TRACE_LINE_COLOR,
        linewidth=_TRACE_LINE_WIDTH,
        zorder=_TRACE_ZORDER,
    )

    _style_trace_axes(ax)
    _apply_decoration_limits(ax, layout)

    # 3. 装饰元素（全部在主图框内，自动选择最少遮挡迹线的角落）
    xlim = (layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad)
    ylim = (layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad)
    positions = resolve_decoration_positions(
        arr,
        xlim=xlim,
        ylim=ylim,
        layout=_DEFAULT_LAYOUT,
        stats_row_count=len(statistics_lines or ()),
        has_compass=True,
        scale_length_data=layout.scale_length,
    )
    legend_anchor = positions["legend"]
    stats_rect = positions["stats"]
    scale_data_x0, scale_data_y = positions["scale"]

    _add_north_arrow(ax, north_angle_deg)
    _add_scale_bar(ax, layout, data_x0=scale_data_x0, data_y=scale_data_y)
    _add_legend(
        ax,
        area_source,
        has_hull,
        has_circles,
        anchor_x=legend_anchor[0],
        anchor_y=legend_anchor[1],
        loc=legend_anchor[2],
    )
    _add_statistics_box(ax, statistics_lines, rect=stats_rect)

    ax.set_title(title, pad=10, **text_font_kwargs(fontsize=12.0, fontweight="bold"))
    return save_figure(fig, output_dir, filename, dpi=dpi)
