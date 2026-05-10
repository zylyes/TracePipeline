"""装饰元素自动避让布局。

将 axes 视为单位正方形 [0,1] × [0,1]，把迹线段按线性插值打入 60×80 栅格，
为图例、统计框、比例尺三个装饰元素分别选择「覆盖迹线最少」的角落。
按面积降序贪心放置（统计框 → 图例 → 比例尺），互不重叠，并把指北针视为已占用区。
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["resolve_decoration_positions"]

_GRID_H: int = 60
_GRID_W: int = 80
_BLOCK_PENALTY: float = 1e6
_OVERLAP_TOLERANCE: float = 1e-9

# 角名 → matplotlib legend loc 名（与 bbox_to_anchor 配合）
_CORNER_TO_LEGEND_LOC: dict[str, str] = {
    "BL": "lower left",
    "BR": "lower right",
    "TL": "upper left",
    "TR": "upper right",
    "ML": "center left",
    "MR": "center right",
    "TM": "upper center",
    "BM": "lower center",
}


def _build_occupancy(segments: np.ndarray, xlim: tuple[float, float], ylim: tuple[float, float]) -> np.ndarray:
    occ = np.zeros((_GRID_H, _GRID_W), dtype=np.float32)
    arr = np.asarray(segments, dtype=float)
    if arr.size == 0 or arr.ndim != 2 or arr.shape[1] != 4:
        return occ
    sx = xlim[1] - xlim[0]
    sy = ylim[1] - ylim[0]
    if sx <= 0.0 or sy <= 0.0:
        return occ
    for x0, y0, x1, y1 in arr:
        if not (math.isfinite(x0) and math.isfinite(y0) and math.isfinite(x1) and math.isfinite(y1)):
            continue
        fx0 = (x0 - xlim[0]) / sx
        fx1 = (x1 - xlim[0]) / sx
        fy0 = (y0 - ylim[0]) / sy
        fy1 = (y1 - ylim[0]) / sy
        n = max(2, int(math.hypot((fx1 - fx0) * _GRID_W, (fy1 - fy0) * _GRID_H)) + 1)
        gx = np.clip((np.linspace(fx0, fx1, n) * _GRID_W).astype(int), 0, _GRID_W - 1)
        gy = np.clip((np.linspace(fy0, fy1, n) * _GRID_H).astype(int), 0, _GRID_H - 1)
        np.add.at(occ, (gy, gx), 1.0)
    return occ


def _rect_to_grid(rect: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x0 = max(0, int(math.floor(rect[0] * _GRID_W)))
    x1 = min(_GRID_W, int(math.ceil(rect[2] * _GRID_W)))
    y0 = max(0, int(math.floor(rect[1] * _GRID_H)))
    y1 = min(_GRID_H, int(math.ceil(rect[3] * _GRID_H)))
    return x0, y0, x1, y1


def _score_rect(occ: np.ndarray, rect: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = _rect_to_grid(rect)
    if x1 <= x0 or y1 <= y0:
        return float("inf")
    return float(occ[y0:y1, x0:x1].sum())


def _block_rect(occ: np.ndarray, rect: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = _rect_to_grid(rect)
    if x1 > x0 and y1 > y0:
        occ[y0:y1, x0:x1] += _BLOCK_PENALTY


def _corner_rects(
    width: float,
    height: float,
    margin: float,
    corners: tuple[str, ...] = ("BL", "BR", "TL", "TR", "ML", "MR", "TM", "BM"),
) -> tuple[list[tuple[float, float, float, float]], list[str]]:
    """为给定大小矩形生成各候选位置（4 角 + 4 中边）。"""
    width = min(max(width, 0.0), 1.0 - 2.0 * margin)
    height = min(max(height, 0.0), 1.0 - 2.0 * margin)
    cx0 = (1.0 - width) / 2.0
    cx1 = cx0 + width
    cy0 = (1.0 - height) / 2.0
    cy1 = cy0 + height
    rects: list[tuple[float, float, float, float]] = []
    names: list[str] = []
    for corner in corners:
        if corner == "BL":
            rect = (margin, margin, margin + width, margin + height)
        elif corner == "BR":
            rect = (1.0 - margin - width, margin, 1.0 - margin, margin + height)
        elif corner == "TL":
            rect = (margin, 1.0 - margin - height, margin + width, 1.0 - margin)
        elif corner == "TR":
            rect = (1.0 - margin - width, 1.0 - margin - height, 1.0 - margin, 1.0 - margin)
        elif corner == "ML":
            rect = (margin, cy0, margin + width, cy1)
        elif corner == "MR":
            rect = (1.0 - margin - width, cy0, 1.0 - margin, cy1)
        elif corner == "TM":
            rect = (cx0, 1.0 - margin - height, cx1, 1.0 - margin)
        elif corner == "BM":
            rect = (cx0, margin, cx1, margin + height)
        else:
            continue
        rects.append(rect)
        names.append(corner)
    return rects, names


def _stats_height(row_count: int, h_min: float, h_max: float) -> float:
    """根据统计行数估算 stats box 高度（按绝对量；与 _add_statistics_box 内部行步长公式一致）。

    title_offset(0.045) + rule_offset 之下首行(0.120-0.045=0.075) + (n-1)*row_step + bottom_offset(0.045)。
    """
    rows = max(1, int(row_count))
    title_to_first = 0.120
    bottom_offset = 0.045
    row_step_min = 0.030
    needed = title_to_first + (rows - 1) * row_step_min + bottom_offset
    return float(min(max(needed, h_min), h_max))


def _legend_anchor_from_corner(
    corner: str,
    margin: float,
) -> tuple[float, float, str]:
    """把角名映射成 matplotlib bbox_to_anchor + loc 三元组。"""
    loc = _CORNER_TO_LEGEND_LOC[corner]
    if corner == "BL":
        return (margin, margin, loc)
    if corner == "BR":
        return (1.0 - margin, margin, loc)
    if corner == "TL":
        return (margin, 1.0 - margin, loc)
    if corner == "TR":
        return (1.0 - margin, 1.0 - margin, loc)
    if corner == "ML":
        return (margin, 0.5, loc)
    if corner == "MR":
        return (1.0 - margin, 0.5, loc)
    if corner == "TM":
        return (0.5, 1.0 - margin, loc)
    # BM
    return (0.5, margin, loc)


def _scale_bar_data_position(
    rect: tuple[float, float, float, float],
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    scale_length_data: float,
) -> tuple[float, float]:
    """把比例尺候选矩形换算成 (data_x0, data_y) — 对应原 _add_scale_bar 接口。

    比例尺起点固定在矩形左缘内一小段；y 取矩形中线偏下 30%，与原视觉一致。
    """
    sx = xlim[1] - xlim[0]
    sy = ylim[1] - ylim[0]
    # x0：在矩形左缘加少量内缩
    inner_pad_axes = 0.01
    rx0 = rect[0] + inner_pad_axes
    ry_center = rect[1] + (rect[3] - rect[1]) * 0.30
    data_x0 = xlim[0] + rx0 * sx
    data_y = ylim[0] + ry_center * sy
    # 防止超出 xlim：如果 scale_length_data 加 x0 超出 xlim[1]，把 x0 左推
    if data_x0 + scale_length_data > xlim[1]:
        data_x0 = xlim[1] - scale_length_data - 0.01 * sx
    return data_x0, data_y


def _legacy_positions(
    layout: Any,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    scale_length_data: float,
) -> dict[str, Any]:
    """auto_placement=False 时返回与原硬编码完全一致的位置。"""
    sx = xlim[1] - xlim[0]
    sy = ylim[1] - ylim[0]
    base_span = max(sx, sy, 1.0)  # 与 _MIN_DATA_SPAN 一致
    # 注意：原 base_span 用的是去掉 padding 的 data 跨度；保守起见，调用方应传整体 xlim/ylim
    # 这里复刻原 _add_scale_bar 中的 base_span * 0.03 / 0.18 行为
    legacy_legend = (layout.legend_rel_x, layout.legend_rel_y, "lower left")
    legacy_stats = (
        layout.stats_box_rel_x0,
        layout.stats_box_rel_y0,
        layout.stats_box_rel_x1,
        layout.stats_box_rel_y1,
    )
    # 旧实现使用 layout.data_x_min + base_span*0.03，调用方在 trace_plot.py 仍直接走原路径
    # 这里返回 None 让调用方知道走 legacy；但为了接口一致，给一个等价 data 坐标
    legacy_scale_x = xlim[0] + base_span * 0.03  # 当 left_pad 较小时近似 data_x_min + base_span*0.03
    legacy_scale_y = ylim[0] + base_span * layout.scale_bar_y_offset_ratio
    return {
        "legend": legacy_legend,
        "stats": legacy_stats,
        "scale": (legacy_scale_x, legacy_scale_y),
        "auto": False,
    }


def resolve_decoration_positions(
    segments: np.ndarray,
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    layout: Any,
    *,
    stats_row_count: int,
    has_compass: bool = True,
    scale_length_data: float = 0.0,
) -> dict[str, Any]:
    """选择最少遮挡迹线的位置。

    Returns:
        {
            "legend": (anchor_x, anchor_y, loc),  # axes 坐标 + matplotlib loc
            "stats":  (rx0, ry0, rx1, ry1),       # axes 坐标矩形
            "scale":  (data_x0, data_y),          # 数据坐标，比例尺左端
            "auto":   bool,                       # 是否启用了避让
        }
    """
    if not getattr(layout, "auto_placement", True):
        return _legacy_positions(layout, xlim, ylim, scale_length_data)

    margin = float(layout.placement_margin)
    occ = _build_occupancy(segments, xlim, ylim)
    if has_compass:
        _block_rect(occ, tuple(layout.compass_rect))

    # 1. statistics box（高大元素优先放角，再考虑中左/中右）
    stats_h = _stats_height(stats_row_count, layout.stats_size_h_min, layout.stats_size_h_max)
    stats_rects, stats_corners = _corner_rects(
        layout.stats_size_w, stats_h, margin,
        corners=("TL", "TR", "BL", "BR", "ML", "MR"),
    )
    stats_scores = [_score_rect(occ, r) for r in stats_rects]
    stats_idx = int(np.argmin(stats_scores))
    stats_rect = stats_rects[stats_idx]
    _block_rect(occ, stats_rect)

    # 2. legend（4 角 + 4 中边都允许，元素较小灵活性更高）
    legend_rects, legend_corners = _corner_rects(
        layout.legend_size_w, layout.legend_size_h, margin,
        corners=("BL", "BR", "TL", "TR", "BM", "TM", "ML", "MR"),
    )
    legend_scores = [_score_rect(occ, r) for r in legend_rects]
    legend_idx = int(np.argmin(legend_scores))
    legend_rect = legend_rects[legend_idx]
    legend_corner = legend_corners[legend_idx]
    _block_rect(occ, legend_rect)
    legend_anchor = _legend_anchor_from_corner(legend_corner, margin)

    # 3. scale bar（水平条，优先底/顶两侧或中部水平边）
    scale_rects, _scale_corners = _corner_rects(
        layout.scale_size_w, layout.scale_size_h, margin,
        corners=("BL", "BR", "TL", "TR", "BM", "TM"),
    )
    scale_scores = [_score_rect(occ, r) for r in scale_rects]
    scale_idx = int(np.argmin(scale_scores))
    scale_rect = scale_rects[scale_idx]
    scale_data = _scale_bar_data_position(scale_rect, xlim, ylim, scale_length_data)

    return {
        "legend": legend_anchor,
        "stats": stats_rect,
        "scale": scale_data,
        "auto": True,
        # 暴露 axes 坐标矩形给单测/调试用
        "_legend_rect": legend_rect,
        "_scale_rect": scale_rect,
    }
