"""节点识别主算法。

基于迹线端点坐标，按文献标准识别三种节点类型：
  - I 型（孤立端点）：端点不与任何其他迹线接触
  - Y 型（三叉节点）：一条迹线的端点落在另一条迹线的内部
  - X 型（交叉节点）：两条迹线在各自的内部位置相交
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..geometry.segments import (
    collinear_overlap,
    cross2d,
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
    event_type: str  # "I" | "Y" | "X"
    param: float = 0.0  # 在线段上的参数 [0,1]


def _point_on_segment_interior(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
    tol: float,
) -> bool:
    """判断点是否落在线段内部（不包括端点邻域），且垂距在容差内。"""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return False
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    if not (tol < t < 1.0 - tol):
        return False
    # 检查垂距
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    dist_sq = (px - proj_x) ** 2 + (py - proj_y) ** 2
    return dist_sq <= tol * tol


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


def _compute_topological_value(cluster: list[_Candidate], tol: float) -> int:
    """按 trace_idx 分组计算拓扑值（分支数）。

    规则：
    - 迹线在节点上有内部 candidate（0 < param < 1）→ 2 分支
    - 迹线在节点上只有端点 candidate（param ≈ 0 或 1）：
      - 该迹线在节点上有 ≥2 个不同端点 candidate → 2 分支（V 型环）
      - 否则 → 1 分支
    """
    trace_params: dict[int, list[float]] = defaultdict(list)
    for cand in cluster:
        trace_params[cand.trace_idx].append(cand.param)

    tv = 0
    for params in trace_params.values():
        # 容差范围内去重（避免重复候选导致误判）
        unique_params: list[float] = []
        for p in params:
            if not any(abs(p - up) <= tol for up in unique_params):
                unique_params.append(p)

        has_internal = any(tol < p < 1.0 - tol for p in unique_params)
        if has_internal:
            tv += 2
        else:
            # 只有端点
            n_endpoints = sum(1 for p in unique_params if p <= tol or p >= 1.0 - tol)
            tv += 2 if n_endpoints >= 2 else 1
    return tv


def _classify_merged_node(cluster: list[_Candidate], tol: float) -> str:
    """合并后节点类型判定。

    真正的 X 型：至少两条迹线在内部交叉（各有内部 X 候选）。
    Y 型：存在端点落在其他迹线内部，或拓扑值≥3（多条端点重合）。
    I 型：其他情况（孤立端点或 V 型）。
    """
    # 统计有内部 X 事件的迹线（param 在 (0,1) 内）
    x_internal_traces: set[int] = set()
    for c in cluster:
        if c.event_type == "X" and tol < c.param < 1.0 - tol:
            x_internal_traces.add(c.trace_idx)
    if len(x_internal_traces) >= 2:
        return "X"

    event_types = {c.event_type for c in cluster}
    if "Y" in event_types:
        return "Y"

    # 多条端点重合（拓扑值≥3）→ Y
    tv = _compute_topological_value(cluster, tol)
    if tv >= 3:
        return "Y"

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

    # 预计算每条线段的中心点和最大半长，用于空间索引加速
    centers = np.empty((n, 2), dtype=float)
    half_lens = np.empty(n, dtype=float)
    valid_mask = np.ones(n, dtype=bool)
    for i in range(n):
        x1, y1, x2, y2 = endpoints[i]
        if is_degenerate_segment(x1, y1, x2, y2, tol):
            degenerate_count += 1
            valid_mask[i] = False
            continue
        centers[i, 0] = (x1 + x2) * 0.5
        centers[i, 1] = (y1 + y2) * 0.5
        half_lens[i] = 0.5 * np.hypot(x2 - x1, y2 - y1)

    # 使用 cKDTree 进行空间索引加速（仅当 n > 20 时启用，避免小数据量下的额外开销）
    use_spatial_index = n > 20
    if use_spatial_index:
        from scipy.spatial import cKDTree
        tree = cKDTree(centers)

    def _nearby_indices(idx: int) -> list[int]:
        """返回可能与迹线 idx 发生交互的邻近迹线索引。"""
        if not use_spatial_index:
            return list(range(n))
        # 查询距离在 (half_len_i + max_half_len + tol * 2) 范围内的候选
        search_radius = half_lens[idx] + half_lens.max() + tol * 2.0
        raw = tree.query_ball_point(centers[idx], r=float(search_radius))
        # 排除自身和退化线段
        return [j for j in raw if j != idx and valid_mask[j]]

    # 1. 端点分析：遍历每条迹线的两个端点
    for i in range(n):
        if not valid_mask[i]:
            continue
        x1, y1, x2, y2 = endpoints[i]

        for end, (px, py) in enumerate(((x1, y1), (x2, y2))):
            param = float(end)  # 0 或 1
            is_y = False
            for j in _nearby_indices(i):
                if j == i:
                    continue
                x1_j, y1_j, x2_j, y2_j = endpoints[j]
                if not valid_mask[j]:
                    continue
                if _point_on_segment_interior(px, py, x1_j, y1_j, x2_j, y2_j, tol):
                    # 检查是否共线：共线情况由 collinear_overlap 统一处理，避免重复候选
                    dx_i = x2 - x1
                    dy_i = y2 - y1
                    dx_j = x2_j - x1_j
                    dy_j = y2_j - y1_j
                    if abs(cross2d(dx_i, dy_i, dx_j, dy_j)) < tol:
                        continue  # 共线重叠由 collinear_overlap 处理
                    # 端点 i 落在迹线 j 的内部 → Y
                    candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="Y", param=param))
                    # 迹线 j 在该点被穿过（内部），贡献 2 分支
                    if dx_j != 0.0 or dy_j != 0.0:
                        t_j = ((px - x1_j) * dx_j + (py - y1_j) * dy_j) / (dx_j * dx_j + dy_j * dy_j)
                        candidates.append(_Candidate(x=px, y=py, trace_idx=j, event_type="X", param=t_j))
                    is_y = True
                    break
            if not is_y:
                # 端点悬空 → I
                candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="I", param=param))

    # 2. 内部相交分析：两两迹线在各自内部相交 → X
    for i in range(n):
        if not valid_mask[i]:
            continue
        x1_i, y1_i, x2_i, y2_i = endpoints[i]
        nearby = _nearby_indices(i)
        for j in nearby:
            if j <= i:
                continue
            if not valid_mask[j]:
                continue
            x1_j, y1_j, x2_j, y2_j = endpoints[j]

            result = segment_intersection(
                (x1_i, y1_i), (x2_i, y2_i),
                (x1_j, y1_j), (x2_j, y2_j),
                tol,
            )
            if result is not None and result.kind == "internal":
                intersections.append(
                    TraceIntersection(
                        trace_a=i,
                        trace_b=j,
                        x=result.px,
                        y=result.py,
                        t=result.t,
                        u=result.u,
                        kind="internal",
                    )
                )
                candidates.append(
                    _Candidate(x=result.px, y=result.py, trace_idx=i, event_type="X", param=result.t)
                )
                candidates.append(
                    _Candidate(x=result.px, y=result.py, trace_idx=j, event_type="X", param=result.u)
                )
            else:
                # 共线重叠：边界节点可能是 Y 或 I（V 型）
                ov_result = collinear_overlap(
                    (x1_i, y1_i), (x2_i, y2_i),
                    (x1_j, y1_j), (x2_j, y2_j),
                    tol,
                )
                for (px, py), t_a, t_b in ov_result:
                    is_endpoint_a = t_a <= tol or t_a >= 1.0 - tol
                    is_endpoint_b = t_b <= tol or t_b >= 1.0 - tol
                    if is_endpoint_a and not is_endpoint_b:
                        # A 的端点落在 B 内部 → Y（A 贡献 1 分支，B 贡献 2 分支）
                        candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="Y", param=t_a))
                        candidates.append(_Candidate(x=px, y=py, trace_idx=j, event_type="X", param=t_b))
                    elif is_endpoint_b and not is_endpoint_a:
                        # B 的端点落在 A 内部 → Y（B 贡献 1 分支，A 贡献 2 分支）
                        candidates.append(_Candidate(x=px, y=py, trace_idx=j, event_type="Y", param=t_b))
                        candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="X", param=t_a))
                    elif is_endpoint_a and is_endpoint_b:
                        # 两端点重合（V 型）→ I（两个悬空端点合并，各贡献 1 分支）
                        candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="I", param=t_a))
                        candidates.append(_Candidate(x=px, y=py, trace_idx=j, event_type="I", param=t_b))
                    else:
                        # 内部点重合（理论上不应发生，因为共线重叠边界只会在端点处）
                        # 按 X 处理（各贡献 2 分支）
                        candidates.append(_Candidate(x=px, y=py, trace_idx=i, event_type="X", param=t_a))
                        candidates.append(_Candidate(x=px, y=py, trace_idx=j, event_type="X", param=t_b))

    # 3. 聚类合并候选点
    clusters = _merge_candidates(candidates, tol)

    nodes: list[TraceNode] = []
    for node_id, cluster in enumerate(clusters):
        cx = float(np.mean([c.x for c in cluster]))
        cy = float(np.mean([c.y for c in cluster]))

        trace_set: set[int] = {c.trace_idx for c in cluster}
        node_type = _classify_merged_node(cluster, tol)
        tv = _compute_topological_value(cluster, tol)

        nodes.append(
            TraceNode(
                node_id=node_id,
                x=cx,
                y=cy,
                node_type=node_type,
                degree=tv,
                trace_indices=tuple(sorted(trace_set)),
                event_count=len(cluster),
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
