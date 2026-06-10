"""独立预览绘图模块 — 与正式运行结果完全解耦。

本模块仅用于生成样式预览图，所有几何数据均为硬编码的演示数据。
不依赖 trace_pipeline 的任何业务逻辑（统计计算、节点识别、覆盖层构建等）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from matplotlib.patches import Circle, Polygon

from ..geology.transforms import normalize_coordinates, normalize_points_like_lines
from ._helpers import add_data_north_arrow, compute_data_bounds, new_figure, save_figure
from ._layout import (
    _MIN_DATA_SPAN,
    _TRACE_AXES_BOUNDS,
    _add_outer_frame,
    _add_scale_bar_band,
    _add_statistics_box,
    _blank_panel_axes,
    _choose_scale_length,
    _render_legend,
    _resolve_layout,
    _resolve_node_style,
    _style_trace_data_axes,
)
from .rose_plot import _compute_rose_histogram, _draw_rose_axes
from .style import configure_style, heading_font_kwargs
from .trace_plot import segments_to_xy

logger = logging.getLogger(__name__)

# ── 演示数据 ─────────────────────────────────────────────


def _demo_endpoints():
    return np.array(
        [
            [0.0, 0.0, 10.0, 5.0],
            [2.0, 8.0, 12.0, 2.0],
            [5.0, 0.0, 5.0, 10.0],
            [0.0, 5.0, 10.0, 5.0],
            [8.0, 0.0, 8.0, 8.0],
            [3.0, 3.0, 10.0, 8.0],
            [1.0, 7.0, 9.0, 1.0],
            [6.0, 2.0, 6.0, 9.0],
            [5.0, 4.0, 2.0, 8.0],  # 迹线8: 端点(5,4)在线6内部，形成真正的Y型节点
        ],
        dtype=float,
    )


def _demo_rotated_endpoints():
    """旋转后的端点数据，通过与 hull/nodes 相同的变换流程得到。"""
    return normalize_coordinates(_demo_endpoints(), _DEMO_SCANLINE_AZIMUTH, margin=1.0)


def _demo_hull_vertices():
    return np.array(
        [
            [0.0, 0.0],
            [5.0, 0.0],
            [8.0, 0.0],
            [12.0, 2.0],
            [10.0, 8.0],
            [5.0, 10.0],
            [2.0, 8.0],
            [1.0, 7.0],
            [0.0, 5.0],
        ],
        dtype=float,
    )


def _demo_circles():
    return (
        {"center_x": 3.0, "center_y": 3.0, "radius": 2.5},
        {"center_x": 8.0, "center_y": 6.0, "radius": 3.0},
    )


def _demo_nodes():
    return (
        {"x": 0.0, "y": 0.0, "node_type": "I", "node_id": 0, "degree": 1},
        {
            "x": 5.0,
            "y": 4.0,
            "node_type": "Y",
            "node_id": 1,
            "degree": 3,
        },  # Y型: 迹线8端点落在迹线6内部
        {"x": 8.36, "y": 4.18, "node_type": "X", "node_id": 2, "degree": 4},  # X型: 迹线1 × 迹线5
    )


def _demo_rotated_hull_vertices():
    return normalize_points_like_lines(
        _demo_hull_vertices(), _demo_endpoints(), _DEMO_SCANLINE_AZIMUTH, margin=1.0
    )


def _demo_rotated_circles():
    centers = np.array([[c["center_x"], c["center_y"]] for c in _demo_circles()], dtype=float)
    rotated = normalize_points_like_lines(
        centers, _demo_endpoints(), _DEMO_SCANLINE_AZIMUTH, margin=1.0
    )
    return tuple(
        {"center_x": float(rotated[i, 0]), "center_y": float(rotated[i, 1]), "radius": c["radius"]}
        for i, c in enumerate(_demo_circles())
    )


def _demo_rotated_nodes():
    pts = np.array([[n["x"], n["y"]] for n in _demo_nodes()], dtype=float)
    rotated = normalize_points_like_lines(
        pts, _demo_endpoints(), _DEMO_SCANLINE_AZIMUTH, margin=1.0
    )
    return tuple(
        {
            "x": float(rotated[i, 0]),
            "y": float(rotated[i, 1]),
            "node_type": n["node_type"],
            "node_id": n["node_id"],
            "degree": n["degree"],
        }
        for i, n in enumerate(_demo_nodes())
    )


def _demo_joint_strikes():
    return np.array([63.43, 120.96, 0.0, 90.0, 0.0, 54.46, 126.87, 0.0, 90.0], dtype=float)


_DEMO_SCANLINE_AZIMUTH = 298.0
_DEMO_NORTH_ANGLE_DEG = 28.0

_DEMO_STATS_LINES = (
    "测线走向: 298.0°",
    "迹线数量: 9",
    "平均迹长: 8.222 m",
    "I/II/III型裂隙: 1/1/7",
    "测线长度: 8.500 m",
    "露头面积: 50.000 m²",
    "P₁₀ 线密度: 1.059 m⁻¹",
    "P₂₀ 面密度: 0.160 m⁻²",
    "P₂₁ 长度密度: 1.528 m⁻¹",
)

# ── 布局常量（与 trace_plot.py 一致）─────────────────────

_PREVIEW_DPI = 300
_COMPASS_AXES_BOUNDS = (0.76, 0.765, 0.12, 0.095)
_LEGEND_AXES_BOUNDS = (0.66, 0.095, 0.285, 0.20)
_COMPASS_W = 0.12
_COMPASS_H = 0.095
_LEGEND_H = 0.20

# ── 节点标记样式（与 trace_plot.py 共享，通过 _layout._resolve_node_style 使用）────────


@dataclass(frozen=True)
class PreviewDemoData:
    """演示数据容器 — 所有字段均为硬编码常量。"""

    endpoints: np.ndarray = field(default_factory=_demo_endpoints)
    rotated_endpoints: np.ndarray = field(default_factory=_demo_rotated_endpoints)
    hull_vertices: np.ndarray = field(default_factory=_demo_hull_vertices)
    rotated_hull_vertices: np.ndarray = field(default_factory=_demo_rotated_hull_vertices)
    circles: tuple[dict[str, float], ...] = field(default_factory=_demo_circles)
    rotated_circles: tuple[dict[str, float], ...] = field(default_factory=_demo_rotated_circles)
    nodes: tuple[dict[str, Any], ...] = field(default_factory=_demo_nodes)
    rotated_nodes: tuple[dict[str, Any], ...] = field(default_factory=_demo_rotated_nodes)
    joint_strikes: np.ndarray = field(default_factory=_demo_joint_strikes)
    scanline_azimuth: float = _DEMO_SCANLINE_AZIMUTH
    north_angle_deg: float = _DEMO_NORTH_ANGLE_DEG
    stats_lines: tuple[str, ...] = _DEMO_STATS_LINES


_DEMO_DATA = PreviewDemoData()


# ── 样式读取辅助 ─────────────────────────────────────────


def _style_val(style: dict[str, Any], key: str, default: Any) -> Any:
    """安全读取样式值，缺失则回退到默认值。"""
    return style.get(key, default)


# ── 几何辅助 ─────────────────────────────────────────────


def _extract_preview_extras(
    hull_vertices: np.ndarray | None = None,
    circles: tuple[dict[str, float], ...] | None = None,
    nodes: tuple[dict[str, Any], ...] | None = None,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    extra_xs_parts: list[np.ndarray] = []
    extra_ys_parts: list[np.ndarray] = []
    if hull_vertices is not None and hull_vertices.size > 0:
        extra_xs_parts.append(hull_vertices[:, 0])
        extra_ys_parts.append(hull_vertices[:, 1])
    if circles:
        cx = np.array(
            [
                x
                for c in circles
                for x in (c["center_x"] - c["radius"], c["center_x"] + c["radius"])
            ],
            dtype=float,
        )
        cy = np.array(
            [
                y
                for c in circles
                for y in (c["center_y"] - c["radius"], c["center_y"] + c["radius"])
            ],
            dtype=float,
        )
        extra_xs_parts.append(cx)
        extra_ys_parts.append(cy)
    if nodes:
        extra_xs_parts.append(np.array([n["x"] for n in nodes], dtype=float))
        extra_ys_parts.append(np.array([n["y"] for n in nodes], dtype=float))
    extra_xs = np.concatenate(extra_xs_parts) if extra_xs_parts else None
    extra_ys = np.concatenate(extra_ys_parts) if extra_ys_parts else None
    return extra_xs, extra_ys


def _add_preview_legend(
    ax,
    show_hull: bool,
    show_circles: bool,
    show_nodes: bool,
    style: dict[str, Any],
) -> None:
    """绘制动态图例 — 仅显示当前可见的元素类型。"""
    trace_line_color = _style_val(style, "trace_line_color", "#000000")
    trace_line_width = _style_val(style, "trace_line_width", 0.85)
    hull_line_color = _style_val(style, "hull_line_color", "#1565C0")
    circle_window_line_color = _style_val(style, "circle_window_line_color", "#E65100")

    items: list[tuple[str, str]] = [("trace", "迹线")]
    if show_hull:
        items.append(("hull", "凸包"))
    if show_circles:
        items.append(("circle", "圆窗"))
    if show_nodes:
        items.append(("node_I", "孤立端点 (I)"))
        items.append(("node_Y", "三叉节点 (Y)"))
        items.append(("node_X", "交叉节点 (X)"))

    styles = {
        "trace_color": trace_line_color,
        "trace_width": trace_line_width,
        "hull_fill": hull_line_color,
        "hull_alpha": 0.08,
        "hull_edge": hull_line_color,
        "hull_lw": 0.8,
        "hull_ls": "--",
        "circle_fill": circle_window_line_color,
        "circle_alpha": 0.08,
        "circle_edge": circle_window_line_color,
        "circle_lw": 0.8,
        "circle_ls": "--",
        "node_style": _resolve_node_style(style),
    }
    _render_legend(
        ax,
        items,
        styles,
        row_spacing=0.16,
        top_margin=0.08,
        bottom_margin=0.08,
        box_height_cap=0.96,
        box_bottom=0.02,
        first_row_offset=0.02,
    )


def render_preview_trace(
    output_dir: str,
    filename: str,
    style: dict[str, Any],
    *,
    show_hull: bool = True,
    show_circles: bool = True,
    show_nodes: bool = True,
    is_rotated: bool = False,
    dpi: int = _PREVIEW_DPI,
    demo: PreviewDemoData | None = None,
    max_figsize: tuple[float, float] = (36.0, 25.0),
) -> str:
    """绘制并保存预览迹线图。

    所有几何数据来自 ``PreviewDemoData`` 硬编码常量，与真实运行结果完全解耦。
    样式参数通过 ``style`` 字典传入，不修改任何模块级全局变量。

    Args:
        max_figsize: (max_width, max_height) figsize 英寸上限。

    Returns:
        输出文件的完整路径。
    """
    configure_style()
    data = demo if demo is not None else _DEMO_DATA
    segments = data.rotated_endpoints if is_rotated else data.endpoints
    title = (
        f"旋转迹线图（测线走向={data.scanline_azimuth:.1f}°）（预览）"
        if is_rotated
        else "原始迹线图（预览）"
    )

    trace_line_color = _style_val(style, "trace_line_color", "#000000")
    trace_line_width = _style_val(style, "trace_line_width", 0.85)
    hull_line_color = _style_val(style, "hull_line_color", "#1565C0")
    hull_fill_alpha = _style_val(style, "hull_fill_alpha", 0.08)
    circle_window_line_color = _style_val(style, "circle_window_line_color", "#E65100")
    circle_window_fill_alpha = _style_val(style, "circle_window_fill_alpha", 0.08)
    title_font_size = _style_val(style, "title_font_size", 10.4)

    # 选择旋转/原始几何数据
    if is_rotated:
        hull_vertices = data.rotated_hull_vertices
        circles = data.rotated_circles
        nodes = data.rotated_nodes
    else:
        hull_vertices = data.hull_vertices
        circles = data.circles
        nodes = data.nodes

    extra_xs, extra_ys = _extract_preview_extras(
        hull_vertices=hull_vertices if show_hull else None,
        circles=circles if show_circles else None,
        nodes=nodes if show_nodes else None,
    )
    x_min, x_max, y_min, y_max = compute_data_bounds(segments, extra_xs=extra_xs, extra_ys=extra_ys)
    x_span = max(x_max - x_min, _MIN_DATA_SPAN)
    y_span = max(y_max - y_min, _MIN_DATA_SPAN)
    base_span = max(x_span, y_span, _MIN_DATA_SPAN)
    left_pad = max(x_span * 0.14, base_span * 0.08)
    right_pad = max(
        x_span * 0.04,
        base_span * 0.04,
        max(0.0, _choose_scale_length(base_span) - x_span + x_span * 0.05),
    )
    bottom_pad = max(y_span * 0.16, base_span * 0.08)
    top_pad = max(y_span * 0.12, base_span * 0.08)
    xlim = (x_min - left_pad, x_max + right_pad)
    scale_length = _choose_scale_length(base_span)

    figsize_w = max(12.0, min(base_span * 0.35 / _TRACE_AXES_BOUNDS[2], max_figsize[0]))
    figsize_h = max(8.0, min(base_span * 0.35 / _TRACE_AXES_BOUNDS[3], max_figsize[1]))

    fig, ax = new_figure((figsize_w, figsize_h), dpi=dpi)
    ax.remove()

    layout_bounds = _resolve_layout(title)
    _add_outer_frame(fig, layout_bounds["trace_outer_frame"])
    ax = fig.add_axes(layout_bounds["trace_data"], label="trace_data")

    # 1. 底层：凸包
    if show_hull and hull_vertices is not None and hull_vertices.size > 0:
        vertices = np.asarray(hull_vertices, dtype=float)
        if vertices.shape[0] >= 3:
            patch = Polygon(
                vertices,
                fill=True,
                facecolor=hull_line_color,
                alpha=hull_fill_alpha,
                edgecolor=hull_line_color,
                linewidth=0.8,
                linestyle="--",
                zorder=2,
            )
            ax.add_patch(patch)

    # 2. 圆窗（置于凸包上方）
    if show_circles and circles:
        for c in circles:
            patch = Circle(
                (c["center_x"], c["center_y"]),
                c["radius"],
                fill=True,
                facecolor=circle_window_line_color,
                alpha=circle_window_fill_alpha,
                edgecolor=circle_window_line_color,
                linewidth=0.8,
                linestyle="--",
                zorder=3,
            )
            ax.add_patch(patch)

    # 2. 迹线
    x_plot, y_plot = segments_to_xy(segments)
    ax.plot(
        x_plot,
        y_plot,
        "-",
        color=trace_line_color,
        linewidth=trace_line_width,
        zorder=10,
    )

    # 3. 节点
    if show_nodes and nodes:
        node_ms = _resolve_node_style(style)
        for node in nodes:
            ms = node_ms.get(node["node_type"], node_ms["I"])
            ax.plot(
                node["x"],
                node["y"],
                linestyle="none",
                markersize=4,
                zorder=12,
                **ms,
            )

    _style_trace_data_axes(ax)
    ax.set_xlim(*xlim)
    ax.set_ylim(y_min - bottom_pad, y_max + top_pad)

    # 4. 装饰元素
    # 指北针绘制在数据区左上角（数据坐标系）
    north_angle = data.north_angle_deg if is_rotated else 90.0
    _north_x = xlim[0] + x_span * 0.05
    _north_y = (y_max + top_pad) - y_span * 0.08
    _arrow_len = base_span * 0.10
    add_data_north_arrow(ax, north_angle, _north_x, _north_y, _arrow_len)

    scale_ax = _blank_panel_axes(fig, layout_bounds["trace_scale"], "trace_scale")
    _add_scale_bar_band(scale_ax, xlim, scale_length)

    legend_ax = _blank_panel_axes(fig, layout_bounds["trace_legend"], "trace_legend")
    _add_preview_legend(legend_ax, show_hull, show_circles, show_nodes, style)

    stats_ax = _blank_panel_axes(fig, layout_bounds["trace_statistics"], "trace_statistics")
    _add_statistics_box(stats_ax, data.stats_lines)

    fig.suptitle(
        title, y=0.03, **heading_font_kwargs(fontsize=float(title_font_size), fontweight="bold")
    )
    return save_figure(fig, output_dir, filename, dpi=dpi, pad_inches=0.08, bbox_inches="tight")


def render_preview_rose(
    output_dir: str,
    filename: str,
    style: dict[str, Any],
    dpi: int = _PREVIEW_DPI,
    demo: PreviewDemoData | None = None,
    max_figsize: tuple[float, float] = (12.0, 12.0),
) -> str:
    """绘制并保存预览玫瑰图。

    分箱宽度固定为 10°（样式预览无需调整）。

    Args:
        max_figsize: (max_width, max_height) figsize 英寸上限。
    """
    configure_style()
    data = demo if demo is not None else _DEMO_DATA
    strikes = data.joint_strikes

    rose_bar_color = _style_val(style, "rose_bar_color", "#C94C4C")
    rose_bar_edge = _style_val(style, "rose_bar_edge", "#7A1F1F")
    rose_grid_color = _style_val(style, "rose_grid_color", "#d9d9d9")

    bin_width = 10.0
    theta, radii, bar_widths = _compute_rose_histogram(strikes, bin_width=bin_width)

    fig, ax = new_figure((12, 12), dpi=dpi, subplot_kw={"projection": "polar"})
    _draw_rose_axes(
        ax,
        theta,
        radii,
        bar_widths,
        bar_color=rose_bar_color,
        bar_edge=rose_bar_edge,
        grid_color=rose_grid_color,
    )
    fig.suptitle(
        "产状玫瑰花瓣图（预览）",
        y=0.03,
        **heading_font_kwargs(fontsize=10.8, fontweight="bold"),
    )
    return save_figure(fig, output_dir, filename, dpi=dpi, pad_inches=0.08)


__all__ = ["PreviewDemoData", "render_preview_trace", "render_preview_rose"]
