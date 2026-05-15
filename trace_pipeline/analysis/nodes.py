"""节点识别主算法。

基于迹线端点坐标，识别端点节点、迹线交点、搭接节点、共线重叠节点。
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..geometry.segments import (
    collinear_overlap,
    is_degenerate_segment,
    segment_intersection,
)
from .models import NodeAnalysis, NodeRecognitionConfig, TraceIntersection, TraceNode

logger = logging.getLogger(__name__)

__all__ = ["recognize_trace_nodes"]


@dataclass(frozen=True, slots=True)
class _Candidate:
    x: float
    y: float
    trace_idx: int
    event_type: str  # endpoint / intersection / overlap
    param: float = 0.0  # 在线段上的参数 [0,1]，端点为 0 或 1
    partner_trace: int | None = None


def _build_spatial_grid(candidates: list[_Candidate], cell_size: float) -> dict[tuple[int, int], list[int]]:
    """将候选点按网格索引分桶，避免 O(N^2) 全量合并。"""
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, cand in enumerate(candidates):
        cell_x = int(np.floor(cand.x / cell_size))
        cell_y = int(np.floor(cand.y / cell_size))
        grid[(cell_x, cell_y)].append(idx)
    return grid


def _merge_candidates(
    candidates: list[_Candidate],
    tolerance: float,
) -> list[list[_Candidate]]:
    """基于空间网格的候选点聚类，每个簇将合并为一个节点。"""
    if not candidates:
        return []

    cell_size = max(tolerance, 1e-12)
    grid = _build_spatial_grid(candidates, cell_size)
    merged: list[list[_Candidate]] = []
    visited = set()

    for i, cand in enumerate(candidates):
        if i in visited:
            continue
        cluster = [cand]
        visited.add(i)
        cx = int(np.floor(cand.x / cell_size))
        cy = int(np.floor(cand.y / cell_size))

        # 搜索邻域 3x3 网格
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j in visited:
                        continue
                    other = candidates[j]
                    if (cand.x - other.x) ** 2 + (cand.y - other.y) ** 2 <= tolerance * tolerance:
                        cluster.append(other)
                        visited.add(j)
        merged.append(cluster)
    return merged


def _classify_node_type(
    degree: int,
    has_endpoint: bool,
    has_intersection: bool,
    has_overlap: bool,
) -> str:
    """根据连接关系分类节点类型（中文化）。"""
    if has_overlap:
        return "overlap"
    if degree >= 4:
        return "multi"
    if degree == 3:
        return "Y"
    if degree == 2 and has_intersection:
        return "Y" if has_endpoint else "X"
    return "I"


def recognize_trace_nodes(
    endpoints: np.ndarray,
    config: NodeRecognitionConfig,
) -> NodeAnalysis:
    """识别裂隙网络节点。

    Args:
        endpoints: (N, 4) 端点坐标，列序 [x1, y1, x2, y2]。
        config: 节点识别配置。

    Returns:
        NodeAnalysis — 包含节点列表、相交事件列表和警告。
    """
    if not config.enabled or endpoints.size == 0:
        return NodeAnalysis(nodes=(), intersections=(), warnings=(), degenerate_skipped=0)

    n = endpoints.shape[0]
    tol = config.merge_tolerance

    candidates: list[_Candidate] = []
    intersections: list[TraceIntersection] = []
    warnings_list: list[str] = []
    degenerate_count = 0

    # 1. 收集所有端点作为候选
    for i in range(n):
        x1, y1, x2, y2 = endpoints[i]
        if is_degenerate_segment(x1, y1, x2, y2, tol):
            degenerate_count += 1
            continue
        candidates.append(_Candidate(x=x1, y=y1, trace_idx=i, event_type="endpoint", param=0.0))
        candidates.append(_Candidate(x=x2, y=y2, trace_idx=i, event_type="endpoint", param=1.0))

    # 2. 两两相交检测
    for i in range(n):
        x1_i, y1_i, x2_i, y2_i = endpoints[i]
        if is_degenerate_segment(x1_i, y1_i, x2_i, y2_i, tol):
            continue
        for j in range(i + 1, n):
            x1_j, y1_j, x2_j, y2_j = endpoints[j]
            if is_degenerate_segment(x1_j, y1_j, x2_j, y2_j, tol):
                continue

            # 非平行相交
            result = segment_intersection(
                (x1_i, y1_i), (x2_i, y2_i),
                (x1_j, y1_j), (x2_j, y2_j),
                tol,
            )
            if result is not None:
                intersections.append(
                    TraceIntersection(
                        trace_a=i,
                        trace_b=j,
                        x=result.px,
                        y=result.py,
                        t=result.t,
                        u=result.u,
                        kind=result.kind,
                    )
                )
                candidates.append(
                    _Candidate(
                        x=result.px,
                        y=result.py,
                        trace_idx=i,
                        event_type="intersection",
                        param=result.t,
                        partner_trace=j,
                    )
                )
                candidates.append(
                    _Candidate(
                        x=result.px,
                        y=result.py,
                        trace_idx=j,
                        event_type="intersection",
                        param=result.u,
                        partner_trace=i,
                    )
                )
            else:
                # 检查共线重叠
                ov_pts = collinear_overlap(
                    (x1_i, y1_i), (x2_i, y2_i),
                    (x1_j, y1_j), (x2_j, y2_j),
                    tol,
                )
                for k, (px, py) in enumerate(ov_pts):
                    candidates.append(
                        _Candidate(
                            x=px,
                            y=py,
                            trace_idx=i,
                            event_type="overlap",
                            param=0.0,  # 重叠边界点参数暂记为 0
                            partner_trace=j,
                        )
                    )
                    candidates.append(
                        _Candidate(
                            x=px,
                            y=py,
                            trace_idx=j,
                            event_type="overlap",
                            param=0.0,
                            partner_trace=i,
                        )
                    )
                if len(ov_pts) == 2:
                    intersections.append(
                        TraceIntersection(
                            trace_a=i,
                            trace_b=j,
                            x=(ov_pts[0][0] + ov_pts[1][0]) / 2.0,
                            y=(ov_pts[0][1] + ov_pts[1][1]) / 2.0,
                            t=0.5,
                            u=0.5,
                            kind="overlap",
                        )
                    )

    # 3. 聚类合并候选点
    clusters = _merge_candidates(candidates, tol)

    nodes: list[TraceNode] = []
    for node_id, cluster in enumerate(clusters):
        cx = float(np.mean([c.x for c in cluster]))
        cy = float(np.mean([c.y for c in cluster]))

        trace_set: set[int] = set()
        has_endpoint = False
        has_intersection = False
        has_overlap = False
        event_count = len(cluster)

        for cand in cluster:
            trace_set.add(cand.trace_idx)
            if cand.event_type == "endpoint":
                has_endpoint = True
            elif cand.event_type == "intersection":
                has_intersection = True
            elif cand.event_type == "overlap":
                has_overlap = True

        degree = len(trace_set)
        node_type = _classify_node_type(degree, has_endpoint, has_intersection, has_overlap)

        nodes.append(
            TraceNode(
                node_id=node_id,
                x=cx,
                y=cy,
                node_type=node_type,
                degree=degree,
                trace_indices=tuple(sorted(trace_set)),
                event_count=event_count,
                is_endpoint=has_endpoint,
                is_intersection=has_intersection,
                is_overlap=has_overlap,
            )
        )

    if degenerate_count > 0:
        warnings_list.append(f"跳过 {degenerate_count} 条退化线段（长度 < {tol}）")

    return NodeAnalysis(
        nodes=tuple(nodes),
        intersections=tuple(intersections),
        warnings=tuple(warnings_list),
        degenerate_skipped=degenerate_count,
    )
