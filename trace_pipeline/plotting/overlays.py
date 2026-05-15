"""覆盖层构建 — 圆窗、凸包、节点等几何覆盖物。

将原本散落在 pipeline.py 中的私有覆盖层函数迁移为公开内部服务，
供 pipeline、后端 StatsService、PreviewService 统一调用。
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import numpy as np

from .trace_plot import CircleWindowOverlay, ConvexHullOverlay, NodeOverlay

if TYPE_CHECKING:
    from ..analysis.models import NodeAnalysis
    from ..geology.statistics import TraceStatistics
    from ..models import TraceData

logger = logging.getLogger(__name__)

__all__ = [
    "build_node_overlays",
    "build_raw_circle_overlays",
    "build_rotated_circle_overlays",
    "build_rotated_node_overlays",
    "build_selected_hull_overlays",
]


def build_raw_circle_overlays(
    trace: TraceData,
    statistics: TraceStatistics,
) -> tuple[CircleWindowOverlay, ...]:
    """根据统计诊断信息构建原始坐标系下的圆窗覆盖层。"""
    from ..geology.angles import azimuth_to_cartesian_deg

    centers: list[tuple[float, float]] = []
    radii: list[float] = []
    for diagnostic in statistics.diagnostics:
        geometry = np.array(
            [diagnostic.center_x, diagnostic.center_y, diagnostic.radius],
            dtype=float,
        )
        if diagnostic.valid and np.isfinite(geometry).all() and diagnostic.radius > 0.0:
            centers.append((diagnostic.center_x, diagnostic.center_y))
            radii.append(float(diagnostic.radius))

    if not centers:
        return ()

    angle = math.radians(azimuth_to_cartesian_deg(trace.scanline_azimuth))
    along = np.array([math.cos(angle), math.sin(angle)], dtype=float)
    left = np.array([-math.sin(angle), math.cos(angle)], dtype=float)
    pts = np.array(centers, dtype=float)
    global_centers = pts[:, [0]] * along + pts[:, [1]] * left
    return tuple(
        CircleWindowOverlay(float(center[0]), float(center[1]), radius)
        for center, radius in zip(global_centers, radii)
    )


def build_rotated_circle_overlays(
    trace: TraceData,
    raw_overlays: tuple[CircleWindowOverlay, ...],
) -> tuple[CircleWindowOverlay, ...]:
    """将原始圆窗覆盖层旋转到测线坐标系。"""
    from ..geology.transforms import normalize_points_like_lines

    if not raw_overlays:
        return ()

    centers = np.array(
        [(overlay.center_x, overlay.center_y) for overlay in raw_overlays],
        dtype=float,
    )
    rotated_centers = normalize_points_like_lines(
        centers, trace.endpoints, trace.scanline_azimuth
    )
    return tuple(
        CircleWindowOverlay(float(center[0]), float(center[1]), overlay.radius)
        for center, overlay in zip(rotated_centers, raw_overlays)
    )


def build_selected_hull_overlays(
    trace: TraceData,
    statistics: TraceStatistics,
) -> tuple[ConvexHullOverlay | None, ConvexHullOverlay | None]:
    """返回与露头面积来源一致的原始/旋转凸包覆盖物。"""
    from ..geology._convex_hull import _buffered_hull_vertices, _compute_convex_hull
    from ..geology.transforms import normalize_points_like_lines

    if statistics.outcrop_area_source not in {"hull", "hull_buffered"}:
        return None, None

    raw_hull = _compute_convex_hull(trace.endpoints)
    if raw_hull is None:
        return None, None

    selected_vertices = raw_hull
    if statistics.outcrop_area_source == "hull_buffered":
        buffer_distance = statistics.hull_buffer_ratio * statistics.mean_trace_length
        buffered_vertices = _buffered_hull_vertices(raw_hull, buffer_distance)
        if buffered_vertices is None:
            return None, None
        selected_vertices = buffered_vertices

    rotated_vertices = normalize_points_like_lines(
        selected_vertices,
        trace.endpoints,
        trace.scanline_azimuth,
    )
    return ConvexHullOverlay(selected_vertices), ConvexHullOverlay(rotated_vertices)


def build_node_overlays(
    node_analysis: NodeAnalysis,
) -> tuple[NodeOverlay, ...]:
    """将节点分析结果转换为绘图覆盖层。"""
    return tuple(
        NodeOverlay(
            x=node.x,
            y=node.y,
            node_type=node.node_type,
            node_id=node.node_id,
            degree=node.degree,
        )
        for node in node_analysis.nodes
    )


def build_rotated_node_overlays(
    node_analysis: NodeAnalysis,
    endpoints: np.ndarray,
    scanline_azimuth: float,
) -> tuple[NodeOverlay, ...]:
    """将原始节点覆盖层旋转到测线坐标系。"""
    from ..geology.transforms import normalize_points_like_lines

    if not node_analysis.nodes:
        return ()

    pts = np.array([(node.x, node.y) for node in node_analysis.nodes], dtype=float)
    rotated = normalize_points_like_lines(pts, endpoints, scanline_azimuth)
    return tuple(
        NodeOverlay(
            x=float(rotated[i, 0]),
            y=float(rotated[i, 1]),
            node_type=node.node_type,
            node_id=node.node_id,
            degree=node.degree,
        )
        for i, node in enumerate(node_analysis.nodes)
    )
