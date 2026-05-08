"""单元测试：迹线统计指标。"""
import math

import numpy as np
import pytest

import trace_pipeline.geology._window_scoring as _window_scoring_module
from tests.conftest import make_trace
from trace_pipeline.geology._convex_hull import convex_hull_area as _convex_hull_area
from trace_pipeline.geology._window_scoring import (
    select_window_diagnostics as _select_window_diagnostics,
)
from trace_pipeline.geology.statistics import (
    CircleWindowDiagnostic,
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)


def test_measured_scanline_length_outcrop_area_and_density_formulas():
    trace = make_trace(
        [
            [5.0, -1.0, 5.0, 1.0],    # I：有限段与测线相交
            [10.0, 1.0, 12.0, 3.0],   # II：延长线与测线相交
            [0.0, 2.0, 1.0, 2.0],     # III：其余记录
        ],
        [0.0, 10.0, 20.0],
        measured_scanline_length=30.0,
        measured_outcrop_area=60.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=99))
    endpoint_total = float(trace.lengths.sum())

    assert stats.scanline_length == pytest.approx(30.0)
    assert stats.scanline_length_source == "measured"
    assert stats.outcrop_area == pytest.approx(60.0)
    assert stats.outcrop_area_source == "measured"
    assert stats.trace_length_source == "endpoint"
    assert stats.trace_types == ("I", "II", "III")
    assert stats.type_i_count == 1
    assert stats.type_ii_count == 1
    assert stats.type_iii_count == 1
    assert stats.mean_trace_length == pytest.approx(endpoint_total / 3)
    assert stats.p10 == pytest.approx(3 / 30.0)
    assert stats.p20 == pytest.approx(3 / 60.0)
    assert stats.p21 == pytest.approx(endpoint_total / 60.0)
    assert stats.p20_source == "measured"
    assert stats.p21_source == "measured"


def test_outcrop_area_estimates_from_endpoint_convex_hull():
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=99))

    assert stats.scanline_length == pytest.approx(35.0)
    assert stats.scanline_length_source == "estimated"
    assert stats.outcrop_area == pytest.approx(40.0)
    assert stats.outcrop_area_source == "hull"
    assert stats.p10 == pytest.approx(4 / 35.0)
    assert stats.p20 == pytest.approx(4 / 40.0)
    assert stats.p20_source == "hull"


def test_convex_hull_area_handles_basic_shapes_and_degenerate_cases():
    rectangle = np.array([
        [0.0, 0.0, 4.0, 0.0],
        [4.0, 0.0, 4.0, 3.0],
        [4.0, 3.0, 0.0, 3.0],
    ])
    triangle = np.array([
        [0.0, 0.0, 4.0, 0.0],
        [4.0, 0.0, 0.0, 3.0],
    ])
    collinear = np.array([
        [0.0, 0.0, 1.0, 0.0],
        [2.0, 0.0, 3.0, 0.0],
    ])

    assert _convex_hull_area(rectangle) == pytest.approx(12.0)
    assert _convex_hull_area(triangle) == pytest.approx(6.0)
    assert math.isnan(_convex_hull_area(collinear))


def test_p21_uses_endpoint_length_total_over_outcrop_area():
    trace = make_trace(
        [
            [0.0, 0.0, 3.0, 4.0],
            [1.0, 0.0, 1.0, 5.0],
        ],
        [0.0, 10.0],
        measured_scanline_length=10.0,
        measured_outcrop_area=20.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=99))

    assert stats.trace_length_total == pytest.approx(10.0)
    assert stats.mean_trace_length == pytest.approx(5.0)
    assert stats.p21 == pytest.approx(10.0 / 20.0)
    assert stats.p21_source == "measured"


def test_trace_length_total_falls_back_from_endpoint_to_segment_lengths():
    trace = make_trace(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 1.0],
        ],
        [0.0, 10.0],
        segment_lengths=[4.0, 6.0],
        measured_scanline_length=10.0,
        measured_outcrop_area=20.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    assert stats.trace_length_source == "segment"
    assert stats.trace_length_total == pytest.approx(10.0)
    assert stats.mean_trace_length == pytest.approx(5.0)
    assert stats.p21 == pytest.approx(0.5)


def test_trace_length_total_falls_back_from_segments_to_window_mean():
    trace = make_trace(
        [
            [5.0, -2.0, 5.0, 2.0],
            [10.0, -2.0, 10.0, 2.0],
            [0.0, 4.0, 20.0, 4.0],
            [0.0, -4.0, 20.0, -4.0],
        ],
        [0.0, 5.0, 10.0, 15.0],
        segment_lengths=[0.0, 0.0, 0.0, 0.0],
        measured_scanline_length=20.0,
    )

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="hybrid",
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=1,
        ),
    )

    assert stats.trace_length_source == "window"
    assert stats.mean_trace_length > 0.0


def test_circle_window_counts_stay_available_for_internal_diagnostics():
    trace = make_trace(
        [
            [9.5, 2.0, 15.5, 2.0],      # N0：两端点都在圆外但线段穿圆
            [12.5, 2.0, 15.5, 2.0],     # N1：一个端点在圆内
            [12.0, 2.0, 13.0, 2.0],     # N2：两个端点都在圆内
            [100.0, 4.0, 101.0, 4.0],   # 提供侧向高度，不与圆相交
        ],
        [0.0, 10.0, 20.0, 20.0],
    )

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="hybrid",
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=1,
        ),
    )
    valid = [diagnostic for diagnostic in stats.diagnostics if diagnostic.valid]

    assert len(valid) == 1
    window = valid[0]
    assert window.side == "left"
    assert window.radius == pytest.approx(2.0)
    assert (window.n0, window.n1, window.n2) == (1, 1, 1)
    assert (window.m, window.q) == (3, 3)
    assert window.p20 == pytest.approx(3 / (8 * math.pi))
    assert window.p21 == pytest.approx(3 / 8)
    assert window.l_est == pytest.approx(math.pi)
    assert window.strategy == "hybrid"
    assert window.group_key == "hybrid:0.5:left"
    assert stats.mean_trace_length == pytest.approx(math.pi)
    assert stats.trace_length_source == "window"
    assert stats.p20 == pytest.approx(3 / (8 * math.pi))
    assert stats.p20_source == "window"
    assert stats.p21 == pytest.approx(3 / 8)
    assert stats.p21_source == "window"

    lines = format_statistics_box_lines(stats)
    joined = "\n".join(lines)
    assert "测线走向: 90.0°" in lines
    assert "圆窗策略: 混合圆窗" in lines
    assert "平均迹线长度（圆窗）" in joined
    assert "(W)" not in joined


def test_p20_measured_area_takes_priority_over_valid_window():
    trace = make_trace(
        [
            [9.5, 2.0, 15.5, 2.0],
            [12.5, 2.0, 15.5, 2.0],
            [12.0, 2.0, 13.0, 2.0],
            [100.0, 4.0, 101.0, 4.0],
        ],
        [0.0, 10.0, 20.0, 20.0],
        measured_outcrop_area=100.0,
    )

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="hybrid",
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=1,
        ),
    )

    assert stats.p20 == pytest.approx(4 / 100.0)
    assert stats.p20_source == "measured"
    assert stats.p21_source == "window"


def test_invalid_circle_windows_record_reasons_and_format_na():
    trace = make_trace([[5.0, -1.0, 5.0, 1.0]], [0.0])

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=5,
        ),
    )
    lines = format_statistics_box_lines(stats)
    joined = "\n".join(lines)

    assert stats.valid_window_count == 0
    assert all(diagnostic.reason for diagnostic in stats.diagnostics)
    assert math.isnan(stats.p20)
    assert "I/II/III型裂隙数: 0/0/1" in lines
    assert "测线长度: 0.000 $\\mathrm{m}$" in lines
    assert "露头面积: N/A" in lines
    assert "测线走向: 90.0°" in lines
    assert "面累计长度密度" in joined
    assert "体密度" not in joined
    assert "总裂隙数" not in joined


def test_explicit_window_strategy_layouts_are_recorded():
    trace = make_trace(
        [
            [1.5, 2.0, 2.5, 2.0],
            [5.5, 2.0, 6.5, 2.0],
            [9.5, 2.0, 10.5, 2.0],
            [1.5, -2.0, 2.5, -2.0],
            [5.5, -2.0, 6.5, -2.0],
            [9.5, -2.0, 10.5, -2.0],
            [0.0, 4.0, 12.0, 4.0],
            [0.0, -4.0, 12.0, -4.0],
        ],
        np.arange(8),
        measured_scanline_length=12.0,
    )

    tangent = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="tangent",
            tangent_window_count=3,
            min_intersections=1,
        ),
    )
    left_tangent = [d for d in tangent.diagnostics if d.side == "left"]
    assert tangent.window_strategy == "tangent"
    assert [d.center_x for d in left_tangent] == pytest.approx([2.0, 6.0, 10.0])
    assert all(d.radius == pytest.approx(2.0) for d in left_tangent)

    hybrid = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="hybrid",
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=1,
        ),
    )
    assert hybrid.window_strategy == "hybrid"
    assert {d.strategy for d in hybrid.diagnostics} == {"hybrid"}

    concentric = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="concentric",
            radius_fractions=(0.5,),
            min_intersections=1,
        ),
    )
    assert concentric.window_strategy == "concentric"
    assert len(concentric.diagnostics) == 1
    assert concentric.diagnostics[0].side == "center"
    assert concentric.diagnostics[0].center_x == pytest.approx(6.0)
    assert concentric.diagnostics[0].center_y == pytest.approx(0.0)
    assert concentric.diagnostics[0].radius == pytest.approx(2.0)


def test_auto_window_strategy_uses_viable_diagnostics_before_density_fallback():
    def rectangular_trace(count, width, height):
        xs = np.linspace(0.0, width, count)
        endpoints = np.column_stack((xs, np.zeros(count), xs, np.full(count, height)))
        return make_trace(
            endpoints,
            np.arange(count),
            measured_scanline_length=30.0,
        )

    sparse = compute_trace_statistics(
        rectangular_trace(2, 100.0, 10.0),
        TraceStatisticsConfig(min_intersections=5),
    )
    medium = compute_trace_statistics(
        rectangular_trace(20, 20.0, 10.0),
        TraceStatisticsConfig(min_intersections=5),
    )
    dense = compute_trace_statistics(
        rectangular_trace(20, 2.0, 1.0),
        TraceStatisticsConfig(min_intersections=5),
    )

    assert sparse.window_strategy == "tangent"
    assert medium.window_strategy == "concentric"
    assert dense.window_strategy == "concentric"


def _window(
    strategy,
    group_key,
    side,
    *,
    cut_position=15.0,
    radius=5.0,
    intersection_count=10,
    valid=True,
    l_est=5.0,
    p20=1.0,
    p21=1.0,
):
    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=cut_position,
        center_y=radius if side == "left" else -radius if side == "right" else 0.0,
        radius=radius,
        intersection_count=intersection_count,
        n0=1,
        n1=1,
        n2=1,
        m=3,
        q=3,
        p20=p20,
        p21=p21,
        l_est=l_est,
        strategy=strategy,
        group_key=group_key,
        valid=valid,
        reason="" if valid else "invalid",
    )


def test_auto_window_strategy_scores_groups_instead_of_raw_window_count(monkeypatch):
    def fake_circle_windows(_segments, _length, _config, strategy):
        if strategy == "hybrid":
            return tuple(
                _window(
                    "hybrid",
                    "hybrid:0.5:left",
                    "left",
                    radius=2.0,
                    intersection_count=20,
                )
                for _ in range(9)
            )
        if strategy == "tangent":
            return (
                _window("tangent", "tangent:left:0", "left", cut_position=5.0),
                _window("tangent", "tangent:right:0", "right", cut_position=5.0),
            )
        return (
            _window(
                "concentric",
                "concentric:center",
                "center",
                valid=False,
                intersection_count=0,
            ),
        )

    monkeypatch.setattr(_window_scoring_module, "compute_circle_windows", fake_circle_windows)

    selected, diagnostics = _select_window_diagnostics(
        np.zeros((0, 4)),
        30.0,
        20,
        TraceStatisticsConfig(min_intersections=5),
        200.0,
    )

    assert selected == "tangent"
    assert len([diagnostic for diagnostic in diagnostics if diagnostic.valid]) == 2


def test_auto_window_strategy_uses_density_preference_for_close_scores(monkeypatch):
    def fake_circle_windows(_segments, _length, _config, strategy):
        if strategy in {"tangent", "hybrid"}:
            return (
                _window(strategy, f"{strategy}:left:0", "left", cut_position=5.0),
                _window(strategy, f"{strategy}:right:0", "right", cut_position=5.0),
            )
        return (
            _window(
                "concentric",
                "concentric:center",
                "center",
                valid=False,
                intersection_count=0,
            ),
        )

    monkeypatch.setattr(_window_scoring_module, "compute_circle_windows", fake_circle_windows)

    selected, _diagnostics = _select_window_diagnostics(
        np.zeros((0, 4)),
        30.0,
        20,
        TraceStatisticsConfig(min_intersections=5),
        200.0,
    )

    assert selected == "hybrid"


def test_auto_window_strategy_falls_back_to_density_when_all_invalid(monkeypatch):
    """当所有策略均无有效分组时，应回退到密度偏好策略。"""

    def fake_circle_windows(_segments, _length, _config, strategy):
        return (
            _window(
                strategy,
                f"{strategy}:center",
                "center",
                valid=False,
                intersection_count=0,
            ),
        )

    monkeypatch.setattr(_window_scoring_module, "compute_circle_windows", fake_circle_windows)

    selected, diagnostics = _select_window_diagnostics(
        np.zeros((0, 4)),
        30.0,
        20,
        TraceStatisticsConfig(min_intersections=5),
        200.0,
    )

    assert selected == "hybrid"
    assert all(not d.valid for d in diagnostics)


def test_auto_window_strategy_tie_tolerance_boundary(monkeypatch):
    """评分差值恰好在 tolerance 边界时，密度偏好应胜出。"""

    call_count = {"n": 0}

    def fake_circle_windows(_segments, _length, _config, strategy):
        call_count["n"] += 1
        if strategy == "tangent":
            return (
                _window("tangent", "tangent:left:0", "left", cut_position=5.0,
                        intersection_count=15, l_est=6.0, p20=1.2, p21=1.5),
                _window("tangent", "tangent:right:0", "right", cut_position=5.0,
                        intersection_count=15, l_est=6.0, p20=1.2, p21=1.5),
                _window("tangent", "tangent:left:1", "left", cut_position=15.0,
                        intersection_count=15, l_est=6.0, p20=1.2, p21=1.5),
            )
        if strategy == "hybrid":
            return (
                _window("hybrid", "hybrid:0.5:left", "left", cut_position=15.0,
                        intersection_count=14, l_est=5.8, p20=1.1, p21=1.4),
                _window("hybrid", "hybrid:0.5:right", "right", cut_position=15.0,
                        intersection_count=14, l_est=5.8, p20=1.1, p21=1.4),
                _window("hybrid", "hybrid:0.25:left", "left", cut_position=7.5,
                        intersection_count=14, l_est=5.8, p20=1.1, p21=1.4),
            )
        return (
            _window("concentric", "concentric:center", "center",
                    intersection_count=12, l_est=5.5, p20=1.0, p21=1.3),
        )

    monkeypatch.setattr(_window_scoring_module, "compute_circle_windows", fake_circle_windows)

    selected, _diagnostics = _select_window_diagnostics(
        np.zeros((0, 4)),
        30.0,
        20,
        TraceStatisticsConfig(min_intersections=5),
        200.0,
    )

    assert selected in {"tangent", "hybrid", "concentric"}
    assert call_count["n"] == 3
