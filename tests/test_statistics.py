"""单元测试 — statistics.py 统计指标计算流水线。"""

from __future__ import annotations

import math

import numpy as np
import pytest

from trace_pipeline.geology._circle_window import (
    _classify_trace_types,
    _count_circle_windows_batch,
)
from trace_pipeline.geology._convex_hull import (
    _compute_convex_hull,
    _convex_hull_area,
)
from trace_pipeline.geology._stat_types import (
    TraceStatisticsConfig,
)
from trace_pipeline.geology._window_scoring import _select_window_diagnostics
from trace_pipeline.geology.statistics import (
    _adaptive_consistency_threshold,
    _adaptive_disagreement_threshold,
    _effective_scanline_length,
    _estimate_scanline_length,
    compute_trace_statistics,
)
from trace_pipeline.models import TraceData

# ── Fixtures ───────────────────────────────────────────────────────────


def _make_trace(
    endpoints: np.ndarray,
    azimuth: float = 298.0,
    segment_lengths: np.ndarray | None = None,
    scanline_positions: np.ndarray | None = None,
    measured_length: float | None = None,
    measured_area: float | None = None,
) -> TraceData:
    n = endpoints.shape[0]
    if segment_lengths is None:
        segment_lengths = np.ones(n, dtype=float)
    if scanline_positions is None:
        scanline_positions = np.linspace(0, 10, n, dtype=float)
    joint_strikes = np.full(n, azimuth - 270.0, dtype=float)
    return TraceData(
        scanline_azimuth=azimuth,
        count=n,
        endpoints=endpoints,
        joint_strikes=joint_strikes,
        segment_lengths=segment_lengths,
        scanline_positions=scanline_positions,
        measured_scanline_length=measured_length,
        measured_outcrop_area=measured_area,
    )


# ── 测线长度估算 ────────────────────────────────────────────────────


class TestScanlineLength:
    def test_estimate_from_positions(self) -> None:
        positions = np.array([0.5, 1.0, 2.0, 4.0])
        length = _estimate_scanline_length(positions)
        assert length > 0
        assert length == pytest.approx(4.0 + 0.5 * 1.0)

    def test_estimate_empty_returns_zero(self) -> None:
        assert _estimate_scanline_length(np.array([])) == 0.0

    def test_estimate_nan_raises(self) -> None:
        with pytest.raises(ValueError, match="NaN"):
            _estimate_scanline_length(np.array([1.0, np.nan, 3.0]))

    def test_measured_preferred(self) -> None:
        trace = _make_trace(
            np.array([[0, 0, 1, 1]]),
            scanline_positions=np.array([0.5]),
            measured_length=100.0,
        )
        length, source = _effective_scanline_length(trace)
        assert length == 100.0
        assert source == "measured"

    def test_estimated_fallback(self) -> None:
        trace = _make_trace(
            np.array([[0, 0, 1, 1], [0, 0, 2, 2]]),
            scanline_positions=np.array([0.5, 1.5]),
        )
        length, source = _effective_scanline_length(trace)
        assert length > 0
        assert source == "estimated"


# ── 自适应阈值 ──────────────────────────────────────────────────────


class TestAdaptiveThresholds:
    def test_disagreement_decays_with_count(self) -> None:
        t0 = _adaptive_disagreement_threshold(0)
        t100 = _adaptive_disagreement_threshold(100)
        assert t0 > t100
        assert 0.30 <= t0 <= 0.50

    def test_consistency_decays_with_count(self) -> None:
        t0 = _adaptive_consistency_threshold(0)
        t100 = _adaptive_consistency_threshold(100)
        assert t0 > t100


# ── 迹线 I/II/III 分型 ─────────────────────────────────────────────


class TestTraceTypeClassification:
    def test_type_i_crossing_scanline(self) -> None:
        segs = np.array([[-1, 1, 1, -1]], dtype=float)  # crosses origin→L scanline
        types = _classify_trace_types(segs, 5.0)
        assert types[0] == "I"

    def test_type_ii_line_intersection(self) -> None:
        """迹线延长线与测线延长线相交但迹线本体不穿测线 → II 型。"""
        segs = np.array([[10, 10, 20, 20]], dtype=float)
        types = _classify_trace_types(segs, 5.0)
        assert types[0] == "II"

    def test_type_iii_parallel_non_crossing(self) -> None:
        """平行于测线且不在同一水平面上 → III 型。"""
        segs = np.array([[2, 1, 3, 1]], dtype=float)
        types = _classify_trace_types(segs, 5.0)
        assert types[0] == "III"

    def test_empty_returns_empty(self) -> None:
        types = _classify_trace_types(np.empty((0, 4)), 5.0)
        assert types == ()


# ── 圆窗计数 ────────────────────────────────────────────────────────


class TestCircleWindowBatch:
    def test_single_window_intersections(self) -> None:
        """线段一端在圆窗内 → 有效窗口。"""
        segs = np.array([[1.5, 0.0, 3.0, 0.0]], dtype=float)
        centers = np.array([[2.0, 0.5]], dtype=float)
        radii = np.array([1.0], dtype=float)
        results = _count_circle_windows_batch(
            segs,
            centers,
            radii,
            min_intersections=1,
            cut_positions=np.array([2.0]),
            sides=["center"],
            strategies=["tangent"],
            group_keys=["g1"],
        )
        assert len(results) == 1
        r = results[0]
        assert r.valid
        assert r.intersection_count >= 1

    def test_window_no_intersections_invalid(self) -> None:
        segs = np.array([[0.0, 0.0, 4.0, 0.0]], dtype=float)
        centers = np.array([[100.0, 100.0]], dtype=float)  # far away
        radii = np.array([1.0], dtype=float)
        results = _count_circle_windows_batch(
            segs,
            centers,
            radii,
            min_intersections=1,
            cut_positions=np.array([2.0]),
            sides=["center"],
            strategies=["tangent"],
            group_keys=["g1"],
        )
        assert results[0].intersection_count == 0

    def test_empty_segments_returns_invalid_windows(self) -> None:
        results = _count_circle_windows_batch(
            np.empty((0, 4)),
            np.array([[0.0, 0.0]]),
            np.array([1.0]),
            min_intersections=1,
            cut_positions=np.array([0.0]),
            sides=["center"],
            strategies=["tangent"],
            group_keys=["g1"],
        )
        assert len(results) == 1
        assert not results[0].valid


# ── 凸包 ───────────────────────────────────────────────────────────


class TestConvexHull:
    def test_rectangle_hull_area(self) -> None:
        segs = np.array([[0, 0, 1, 0], [1, 0, 1, 1], [1, 1, 0, 1], [0, 1, 0, 0]], dtype=float)
        area = _convex_hull_area(segs)
        assert area == pytest.approx(1.0, rel=1e-3)

    def test_hull_vertices_count(self) -> None:
        segs = np.array([[0, 0, 1, 0], [0, 0, 0, 1], [1, 0, 1, 1]], dtype=float)
        verts = _compute_convex_hull(segs)
        assert verts is not None
        assert verts.shape[0] >= 3


# ── 策略选择 ────────────────────────────────────────────────────────


class TestWindowStrategySelection:
    def test_tangent_strategy_is_deterministic(self) -> None:
        segs = np.array([[0, 0, 3, 0], [0, 1, 3, 1], [0, 2, 3, 2]], dtype=float)
        config = TraceStatisticsConfig(window_strategy="tangent")
        strategy, diagnostics = _select_window_diagnostics(
            segs,
            scanline_length=5.0,
            trace_count=3,
            config=config,
            hull_area=6.0,
        )
        assert strategy == "tangent"
        assert len(diagnostics) > 0

    def test_concentric_strategy(self) -> None:
        segs = np.array([[0, 0, 3, 0], [0, 1, 3, 1], [0, 2, 3, 2]], dtype=float)
        config = TraceStatisticsConfig(window_strategy="concentric")
        strategy, diagnostics = _select_window_diagnostics(
            segs,
            scanline_length=5.0,
            trace_count=3,
            config=config,
            hull_area=6.0,
        )
        assert strategy == "concentric"

    def test_auto_strategy_returns_valid(self) -> None:
        segs = np.array([[0, 0, 3, 0], [0, 1, 3, 1], [0, 2, 3, 2]], dtype=float)
        config = TraceStatisticsConfig(window_strategy="auto")
        strategy, diagnostics = _select_window_diagnostics(
            segs,
            scanline_length=5.0,
            trace_count=3,
            config=config,
            hull_area=6.0,
        )
        assert strategy in ("tangent", "hybrid", "concentric")
        assert len(diagnostics) > 0


# ── 主统计入口 ──────────────────────────────────────────────────────


class TestComputeTraceStatistics:
    def test_basic_computation(self) -> None:
        trace = _make_trace(
            endpoints=np.array([[0, 0, 3, 2], [1, 0, 4, 2], [2, 0, 5, 2]], dtype=float),
            measured_length=5.0,
            measured_area=10.0,
        )
        stats = compute_trace_statistics(trace)
        assert stats.total_count == 3
        assert math.isfinite(stats.p10)
        assert math.isfinite(stats.p20)
        assert stats.outcrop_area_source == "measured"

    def test_no_measured_area_falls_back(self) -> None:
        trace = _make_trace(
            endpoints=np.array([[0, 0, 3, 2], [1, 0, 4, 2], [2, 0, 5, 2]], dtype=float),
            measured_length=5.0,
        )
        stats = compute_trace_statistics(trace)
        assert stats.total_count == 3
        assert stats.outcrop_area_source != "measured"

    def test_config_defaults(self) -> None:
        trace = _make_trace(np.array([[0, 0, 1, 1]]))
        stats = compute_trace_statistics(trace, TraceStatisticsConfig())
        assert stats.total_count == 1

    def test_custom_window_strategy(self) -> None:
        trace = _make_trace(
            endpoints=np.array([[0, 0, 3, 2], [1, 0, 4, 2], [2, 0, 5, 2]], dtype=float),
            measured_length=5.0,
            measured_area=10.0,
        )
        config = TraceStatisticsConfig(window_strategy="tangent")
        stats = compute_trace_statistics(trace, config)
        assert stats.window_strategy == "tangent"
