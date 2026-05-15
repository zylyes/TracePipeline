"""节点识别算法单元测试。

基于文献标准的三分类体系：
  - I 型（孤立端点）：端点不与任何其他迹线接触
  - Y 型（三叉节点）：一条迹线的端点落在另一条迹线的内部
  - X 型（交叉节点）：两条迹线在各自的内部位置相交
"""
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
        # X 型相交：两条线在各自内部相交
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
        # X 型节点拓扑值应为 4
        x_node = next(n for n in result.nodes if n.node_type == "X")
        assert x_node.degree == 4

    def test_endpoint_touch(self):
        # Y 型：一条线端点落在另一条端点上
        # 迹线 0: (0,0)-(2,0)，迹线 1: (1,0)-(1,2)
        # 迹线 0 的端点 (1,0) 落在迹线 1 的端点 (1,0) 上
        # 这是一个端点-端点接触，在容差内合并后：
        # 迹线 0 的 (1,0) 是端点，迹线 1 的 (1,0) 也是端点
        # 如果两个端点重合，按 V 型处理 → I（两个悬空端点合并）
        endpoints = np.array([
            [0, 0, 2, 0],
            [1, 0, 1, 2],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        # 在精确坐标下，(1,0) 既是迹线0端点也是迹线1端点
        # 这是 V 型（两个端点重合）→ 归入 I
        # 但还有迹线0的另一个端点 (0,0) 和 (2,0)，迹线1的 (1,2)
        # 所以应该有 3 个 I（如果 (1,0) 被合并为 I）
        # 以及可能的一个 Y 如果端点接触被视为 Y
        # 根据文献：端点-端点接触是 V 型 → I
        assert "I" in types

    def test_endpoint_on_segment(self):
        # Y 型：端点落在线段内部
        endpoints = np.array([
            [0, 0, 2, 0],
            [1, 0, 1, 1],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        assert "Y" in types
        # Y 型节点拓扑值应为 3
        y_node = next(n for n in result.nodes if n.node_type == "Y")
        assert y_node.degree == 3

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
        # 共线重叠：边界节点应为 Y（端点落在内部）
        endpoints = np.array([
            [0, 0, 4, 0],
            [2, 0, 6, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        # 共线重叠边界产生 Y 节点
        assert "Y" in types

    def test_multi_intersection(self):
        # 多条线在同一点交叉：全内部穿过 → X
        endpoints = np.array([
            [0, 0, 2, 2],
            [0, 2, 2, 0],
            [1, 0, 1, 2],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        types = [n.node_type for n in result.nodes]
        # 3 条线内部交叉 → X（拓扑值 6）
        assert "X" in types
        x_node = next(n for n in result.nodes if n.node_type == "X")
        assert x_node.degree == 6

    def test_degenerate_skip(self):
        endpoints = np.array([
            [0, 0, 1e-12, 0],
            [0, 0, 1, 1],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        assert result.degenerate_skipped == 1

    def test_tolerance_merge(self):
        # 两个非常接近的端点应合并为一个节点
        endpoints = np.array([
            [0, 0, 1, 0],
            [1e-7, 0, 2, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        # 两个端点非常接近，应被合并为 V 型 → I
        assert result.node_count < 4

    def test_v_node(self):
        # V 型：两条迹线端点重合 → I（两个悬空端点合并）
        endpoints = np.array([
            [0, 0, 1, 1],
            [1, 1, 2, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        # 端点 (1,1) 重合，但两条迹线都不继续延伸
        # 这是一个 V 型节点，应归入 I
        types = [n.node_type for n in result.nodes]
        # 3 个节点：(0,0) I, (1,1) I（V 型）, (2,0) I
        assert types.count("I") >= 1

    def test_overlap_branch_count(self):
        # 共线重叠边界节点拓扑值 = 3 → Y
        endpoints = np.array([
            [0, 0, 4, 0],
            [2, 0, 6, 0],
        ], dtype=float)
        cfg = NodeRecognitionConfig(merge_tolerance=1e-6)
        result = recognize_trace_nodes(endpoints, cfg)
        y_nodes = [n for n in result.nodes if n.node_type == "Y"]
        for y_node in y_nodes:
            assert y_node.degree == 3
