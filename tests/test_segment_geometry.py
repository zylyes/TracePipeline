"""线段几何运算单元测试。"""
from __future__ import annotations

import pytest

from trace_pipeline.geometry.segments import (
    collinear_overlap,
    cross2d,
    is_degenerate_segment,
    point_segment_distance,
    segment_intersection,
)


class TestCross2d:
    def test_basic(self):
        assert cross2d(1, 0, 0, 1) == 1.0
        assert cross2d(0, 1, 1, 0) == -1.0
        assert cross2d(1, 1, 2, 2) == 0.0


class TestDegenerateSegment:
    def test_short(self):
        assert is_degenerate_segment(0, 0, 1e-12, 0, tol=1e-9)

    def test_normal(self):
        assert not is_degenerate_segment(0, 0, 1, 0, tol=1e-9)


class TestSegmentIntersection:
    def test_crossing(self):
        # 两条线内部相交
        result = segment_intersection((0, 0), (2, 2), (0, 2), (2, 0), tol=1e-9)
        assert result is not None
        assert result.kind == "internal"
        assert pytest.approx(result.px, abs=1e-9) == 1.0
        assert pytest.approx(result.py, abs=1e-9) == 1.0

    def test_endpoint_touch(self):
        # 端点接触
        result = segment_intersection((0, 0), (1, 1), (1, 1), (2, 0), tol=1e-9)
        assert result is not None
        assert result.kind == "endpoint"

    def test_no_intersection(self):
        result = segment_intersection((0, 0), (1, 1), (2, 2), (3, 0), tol=1e-9)
        assert result is None

    def test_parallel_non_collinear(self):
        result = segment_intersection((0, 0), (1, 0), (0, 1), (1, 1), tol=1e-9)
        assert result is None


class TestCollinearOverlap:
    def test_overlap(self):
        pts = collinear_overlap((0, 0), (4, 0), (2, 0), (6, 0), tol=1e-9)
        assert len(pts) == 2
        assert pytest.approx(pts[0][0], abs=1e-9) == 2.0
        assert pytest.approx(pts[1][0], abs=1e-9) == 4.0

    def test_no_overlap(self):
        pts = collinear_overlap((0, 0), (1, 0), (2, 0), (3, 0), tol=1e-9)
        assert len(pts) == 0


class TestPointSegmentDistance:
    def test_on_segment(self):
        assert point_segment_distance(0.5, 0, 0, 0, 1, 0) == pytest.approx(0.0, abs=1e-9)

    def test_off_segment(self):
        d = point_segment_distance(0.5, 1, 0, 0, 1, 0)
        assert d == pytest.approx(1.0, abs=1e-9)
