"""单元测试 — analysis/nodes.py 节点识别算法。"""

from __future__ import annotations

import numpy as np

from trace_pipeline.analysis.models import NodeRecognitionConfig
from trace_pipeline.analysis.nodes import recognize_trace_nodes


def _make_config(**kwargs) -> NodeRecognitionConfig:
    defaults = {
        "enabled": True,
        "merge_tolerance": 0.01,
        "show_overlay": True,
        "label_mode": "type",
    }
    defaults.update(kwargs)
    return NodeRecognitionConfig(**defaults)


class TestNodeRecognition:
    """节点识别回归测试 — 交叉、端点接触、退化线段等场景。"""

    def test_crossing_x_node(self) -> None:
        """两条迹线在内部交叉 → X 型节点。"""
        endpoints = np.array(
            [
                [0, 0, 4, 4],
                [0, 4, 4, 0],
            ],
            dtype=float,
        )
        result = recognize_trace_nodes(endpoints, _make_config())
        assert result.node_count >= 1

    def test_endpoint_touch_y_node(self) -> None:
        """一条迹线端点落在另一条迹线内部 → Y 型节点。"""
        endpoints = np.array(
            [
                [0, 0, 4, 0],
                [2, 0, 2, 2],
            ],
            dtype=float,
        )
        result = recognize_trace_nodes(endpoints, _make_config())
        assert result.node_count >= 1

    def test_crossing_with_later_segment_starting_left_is_detected(self) -> None:
        """索引更大的迹线可从更左侧开始，不能被 bbox 去重过滤漏掉。"""
        endpoints = np.array(
            [
                [1, 0, 3, 0],
                [0, -1, 4, 1],
            ],
            dtype=float,
        )

        result = recognize_trace_nodes(endpoints, _make_config())

        assert result.intersection_count == 1
        assert any(node.node_type == "X" for node in result.nodes)

    def test_disabled_returns_empty(self) -> None:
        endpoints = np.array([[0, 0, 1, 1], [0, 1, 1, 0]], dtype=float)
        config = _make_config(enabled=False)
        result = recognize_trace_nodes(endpoints, config)
        assert result.node_count == 0
        assert result.intersection_count == 0

    def test_empty_endpoints_returns_empty(self) -> None:
        result = recognize_trace_nodes(np.empty((0, 4)), _make_config(enabled=False))
        assert result.node_count == 0

    def test_parallel_segments_no_intersection(self) -> None:
        """两条平行不共线迹线 → 无迹线间交点，仅有孤立端点节点。"""
        endpoints = np.array(
            [
                [0, 0, 4, 0],
                [0, 2, 4, 2],
            ],
            dtype=float,
        )
        result = recognize_trace_nodes(endpoints, _make_config())
        # 终端点聚类产生 I 型节点（迹线未达到聚类阈值时的孤立端点）
        # 但不应产生 X/Y 型交点
        assert result.intersection_count == 0
        for node in result.nodes:
            assert node.node_type == "I"

    def test_collinear_overlap_node(self) -> None:
        """共线重叠迹线 → 产生节点。"""
        endpoints = np.array(
            [
                [0, 0, 3, 0],
                [2, 0, 5, 0],
            ],
            dtype=float,
        )
        result = recognize_trace_nodes(endpoints, _make_config())
        assert result.node_count >= 1

    def test_degenerate_trace_skipped(self) -> None:
        """退化线段（长度 < tolerance）→ 被跳过且产生警告。"""
        endpoints = np.array(
            [
                [0, 0, 1e-6, 1e-6],  # degenerate
                [0, 0, 4, 0],
                [2, -2, 2, 2],
            ],
            dtype=float,
        )
        config = _make_config(merge_tolerance=0.01)
        result = recognize_trace_nodes(endpoints, config)
        assert result.degenerate_skipped >= 1
        assert any("退化" in w for w in result.warnings)

    def test_node_type_counts(self) -> None:
        """统计 I/Y/X 节点数之和等于节点总数。"""
        endpoints = np.array(
            [
                [0, 0, 4, 4],
                [0, 4, 4, 0],
                [1, 1, 1, 5],
            ],
            dtype=float,
        )
        result = recognize_trace_nodes(endpoints, _make_config(merge_tolerance=0.1))
        tc = result.type_counts
        assert tc.get("I", 0) + tc.get("Y", 0) + tc.get("X", 0) == result.node_count


class TestNodeModelIntegrity:
    def test_node_analysis_properties(self) -> None:
        endpoints = np.array([[0, 0, 4, 4], [0, 4, 4, 0]], dtype=float)
        result = recognize_trace_nodes(endpoints, _make_config())
        assert result.node_count > 0
        assert result.intersection_count > 0
        assert result.merge_tolerance > 0
        # density without area should be None
        assert result.node_density(None) is None

    def test_node_density_with_area(self) -> None:
        endpoints = np.array([[0, 0, 4, 4], [0, 4, 4, 0]], dtype=float)
        result = recognize_trace_nodes(endpoints, _make_config())
        density = result.node_density(8.0)
        assert density > 0
        assert np.isfinite(density)
