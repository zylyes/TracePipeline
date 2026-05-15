"""节点识别算法单元测试。"""
from __future__ import annotations

import numpy as np

from trace_pipeline.analysis.models import NodeRecognitionConfig
from trace_pipeline.analysis.nodes import recognize_trace_nodes


class TestNodeRecognition:
    def test_empty(self):
        cfg = NodeRecognitionConfig()
        endpoints = np.array([], dtype=float).reshape(0, 4)
        result = recognize_trace_nodes(endpoints, cfg)
        assert result.node_count == 0
        assert result.intersection_count == 0

    def test_two_lines_crossing(self):
        # X 型相交
        endpoints = np.array([
            [0, 0, 2, 2],
            [0, 2, 2, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        assert result.intersection_count == 1
        types = [n.node_type for n in result.nodes]
        # 中心一个 X，四个自由端点 I
        assert "X" in types
        assert types.count("I") == 4

    def test_endpoint_touch(self):
        # T 型 / Y 型：一条线端点落在另一条端点上
        endpoints = np.array([
            [0, 0, 2, 0],
            [1, 0, 1, 2],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        assert "Y" in types or "multi" in types

    def test_endpoint_on_segment(self):
        # 端点落在线段内部 -> Y
        endpoints = np.array([
            [0, 0, 2, 0],
            [1, 0, 1, 1],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        assert "Y" in types

    def test_no_intersection(self):
        endpoints = np.array([
            [0, 0, 1, 1],
            [2, 2, 3, 3],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        assert result.intersection_count == 0
        assert result.node_count == 4
        assert all(n.node_type == "I" for n in result.nodes)

    def test_collinear_overlap(self):
        endpoints = np.array([
            [0, 0, 4, 0],
            [2, 0, 6, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        # 共线重叠会产生 overlap 节点
        assert "overlap" in types

    def test_multi_intersection(self):
        # 多条线在同一点相交
        endpoints = np.array([
            [0, 0, 2, 2],
            [0, 2, 2, 0],
            [1, 0, 1, 2],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        assert "multi" in types or "Y" in types

    def test_degenerate_skip(self):
        endpoints = np.array([
            [0, 0, 1e-12, 0],
            [0, 0, 1, 1],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        assert result.degenerate_skipped == 1

    def test_tolerance_merge(self):
        # 两个非常接近的点应合并为一个节点
        endpoints = np.array([
            [0, 0, 1, 0],
            [1e-7, 0, 2, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        # 两个端点非常接近，应被合并
        assert result.node_count < 4
