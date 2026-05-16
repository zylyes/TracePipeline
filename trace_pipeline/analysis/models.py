"""节点分析结果类型。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


__all__ = [
    "NodeAnalysis",
    "NodeRecognitionConfig",
    "TraceIntersection",
    "TraceNode",
]

_NODE_TYPE_LABELS: dict[str, str] = {
    "I": "孤立端点",
    "Y": "三叉节点",
    "X": "交叉节点",
}


@dataclass(frozen=True)
class NodeRecognitionConfig:
    """节点识别配置。"""

    enabled: bool = True
    merge_tolerance: float = 1e-6
    show_overlay: bool = True
    label_mode: Literal["none", "type", "id"] = "type"

    def __post_init__(self) -> None:
        if self.merge_tolerance <= 0.0:
            raise ValueError("merge_tolerance 必须大于 0")
        if self.label_mode not in ("none", "type", "id"):
            raise ValueError(f"label_mode 必须为 none/type/id 之一: {self.label_mode}")


@dataclass(frozen=True)
class TraceNode:
    """单个裂隙网络节点。"""

    node_id: int
    x: float
    y: float
    node_type: str  # I/Y/X
    degree: int  # 拓扑值（分支数）
    trace_indices: tuple[int, ...]
    event_count: int

    @property
    def type_label(self) -> str:
        """返回中文节点类型名称。"""
        return _NODE_TYPE_LABELS.get(self.node_type, self.node_type)


@dataclass(frozen=True)
class TraceIntersection:
    """两个迹线之间的相交事件。"""

    trace_a: int
    trace_b: int
    x: float
    y: float
    t: float
    u: float
    kind: str  # endpoint / internal / overlap


@dataclass(frozen=True)
class NodeAnalysis:
    """节点分析结果。"""

    nodes: tuple[TraceNode, ...]
    intersections: tuple[TraceIntersection, ...]
    warnings: tuple[str, ...]
    degenerate_skipped: int = 0
    merge_tolerance: float = 1e-6

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return counts

    @property
    def intersection_count(self) -> int:
        return len(self.intersections)

    def node_density(self, area: float | None) -> float | None:
        if area is None or area <= 0.0 or not self.nodes:
            return None
        return self.node_count / area
