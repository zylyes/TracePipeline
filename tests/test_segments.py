"""单元测试 — geometry/segments.py 线段相交,重点覆盖退化几何。"""

from __future__ import annotations

from trace_pipeline.geometry.segments import (
    SegmentIntersection,
    segment_intersection,
)


class TestSegmentIntersection:
    """segment_intersection 的相交契约测试。

    回归重点(C1):共线分支必须返回 SegmentIntersection | None,
    绝不返回 list,否则上层节点识别会因 list 无 .t 属性而崩溃。
    """

    def test_internal_cross(self) -> None:
        """X 型:两线段内部相交。"""
        result = segment_intersection((0, 0), (2, 2), (0, 2), (2, 0))
        assert isinstance(result, SegmentIntersection)
        assert result.kind == "internal"
        assert abs(result.px - 1.0) < 1e-9
        assert abs(result.py - 1.0) < 1e-9

    def test_parallel_no_overlap(self) -> None:
        """平行不共线:无交点。"""
        result = segment_intersection((0, 0), (2, 0), (0, 1), (2, 1))
        assert result is None

    def test_collinear_overlap_returns_intersection(self) -> None:
        """共线且重叠:返回单个 SegmentIntersection(parallel_overlap),非 list。"""
        result = segment_intersection((0, 0), (2, 0), (1, 0), (3, 0))
        assert isinstance(result, SegmentIntersection)
        assert not isinstance(result, list)
        assert result.kind == "parallel_overlap"
        # 重叠区间为 [1,2],代表点为中点 1.5
        assert abs(result.px - 1.5) < 1e-9
        assert abs(result.py - 0.0) < 1e-9

    def test_collinear_no_overlap(self) -> None:
        """共线但不重叠:返回 None。"""
        result = segment_intersection((0, 0), (1, 0), (2, 0), (3, 0))
        assert result is None

    def test_endpoint_touch(self) -> None:
        """端-端接触:kind 为 endpoint。"""
        result = segment_intersection((0, 0), (1, 1), (1, 1), (2, 0))
        assert isinstance(result, SegmentIntersection)
        assert result.kind == "endpoint"

    def test_collinear_result_is_unpackable(self) -> None:
        """回归:共线结果的 .t/.u/.px/.py 可正常访问(模拟 nodes.py 解包)。"""
        result = segment_intersection((0, 0), (4, 0), (2, 0), (6, 0))
        assert result is not None
        t, u = result.t, result.u
        assert 0.0 <= t <= 1.0
        assert 0.0 <= u <= 1.0
        assert 2.0 <= result.px <= 4.0
        assert result.py == 0.0
