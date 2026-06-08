"""迹线图与预览图共享的布局工具函数与常量。

本模块提取自 ``trace_plot.py`` 与 ``preview_plot.py`` 的公共代码，
消除两处 150+ 行的重复函数与常量定义。
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from matplotlib.patches import Rectangle

from ._helpers import _north_arrow_geometry
from .style import text_font_kwargs

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

__all__ = [
    "_add_north_arrow",
    "_add_outer_frame",
    "_add_scale_bar_band",
    "_add_statistics_box",
    "_blank_panel_axes",
    "_choose_scale_length",
    "_resolve_layout",
    "_resolve_node_style",
    "_split_statistics_line",
    "_statistics_font_size",
    "_style_trace_axes",
    "_style_trace_data_axes",
]

# ── 共享常量 ─────────────────────────────────────────────

_ANNOTATION_LINE_WIDTH = 0.75
_ANNOTATION_ZORDER = 12

_FRAME_BOTTOM = 0.055
_FRAME_LEFT = 0.035
_FRAME_WIDTH = 0.93

_SINGLE_FRAME_TOP = 0.940
_DOUBLE_FRAME_TOP = 0.920

_HARD_GAP = 0.020
_LEGEND_BOTTOM_MARGIN = 0.010
_LEGEND_W = 0.285

_MIN_DATA_SPAN = 1.0

_STATS_W = 0.285
_STATS_H = 0.46

_TRACE_AXES_BOUNDS = (0.065, 0.185, 0.57, 0.705)
_STATS_AXES_BOUNDS = (0.66, 0.145, 0.285, 0.65)
_SCALE_AXES_BOUNDS = (0.065, 0.075, 0.57, 0.08)

# 指北针默认参数（与 TracePlotLayout 默认值一致）
_DEFAULT_ARROW_REL_LEN = 0.06
_DEFAULT_ARROW_REL_X = 0.86
_DEFAULT_ARROW_REL_Y = 0.86

# ── 单位转换 ─────────────────────────────────────────────

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

_UNIT_MATH_TEXT: dict[str, str] = {
    "__TRACE_UNIT_M2_INV__": r"$\mathrm{m}^{-2}$",
    "__TRACE_UNIT_M_INV__": r"$\mathrm{m}^{-1}$",
    "__TRACE_UNIT_M2__": r"$\mathrm{m}^{2}$",
    "__TRACE_UNIT_CM__": r"$\mathrm{cm}$",
    "__TRACE_UNIT_M__": r"$\mathrm{m}$",
}

# ── 节点样式预设 ─────────────────────────────────────────

_NODE_STYLE_PRESETS: dict[str, dict[str, dict[str, object]]] = {
    "default": {
        "I": {
            "marker": "o",
            "markerfacecolor": "#4CAF50",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
        "Y": {
            "marker": "^",
            "markerfacecolor": "#F44336",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
        "X": {
            "marker": "X",
            "markerfacecolor": "#2196F3",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
    },
    "solid": {
        "I": {
            "marker": "o",
            "markerfacecolor": "#2E7D32",
            "markeredgecolor": "#1B5E20",
            "markeredgewidth": 1.0,
        },
        "Y": {
            "marker": "^",
            "markerfacecolor": "#C62828",
            "markeredgecolor": "#B71C1C",
            "markeredgewidth": 1.0,
        },
        "X": {
            "marker": "X",
            "markerfacecolor": "#1565C0",
            "markeredgecolor": "#0D47A1",
            "markeredgewidth": 1.0,
        },
    },
    "hollow": {
        "I": {
            "marker": "o",
            "markerfacecolor": "none",
            "markeredgecolor": "#4CAF50",
            "markeredgewidth": 1.2,
        },
        "Y": {
            "marker": "^",
            "markerfacecolor": "none",
            "markeredgecolor": "#F44336",
            "markeredgewidth": 1.2,
        },
        "X": {
            "marker": "X",
            "markerfacecolor": "none",
            "markeredgecolor": "#2196F3",
            "markeredgewidth": 1.2,
        },
    },
    "dark": {
        "I": {
            "marker": "o",
            "markerfacecolor": "#1B5E20",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
        "Y": {
            "marker": "^",
            "markerfacecolor": "#B71C1C",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
        "X": {
            "marker": "X",
            "markerfacecolor": "#0D47A1",
            "markeredgecolor": "black",
            "markeredgewidth": 0.8,
        },
    },
}


# ── 比例尺 ───────────────────────────────────────────────


def _choose_scale_length(base_span: float) -> float:
    """根据数据跨度自适应选择规整比例尺长度（1/2/5 × 10ⁿ 序列）。"""
    target = base_span / 5.0
    if target <= 0.0:
        return 1.0
    exponent = math.floor(math.log10(target))
    base = target / (10.0**exponent)
    if base <= 1.0:
        scale = 1.0
    elif base <= 2.0:
        scale = 2.0
    elif base <= 5.0:
        scale = 5.0
    else:
        scale = 10.0
    return scale * (10.0**exponent)


def _format_scale_label(length: float) -> str:
    if length >= 1.0:
        return f"{length:g} $\\mathrm{{m}}$"
    return f"{length * 100:g} $\\mathrm{{cm}}$"


# ── 统计框 ───────────────────────────────────────────────


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


def _split_statistics_line(line: str) -> tuple[str, str]:
    text = str(line).strip()
    for separator in ("：", ":"):
        if separator in text:
            label, value = text.split(separator, 1)
            return _compact_statistics_label(label.strip()), _mathtext_units(value.strip())
    return _compact_statistics_label(text), ""


def _add_statistics_box(
    ax,
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
        panel_x0 = 0.02
        panel_x1 = 0.98
        panel_y0 = 0.02
        panel_y1 = 0.98
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
    if len(rows) == 1:
        first_row_y = (panel_y1 + panel_y0) / 2
        row_step = 0
    else:
        row_step = (first_row_y - bottom_y) / (len(rows) - 1)
    font_size = _statistics_font_size(len(rows))

    ax.add_patch(
        Rectangle(
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
        )
    )
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


# ── 布局解析 ─────────────────────────────────────────────


def _resolve_layout(title: str) -> dict[str, tuple[float, float, float, float]]:
    """根据标题行数动态解析各轴在 figure 中的位置。

    与 preview_plot.py 保持完全一致的布局策略：
    - 统计框占据指北针位置（frame 右上区域），不做独立指北针面板。
    - 图例框高度根据内容自适应，底边固定。
    - 指北针直接绘制在数据轴左上角。
    """
    title_lines = title.count("\n") + 1 if title else 1
    frame_top = _DOUBLE_FRAME_TOP if title_lines >= 2 else _SINGLE_FRAME_TOP
    frame_h = frame_top - _FRAME_BOTTOM

    # 统计框整体上移，占据原指北针位置
    stats_y1 = frame_top - _LEGEND_BOTTOM_MARGIN
    stats_y0 = stats_y1 - _STATS_H

    # 图例放在统计框下方，动态高度，底边余量 0.055
    legend_y1 = stats_y0 - _HARD_GAP
    legend_y0 = _FRAME_BOTTOM + 0.055
    legend_h = legend_y1 - legend_y0

    info_left = _STATS_AXES_BOUNDS[0]

    return {
        "trace_outer_frame": (_FRAME_LEFT, _FRAME_BOTTOM, _FRAME_WIDTH, frame_h),
        "trace_data": _TRACE_AXES_BOUNDS,
        "trace_statistics": (info_left, stats_y0, _STATS_W, _STATS_H),
        "trace_legend": (info_left, legend_y0, _LEGEND_W, legend_h),
        "trace_scale": _SCALE_AXES_BOUNDS,
    }


# ── 外框与面板 ───────────────────────────────────────────


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


def _blank_panel_axes(
    fig: plt.Figure, bounds: tuple[float, float, float, float], label: str
) -> plt.Axes:
    ax = fig.add_axes(bounds, label=label)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_frame_on(False)
    ax.set_facecolor("none")
    return ax


# ── 坐标轴样式 ───────────────────────────────────────────


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


# ── 指北针 ───────────────────────────────────────────────


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

    arrow_len = _DEFAULT_ARROW_REL_LEN if arrow_len is None else arrow_len

    if center is None:
        center_x = _DEFAULT_ARROW_REL_X
        center_y = _DEFAULT_ARROW_REL_Y
    else:
        center_x, center_y = center
    (base_x, base_y), (tip_x, tip_y), (label_x, label_y), _dx, _dy = _north_arrow_geometry(
        north_angle_deg, center_x, center_y, arrow_len
    )

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


# ── 比例尺带 ─────────────────────────────────────────────


def _render_legend(
    ax: plt.Axes,
    items: list[tuple[str, str]],
    styles: dict[str, Any],
    *,
    row_spacing: float,
    top_margin: float,
    bottom_margin: float,
    box_height_cap: float,
    box_bottom: float,
    first_row_offset: float,
) -> None:
    """绘制自适应图例框(背景 + 图标行 + 文本)。

    供数据图 _add_legend 与预览图 _add_preview_legend 共享,消除约 40 行
    重复的布局/绘制骨架。布局间距与各图标样式由调用方算好后通过参数注入,
    items 列表(由各自业务逻辑构建)决定显示哪些行。
    """
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_axis_off()

    n_items = len(items)
    box_height = min(top_margin + n_items * row_spacing + bottom_margin, box_height_cap)

    ax.add_patch(
        Rectangle(
            (0.02, box_bottom),
            0.96,
            box_height,
            facecolor="white",
            edgecolor="0.68",
            linewidth=0.6,
            alpha=0.94,
            transform=ax.transAxes,
            clip_on=True,
            zorder=_ANNOTATION_ZORDER,
        )
    )

    first_row_y = box_bottom + box_height - top_margin - first_row_offset
    y_positions = tuple(first_row_y - i * row_spacing for i in range(n_items))
    icon_h = 0.12
    icon_half = icon_h / 2.0
    for (kind, label), y in zip(items, y_positions, strict=False):
        if kind == "trace":
            ax.plot(
                [0.08, 0.24],
                [y, y],
                color=styles["trace_color"],
                linewidth=styles["trace_width"],
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
                    facecolor=styles["hull_fill"],
                    alpha=styles["hull_alpha"],
                    edgecolor=styles["hull_edge"],
                    linewidth=styles["hull_lw"],
                    linestyle=styles["hull_ls"],
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
                    facecolor=styles["circle_fill"],
                    alpha=styles["circle_alpha"],
                    edgecolor=styles["circle_edge"],
                    linewidth=styles["circle_lw"],
                    linestyle=styles["circle_ls"],
                    transform=ax.transAxes,
                    clip_on=True,
                    zorder=_ANNOTATION_ZORDER + 1,
                )
            )
        elif kind.startswith("node_"):
            node_type = kind.replace("node_", "")
            node_ms = styles["node_style"]
            ms = node_ms.get(node_type, node_ms["I"])
            ax.plot(
                0.16,
                y,
                linestyle="none",
                markersize=3.5,
                transform=ax.transAxes,
                clip_on=True,
                zorder=_ANNOTATION_ZORDER + 1,
                **ms,
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


def _draw_scale_bar(
    ax: plt.Axes,
    x0: float,
    x1: float,
    y: float,
    tick: float,
    scale_length: float,
    *,
    label_offset_ratio: float,
) -> None:
    """绘制比例尺主体(横线 + 两端竖 tick + 标签文本)。

    供数据轴版(_add_scale_bar)与独立比例尺带版(_add_scale_bar_band)共享,
    消除两处约 30 行重复的绘制逻辑。坐标与文本偏移由调用方算好后传入。
    """
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
        y - tick * label_offset_ratio,
        _format_scale_label(scale_length),
        ha="center",
        va="top",
        clip_on=True,
        zorder=_ANNOTATION_ZORDER,
        **text_font_kwargs(fontsize=7.2, color="black"),
    )


def _add_scale_bar_band(
    ax: plt.Axes,
    xlim: tuple[float, float],
    scale_length: float,
) -> None:
    """在独立比例尺带中绘制与数据轴同尺度的比例尺。"""
    ax.set_xlim(*xlim)
    ax.set_ylim(0.0, 1.0)
    ax.set_axis_off()

    x_span = xlim[1] - xlim[0]
    x0 = xlim[0] + x_span * 0.04
    if x0 + scale_length > xlim[1]:
        x0 = xlim[1] - scale_length - x_span * 0.04
    x1 = x0 + scale_length
    y = 0.62
    tick = 0.17

    _draw_scale_bar(ax, x0, x1, y, tick, scale_length, label_offset_ratio=0.85)


# ── 节点样式 ─────────────────────────────────────────────


def _resolve_node_style(style: dict[str, Any]) -> dict[str, dict[str, object]]:
    """根据 style 中的 node_style 预设名返回对应的节点标记样式字典。"""
    preset_name = style.get("node_style", "default")
    if preset_name in _NODE_STYLE_PRESETS:
        return _NODE_STYLE_PRESETS[preset_name]
    return _NODE_STYLE_PRESETS["default"]
