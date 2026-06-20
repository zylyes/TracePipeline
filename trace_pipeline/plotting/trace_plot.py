"""迹线长度图绘制。"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple
from collections import defaultdict

import numpy as np
from matplotlib.patches import Circle, Polygon

from ._helpers import add_data_north_arrow, compute_data_bounds, new_figure, save_figure
from ._layout import (
    _MIN_DATA_SPAN,
    _TRACE_AXES_BOUNDS,
    _add_outer_frame,
    _add_scale_bar_band,
    _add_statistics_box,
    _blank_panel_axes,
    _choose_scale_length,
    _draw_scale_bar,
    _render_legend,
    _resolve_layout,
    _resolve_node_style,
    _style_trace_data_axes,
)
from .style import configure_style, heading_font_kwargs

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = [
    "CircleWindowOverlay",
    "ConvexHullOverlay",
    "NodeOverlay",
    "render_trace_plot",
    "segments_to_xy",
]

_DEFAULT_TRACE_DPI = 300
_TARGET_SCALE_CM_PER_METER: float = 0.35
_MIN_FIGSIZE_CM: tuple[float, float] = (12.0, 8.0)
_MAX_FIGSIZE_CM: tuple[float, float] = (36.0, 25.0)
_TRACE_LINE_COLOR = (0, 0, 0)
_TRACE_LINE_WIDTH = 0.85
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

    x_values = np.column_stack(
        [seg_arr[:, 0], seg_arr[:, 2], np.full((n_segments,), np.nan)]
    ).ravel()
    y_values = np.column_stack(
        [seg_arr[:, 1], seg_arr[:, 3], np.full((n_segments,), np.nan)]
    ).ravel()
    return x_values, y_values


def _valid_circles(
    circle_windows: Sequence[CircleWindowOverlay] | None,
) -> list[CircleWindowOverlay]:
    """返回几何有效的圆窗列表（有限坐标且正半径）。"""
    return [
        cw
        for cw in (circle_windows or ())
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

    extra_xs_parts: list[np.ndarray] = []
    extra_ys_parts: list[np.ndarray] = []
    if circles:
        extra_xs_parts.append(circle_xs)
        extra_ys_parts.append(circle_ys)
    if hull_overlay is not None and hull_overlay.vertices.size > 0:
        hull_vertices = np.asarray(hull_overlay.vertices, dtype=float)
        extra_xs_parts.append(hull_vertices[:, 0])
        extra_ys_parts.append(hull_vertices[:, 1])
    if node_overlays:
        extra_xs_parts.append(np.array([n.x for n in node_overlays], dtype=float))
        extra_ys_parts.append(np.array([n.y for n in node_overlays], dtype=float))

    extra_xs = np.concatenate(extra_xs_parts) if extra_xs_parts else None
    extra_ys = np.concatenate(extra_ys_parts) if extra_ys_parts else None
    return compute_data_bounds(segments, extra_xs=extra_xs, extra_ys=extra_ys)


def _build_decoration_layout(
    segments: np.ndarray,
    circle_windows: Sequence[CircleWindowOverlay] | None = None,
    hull_overlay: ConvexHullOverlay | None = None,
    node_overlays: Sequence[NodeOverlay] | None = None,
) -> _DecorationLayout:
    x_min, x_max, y_min, y_max = _data_bounds(
        segments,
        circle_windows=circle_windows,
        hull_overlay=hull_overlay,
        node_overlays=node_overlays,
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
        left_pad=max(
            x_span * _DEFAULT_LAYOUT.left_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio
        ),
        right_pad=right_pad,
        bottom_pad=max(
            y_span * _DEFAULT_LAYOUT.bottom_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio
        ),
        top_pad=max(
            y_span * _DEFAULT_LAYOUT.top_pad_ratio, base_span * _DEFAULT_LAYOUT.pad_base_ratio
        ),
        scale_length=scale_length,
    )


def _apply_decoration_limits(ax: plt.Axes, layout: _DecorationLayout) -> None:
    ax.set_xlim(layout.data_x_min - layout.left_pad, layout.data_x_max + layout.right_pad)
    ax.set_ylim(layout.data_y_min - layout.bottom_pad, layout.data_y_max + layout.top_pad)


def _decoration_limits(
    layout: _DecorationLayout,
) -> tuple[tuple[float, float], tuple[float, float]]:
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
    tick = min(
        layout.bottom_pad * _DEFAULT_LAYOUT.tick_pad_ratio,
        layout.base_span * _DEFAULT_LAYOUT.tick_base_ratio,
    )

    _draw_scale_bar(ax, x0, x1, y, tick, layout.scale_length, label_offset_ratio=1.45)


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


def _add_node_overlays(
    ax: plt.Axes,
    node_overlays: Sequence[NodeOverlay],
    style: dict[str, Any] | None = None,
) -> None:
    """在数据轴上绘制节点符号（不标注文字），按节点类型分组批量 scatter 以提升性能。"""
    if not node_overlays:
        return
    node_ms = _resolve_node_style(style or {})

    # 按节点类型分组
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for node in node_overlays:
        grouped[node.node_type].append((node.x, node.y))

    # 批量绘制每种类型
    for ntype, points in grouped.items():
        if not points:
            continue
        xs, ys = zip(*points)
        ms = node_ms.get(ntype, node_ms["I"])

        # 将 plot 样式参数映射为 scatter 兼容参数
        # scatter 的 s = markersize**2，markersize=4 → s=16
        # plot 的 markerfacecolor → scatter 的 facecolors
        # plot 的 markeredgecolor → scatter 的 edgecolors
        # plot 的 markeredgewidth → scatter 的 linewidths
        ax.scatter(
            xs,
            ys,
            marker=ms.get("marker", "o"),
            s=16,  # markersize=4 → s=4**2=16
            facecolors=ms.get("markerfacecolor", "#4CAF50"),
            edgecolors=ms.get("markeredgecolor", "black"),
            linewidths=ms.get("markeredgewidth", 0.8),
            zorder=_TRACE_ZORDER + 2,
        )


def _add_legend(
    ax: plt.Axes,
    area_source: str,
    has_hull: bool,
    has_circles: bool,
    has_nodes: bool = False,
    node_overlays: Sequence[NodeOverlay] | None = None,
) -> None:
    """绘制自适应图例。"""
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

    styles = {
        "trace_color": _TRACE_LINE_COLOR,
        "trace_width": _TRACE_LINE_WIDTH,
        "hull_fill": _HULL_FILL_COLOR,
        "hull_alpha": _HULL_FILL_ALPHA,
        "hull_edge": _HULL_LINE_COLOR,
        "hull_lw": _HULL_LINE_WIDTH,
        "hull_ls": _HULL_LINE_STYLE,
        "circle_fill": _CIRCLE_WINDOW_FILL_COLOR,
        "circle_alpha": _CIRCLE_WINDOW_FILL_ALPHA,
        "circle_edge": _CIRCLE_WINDOW_LINE_COLOR,
        "circle_lw": _CIRCLE_WINDOW_LINE_WIDTH,
        "circle_ls": _CIRCLE_WINDOW_LINE_STYLE,
        "node_style": _resolve_node_style({}),
    }
    _render_legend(
        ax,
        items,
        styles,
        row_spacing=0.18,
        top_margin=0.06,
        bottom_margin=0.06,
        box_height_cap=0.94,
        box_bottom=0.04,
        first_row_offset=0.08,
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
    style: dict[str, Any] | None = None,
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
            x_plot,
            y_plot,
            "-",
            color=_TRACE_LINE_COLOR,
            linewidth=_TRACE_LINE_WIDTH,
            zorder=_TRACE_ZORDER,
        )

    # 2.5 节点覆盖层
    if include_nodes and node_overlays:
        _add_node_overlays(ax, node_overlays, style=style)

    _style_trace_data_axes(ax)
    _apply_decoration_limits(ax, layout)

    if include_decorations:
        # 3. 装饰元素 — 指北针画在数据轴左上角
        xlim, _ylim = _decoration_limits(layout)
        _north_x = xlim[0] + layout.x_span * 0.05
        _north_y = layout.data_y_max + layout.top_pad - layout.y_span * 0.08
        _arrow_len = layout.base_span * 0.10
        add_data_north_arrow(ax, north_angle_deg, _north_x, _north_y, _arrow_len)

        scale_ax = _blank_panel_axes(fig, layout_bounds["trace_scale"], "trace_scale")
        _add_scale_bar_band(scale_ax, xlim, layout.scale_length)

        legend_ax = _blank_panel_axes(fig, layout_bounds["trace_legend"], "trace_legend")
        _add_legend(
            legend_ax,
            area_source,
            has_hull,
            has_circles,
            has_nodes=has_nodes,
            node_overlays=node_overlays,
        )

        stats_ax = _blank_panel_axes(fig, layout_bounds["trace_statistics"], "trace_statistics")
        _add_statistics_box(stats_ax, statistics_lines, rect=(0.02, 0.02, 0.98, 0.98))

        fig.suptitle(title, y=0.03, **heading_font_kwargs(fontsize=10.4, fontweight="bold"))

    return save_figure(fig, output_dir, filename, dpi=dpi, pad_inches=0.08, bbox_inches="tight")
