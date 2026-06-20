"""节点识别主算法。

基于直线交点检测算法，按几何接触关系识别三种节点类型：
  - I 型（孤立端点）：端点不与任何其他迹线接触
  - Y 型（三叉节点）：一条迹线的端点落在另一条迹线的内部（端-中接触）
  - X 型（交叉节点）：两条迹线在各自内部位置相交（中-中接触）

算法流程：
  1. 预处理：计算迹线包围盒，过滤不可能相交的迹线对
  2. 相交检测：对候选迹线对调用 segment_intersection，分类 X/Y/端-端事件
  3. 端点处理：收集未使用端点，检测接近的端点对
  4. 聚类合并：对候选点进行空间聚类
  5. 节点分类：根据簇内迹线参与方式确定类型与分支数

性能优化：
  - NumPy 向量化包围盒筛选
  - 批量处理候选点聚类
  - 预计算数据结构减少重复计算
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from ..geometry.segments import segment_intersection
from .models import NodeAnalysis, NodeRecognitionConfig, TraceIntersection, TraceNode

logger = logging.getLogger(__name__)

__all__ = ["recognize_trace_nodes"]


@dataclass(frozen=True, slots=True)
class _Candidate:
    """几何事件候选点。"""

    x: float
    y: float
    trace_idx: int
    param: float


def _is_interior(param: float, tol: float) -> bool:
    """判断参数是否位于线段内部（不含端点邻域）。"""
    return tol < param < 1.0 - tol


class _UnionFind:
    """并查集，用于传递性聚类合并。"""

    __slots__ = ("parent", "rank")

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def _merge_candidates(
    candidates: list[_Candidate],
    tolerance: float,
) -> list[list[_Candidate]]:
    """基于空间网格 + 并查集的候选点聚类。"""
    if not candidates:
        return []

    m = len(candidates)
    cell_size = max(tolerance, 1e-12)
    tol2 = tolerance * tolerance

    # 构建网格
    grid: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, cand in enumerate(candidates):
        cell_x = int(np.floor(cand.x / cell_size))
        cell_y = int(np.floor(cand.y / cell_size))
        grid[(cell_x, cell_y)].append(idx)

    uf = _UnionFind(m)

    # 并行合并
    for i, cand in enumerate(candidates):
        cx = int(np.floor(cand.x / cell_size))
        cy = int(np.floor(cand.y / cell_size))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if j <= i:
                        continue
                    other = candidates[j]
                    dx_ = cand.x - other.x
                    dy_ = cand.y - other.y
                    if dx_ * dx_ + dy_ * dy_ <= tol2:
                        uf.union(i, j)

    groups: dict[int, list[_Candidate]] = defaultdict(list)
    for idx, cand in enumerate(candidates):
        groups[uf.find(idx)].append(cand)

    return list(groups.values())


def _compute_topological_value(trace_params: dict[int, list[float]], tol: float) -> int:
    """计算节点拓扑值：每条迹线贡献 2（内部通过）或 1-2（端点参与）。"""
    tv = 0
    for params in trace_params.values():
        unique_params: list[float] = []
        for p in params:
            if not any(abs(p - up) <= tol for up in unique_params):
                unique_params.append(p)
        if any(_is_interior(p, tol) for p in unique_params):
            tv += 2
        else:
            n_endpoints = sum(1 for p in unique_params if p <= tol or p >= 1.0 - tol)
            tv += 2 if n_endpoints >= 2 else 1
    return tv


def _classify_and_compute_node(cluster: list[_Candidate], tol: float) -> tuple[str, int]:
    """一次性计算节点类型和拓扑值。

    Returns:
        (node_type, topological_value)
    """
    trace_params: dict[int, list[float]] = defaultdict(list)
    interior_traces: set[int] = set()

    for cand in cluster:
        trace_params[cand.trace_idx].append(cand.param)
        if _is_interior(cand.param, tol):
            interior_traces.add(cand.trace_idx)

    tv = _compute_topological_value(trace_params, tol)

    if len(interior_traces) >= 2:
        return "X", tv
    if len(interior_traces) == 1 or tv >= 3:
        return "Y", tv
    return "I", tv


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
        return NodeAnalysis(
            nodes=(),
            intersections=(),
            warnings=(),
            degenerate_skipped=0,
            merge_tolerance=config.merge_tolerance,
        )

    n = endpoints.shape[0]
    tol = config.merge_tolerance

    # 聚类容差
    lengths = np.hypot(endpoints[:, 2] - endpoints[:, 0], endpoints[:, 3] - endpoints[:, 1])
    mean_len = float(np.mean(lengths)) if lengths.size > 0 else 0.0
    cluster_tol = max(tol, 0.01 * mean_len)

    logger.debug(
        "节点识别容差: 几何检测=%.6f, 聚类合并=%.6f (mean_len=%.2f)",
        tol,
        cluster_tol,
        mean_len,
    )

    candidates: list[_Candidate] = []
    intersections: list[TraceIntersection] = []
    warnings_list: list[str] = []
    degenerate_count = 0

    # ------------------------------------------------------------------
    # 预处理：计算迹线元数据
    # ------------------------------------------------------------------
    x1 = endpoints[:, 0]
    y1 = endpoints[:, 1]
    x2 = endpoints[:, 2]
    y2 = endpoints[:, 3]

    # 退化线段检测
    half_lens = 0.5 * lengths
    valid_mask = lengths > tol

    degenerate_count = int(np.sum(~valid_mask))
    valid_indices = np.where(valid_mask)[0]

    if len(valid_indices) == 0:
        return NodeAnalysis(
            nodes=(),
            intersections=(),
            warnings=(f"跳过 {degenerate_count} 条退化线段",),
            degenerate_skipped=degenerate_count,
            merge_tolerance=config.merge_tolerance,
        )

    # 预计算有效迹线的数据
    n_valid = len(valid_indices)
    valid_x1 = x1[valid_indices]
    valid_y1 = y1[valid_indices]
    valid_x2 = x2[valid_indices]
    valid_y2 = y2[valid_indices]
    valid_half_lens = half_lens[valid_indices]

    # 预计算有效迹线的 AABB 包围盒
    valid_bbox = np.column_stack(
        (
            np.minimum(valid_x1, valid_x2),
            np.minimum(valid_y1, valid_y2),
            np.maximum(valid_x1, valid_x2),
            np.maximum(valid_y1, valid_y2),
        )
    )

    # 全局包围盒扩展（用于过滤）
    max_half_len = float(np.max(valid_half_lens))
    bbox_margin = max(tol, max_half_len * 0.5)

    # ------------------------------------------------------------------
    # Phase 1: 高效迹线对筛选 + 相交检测
    # ------------------------------------------------------------------
    used_endpoints: set[tuple[int, int]] = set()

    # 对每条迹线，找出候选邻居（包围盒可能重叠）
    for idx_in_valid in range(n_valid):
        i = valid_indices[idx_in_valid]

        # 向量化筛选：在包围盒内且索引更大的迹线
        bbox_i = valid_bbox[idx_in_valid]
        x_min_i, y_min_i = bbox_i[0] - bbox_margin, bbox_i[1] - bbox_margin
        x_max_i, y_max_i = bbox_i[2] + bbox_margin, bbox_i[3] + bbox_margin

        # 快速包围盒过滤
        candidate_mask = (
            (valid_bbox[:, 0] <= x_max_i)  # bbox_j.x_min <= bbox_i.x_max
            & (valid_bbox[:, 2] >= x_min_i)  # bbox_j.x_max >= bbox_i.x_min
            & (valid_bbox[:, 1] <= y_max_i)  # bbox_j.y_min <= bbox_i.y_max
            & (valid_bbox[:, 3] >= y_min_i)  # bbox_j.y_max >= bbox_i.y_min
        )

        # 只处理索引更大的迹线
        candidate_indices = np.where(candidate_mask)[0]
        candidate_indices = candidate_indices[candidate_indices > idx_in_valid]

        if candidate_indices.size == 0:
            continue

        x1_i, y1_i = valid_x1[idx_in_valid], valid_y1[idx_in_valid]
        x2_i, y2_i = valid_x2[idx_in_valid], valid_y2[idx_in_valid]

        for idx_j in candidate_indices:
            j = valid_indices[idx_j]

            # 精确相交检测
            result = segment_intersection(
                (x1_i, y1_i),
                (x2_i, y2_i),
                (valid_x1[idx_j], valid_y1[idx_j]),
                (valid_x2[idx_j], valid_y2[idx_j]),
                tol,
            )
            if result is None:
                continue

            t, u, px, py = result.t, result.u, result.px, result.py
            t_is_interior = _is_interior(t, tol)
            u_is_interior = _is_interior(u, tol)
            t_end = 0 if t <= 0.5 else 1
            u_end = 0 if u <= 0.5 else 1

            if t_is_interior and u_is_interior:
                # X 型
                candidates.append(_Candidate(x=px, y=py, trace_idx=i, param=t))
                candidates.append(_Candidate(x=px, y=py, trace_idx=j, param=u))
                intersections.append(
                    TraceIntersection(trace_a=i, trace_b=j, x=px, y=py, t=t, u=u, kind="internal")
                )
            elif not t_is_interior and u_is_interior:
                # Y 型：迹线 i 的端点落在迹线 j 内部
                candidates.append(_Candidate(x=px, y=py, trace_idx=i, param=t))
                candidates.append(_Candidate(x=px, y=py, trace_idx=j, param=u))
                used_endpoints.add((i, t_end))
            elif t_is_interior and not u_is_interior:
                # Y 型：迹线 j 的端点落在迹线 i 内部
                candidates.append(_Candidate(x=px, y=py, trace_idx=i, param=t))
                candidates.append(_Candidate(x=px, y=py, trace_idx=j, param=u))
                used_endpoints.add((j, u_end))
            else:
                # 端-端接触
                candidates.append(_Candidate(x=px, y=py, trace_idx=i, param=t))
                candidates.append(_Candidate(x=px, y=py, trace_idx=j, param=u))
                used_endpoints.add((i, t_end))
                used_endpoints.add((j, u_end))

    # ------------------------------------------------------------------
    # Phase 2: 端点接近检测（向量化）
    # ------------------------------------------------------------------
    # 收集未使用端点
    unused_endpoints: list[tuple[int, int, float, float]] = []
    for i in range(n):
        if not valid_mask[i]:
            continue
        for end_idx, (px, py) in enumerate(((x1[i], y1[i]), (x2[i], y2[i]))):
            if (i, end_idx) not in used_endpoints:
                unused_endpoints.append((i, end_idx, px, py))

    if unused_endpoints:
        # 提取端点坐标用于网格分桶
        endpoint_coords = np.array(
            [(px, py) for _, _, px, py in unused_endpoints], dtype=np.float64
        )

        # 网格分桶
        cell_size = max(tol, 1e-12)
        # 防止极大坐标值导致 int64 溢出
        coord_max = float(np.max(np.abs(endpoint_coords))) if len(endpoint_coords) > 0 else 0.0
        if coord_max > 1e15:
            import warnings
            warnings.warn(
                f"节点识别坐标值过大 (max={coord_max:.3e})，可能导致网格索引溢出",
                stacklevel=2,
            )
        endpoint_cells = np.floor(endpoint_coords / cell_size).astype(np.int64)

        cell_to_indices: dict[tuple[int, int], list[int]] = defaultdict(list)
        for idx, (cx, cy) in enumerate(endpoint_cells):
            cell_to_indices[(int(cx), int(cy))].append(idx)

        # 接近检测
        endpoint_uf = _UnionFind(len(unused_endpoints))
        tol2 = tol * tol

        for i in range(len(unused_endpoints)):
            px, py = endpoint_coords[i]
            cx, cy = endpoint_cells[i]

            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in cell_to_indices.get((cx + dx, cy + dy), []):
                        if j <= i:
                            continue
                        qx, qy = endpoint_coords[j]
                        if (px - qx) ** 2 + (py - qy) ** 2 <= tol2:
                            endpoint_uf.union(i, j)

        # 按组生成候选
        endpoint_groups: dict[int, list[tuple[int, int, float, float]]] = defaultdict(list)
        for idx, item in enumerate(unused_endpoints):
            endpoint_groups[endpoint_uf.find(idx)].append(item)

        for group in endpoint_groups.values():
            coords = [(px, py) for _, _, px, py in group]
            avg_x = float(np.mean([c[0] for c in coords]))
            avg_y = float(np.mean([c[1] for c in coords]))
            for trace_idx, end_idx, _, _ in group:
                candidates.append(
                    _Candidate(x=avg_x, y=avg_y, trace_idx=trace_idx, param=float(end_idx))
                )
                used_endpoints.add((trace_idx, end_idx))

    # ------------------------------------------------------------------
    # Phase 3: 聚类合并
    # ------------------------------------------------------------------
    clusters = _merge_candidates(candidates, cluster_tol)

    # ------------------------------------------------------------------
    # 节点生成
    # ------------------------------------------------------------------
    nodes: list[TraceNode] = []
    for node_id, cluster in enumerate(clusters):
        cx = float(np.mean([c.x for c in cluster]))
        cy = float(np.mean([c.y for c in cluster]))
        trace_set = {c.trace_idx for c in cluster}
        node_type, tv = _classify_and_compute_node(cluster, tol)

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
        merge_tolerance=cluster_tol,
    )
