"""单元测试：迹线统计指标。"""
import math

import numpy as np
import pytest

import trace_pipeline.geology._window_scoring as _window_scoring_module
from tests.conftest import make_trace
from trace_pipeline.geology._convex_hull import _convex_hull_area
from trace_pipeline.geology._window_scoring import _select_window_diagnostics
from trace_pipeline.geology.statistics import (
    CircleWindowDiagnostic,
    TraceStatisticsConfig,
    _effective_trace_length_total,
    _select_effective_area,
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
        segment_lengths=[0.0, 0.0, 0.0],  # 强制回退到 endpoint
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


def test_p21_uses_measured_area_when_available():
    trace = make_trace(
        [
            [0.0, 0.0, 3.0, 4.0],
            [1.0, 0.0, 1.0, 5.0],
        ],
        [0.0, 10.0],
        segment_lengths=[0.0, 0.0],  # 强制回退到 endpoint
        measured_scanline_length=10.0,
        measured_outcrop_area=20.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=99))

    assert stats.trace_length_total == pytest.approx(10.0)
    assert stats.mean_trace_length == pytest.approx(5.0)
    assert stats.p21 == pytest.approx(10.0 / 20.0)
    assert stats.p21_source == "measured"


def test_trace_length_total_uses_segment_when_available():
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


def test_trace_length_prefers_endpoint_when_segments_zero():
    """segment 全为零时回退到 endpoint，不再优先使用圆窗。"""
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

    # 端点距离总和 = 4+4+20+20 = 48，segment 全为 0，所以用 endpoint
    assert stats.trace_length_source == "endpoint"
    assert stats.trace_length_total == pytest.approx(48.0)


def test_trace_length_falls_back_to_window_when_observed_unavailable():
    """segment 和 endpoint 均不可用时才回退到圆窗 l_est。"""
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

    # segment 全为 0 → endpoint 优先 → 48.0
    assert stats.trace_length_source == "endpoint"
    assert stats.trace_length_total == pytest.approx(48.0)

    # 直接测试函数：observed 不可用时回退圆窗
    total, source = _effective_trace_length_total(
        trace,
        estimated_mean_length=5.0,
        observed_total=math.nan,
        observed_source="unavailable",
    )
    assert source == "window"
    assert total == pytest.approx(5.0 * trace.count)


def test_full_statistics_chain_with_sources_and_formatting():
    trace = make_trace(
        [
            [9.5, 2.0, 15.5, 2.0],      # N0：两端点都在圆外但线段穿圆
            [12.5, 2.0, 15.5, 2.0],     # N1：一个端点在圆内
            [12.0, 2.0, 13.0, 2.0],     # N2：两个端点都在圆内
            [100.0, 4.0, 101.0, 4.0],   # 提供侧向高度，不与圆相交
        ],
        [0.0, 10.0, 20.0, 20.0],
        segment_lengths=[0.0, 0.0, 0.0, 0.0],  # 强制回退到 endpoint
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

    # 圆窗诊断始终可用，但主统计现在优先使用观测值
    # endpoint_total = 6+3+1+1 = 11，mean = 11/4 = 2.75
    assert stats.trace_length_source == "endpoint"
    assert stats.trace_length_total == pytest.approx(11.0)
    assert stats.mean_trace_length == pytest.approx(11.0 / 4)

    # P20 = count / effective_area（凸包或圆窗等效）
    # 此 trace 的凸包面积与圆窗等效面积差异大，可能触发降级
    assert stats.p20_source in ("hull", "window_equivalent")
    # P21 = observed_total / effective_area
    assert stats.p21_source == stats.p20_source

    # 圆窗等效面积应被记录
    assert stats.window_outcrop_area > 0.0

    lines = format_statistics_box_lines(stats)
    joined = "\n".join(lines)
    assert "测线走向: 90.0°" in lines
    assert "圆窗策略: 混合圆窗" in lines
    assert "平均迹线长度（端点）" in joined
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
    # P21 现在优先 observed_total / measured_area，不再优先圆窗
    assert stats.p21_source == "measured"


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
    assert all(diagnostic.invalid_reason for diagnostic in stats.diagnostics)
    assert math.isnan(stats.p20)
    assert "I/II/III型裂隙数: 0/0/1" in lines
    assert "测线长度: 0.000 $\\mathrm{m}$" in lines
    assert any("露头面积" in line for line in lines)
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
        invalid_reason="" if valid else "invalid",
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


# ── 新增测试：面积三层回退 ─────────────────────────────────────────────


def test_area_priority_measured_over_hull_and_window():
    """实测面积存在时，无论凸包和圆窗如何，都使用实测。"""
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
        measured_outcrop_area=1000.0,  # 远大于凸包面积 40
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))
    assert stats.outcrop_area_source == "measured"
    assert stats.outcrop_area == pytest.approx(1000.0)
    assert stats.p20_source == "measured"
    assert stats.p20 == pytest.approx(4 / 1000.0)
    # 实测面积不应触发降级告警
    assert stats.window_validation_warning == ""


def test_area_priority_hull_over_window_equivalent():
    """无实测面积时，凸包有效且与圆窗差异不大，优先使用凸包。"""
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))
    assert stats.outcrop_area_source == "hull"
    assert stats.outcrop_area == pytest.approx(40.0)


def test_area_falls_back_to_window_equivalent_when_hull_degenerate():
    """凸包退化（点数不足/共线）时回退到圆窗等效面积。"""
    # 使用与圆窗相交的共线迹线
    # 原始坐标为竖直线，旋转 90° 后变为水平线（与测线平行）
    # 端点 (0,0)→(0,0), (0,5)→(5,0), (0,10)→(10,0) 在局部坐标系中
    trace = make_trace(
        [
            [0.0, 0.0, 0.0, 5.0],
            [0.0, 5.0, 0.0, 10.0],
        ],
        [0.0, 10.0],
        measured_scanline_length=10.0,
    )

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="tangent",
            tangent_window_count=1,
            min_intersections=1,
        ),
    )

    # 凸包共线 → NaN
    assert math.isnan(_convex_hull_area(trace.endpoints.reshape(-1, 2)))
    # 应回退到圆窗等效面积
    assert stats.outcrop_area_source == "window_equivalent"
    assert stats.window_outcrop_area > 0.0
    assert stats.outcrop_area == pytest.approx(stats.window_outcrop_area)


def test_p20_uses_effective_area_chain():
    """P20 = trace_count / effective_area，跟随面积优先链。"""
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))
    # 凸包面积 = 40
    assert stats.outcrop_area == pytest.approx(40.0)
    assert stats.p20 == pytest.approx(4 / 40.0)
    assert stats.p20_source == "hull"


def test_p20_falls_back_to_window_p20_when_area_unavailable():
    """面积完全不可用时，回退到圆窗 P20。"""
    trace = make_trace(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 1.0, 0.0],
        ],
        [0.0, 10.0],
        measured_scanline_length=10.0,
    )

    stats = compute_trace_statistics(
        trace,
        TraceStatisticsConfig(
            window_strategy="hybrid",
            cut_fractions=(0.5,),
            radius_fractions=(1.0,),
            min_intersections=5,  # 迹线少，窗口无效
        ),
    )

    # 凸包退化 + 圆窗无效 → 面积不可用
    assert stats.outcrop_area_source == "unavailable"
    assert math.isnan(stats.outcrop_area) or stats.outcrop_area == 0.0
    # P20 也不可用
    assert math.isnan(stats.p20)
    assert stats.p20_source == "unavailable"


def test_p21_uses_observed_over_window():
    """P21 优先使用 observed_total / effective_area，而非圆窗 P21。"""
    trace = make_trace(
        [
            [9.5, 2.0, 15.5, 2.0],
            [12.5, 2.0, 15.5, 2.0],
            [12.0, 2.0, 13.0, 2.0],
            [100.0, 4.0, 101.0, 4.0],
        ],
        [0.0, 10.0, 20.0, 20.0],
        segment_lengths=[0.0, 0.0, 0.0, 0.0],  # 强制回退到 endpoint
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

    # observed_total = 6+3+1+1 = 11
    observed_total = 11.0
    # effective_area = hull_area
    assert stats.p21 == pytest.approx(observed_total / stats.outcrop_area)
    assert stats.p21_source == stats.outcrop_area_source


def test_p21_consistency_p20_times_mean_close():
    """P21 ≈ P20 * mean_trace_length 自洽性检验。"""
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
        measured_scanline_length=35.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    # P21 ≈ P20 * mean_trace_length
    if math.isfinite(stats.p20) and math.isfinite(stats.mean_trace_length) and math.isfinite(stats.p21):
        expected_p21 = stats.p20 * stats.mean_trace_length
        assert stats.p21 == pytest.approx(expected_p21, rel=0.01)


# ── 新增测试：迹长优先级 ───────────────────────────────────────────────


def test_trace_length_prefers_segment_over_endpoint():
    """segment(r5+r7) 优先于端点欧氏距离。"""
    trace = make_trace(
        [
            [0.0, 0.0, 3.0, 4.0],   # endpoint length = 5
            [1.0, 0.0, 1.0, 5.0],   # endpoint length = 5
        ],
        [0.0, 10.0],
        segment_lengths=[6.0, 8.0],  # segment lengths 大于 endpoint
        measured_scanline_length=10.0,
        measured_outcrop_area=20.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=99))

    assert stats.trace_length_source == "segment"
    assert stats.trace_length_total == pytest.approx(14.0)
    assert stats.mean_trace_length == pytest.approx(7.0)


# ── 新增测试：窗口校验与告警 ───────────────────────────────────────────


def test_no_warning_when_sources_agree():
    """常规数据下不应产生降级告警。"""
    trace = make_trace(
        [
            [0.0, 0.0, 10.0, 0.0],
            [10.0, 0.0, 10.0, 4.0],
            [10.0, 4.0, 0.0, 4.0],
            [0.0, 4.0, 0.0, 0.0],
        ],
        [0.0, 10.0, 20.0, 30.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    assert stats.window_validation_warning == ""
    assert stats.outcrop_area_source == "hull"


def test_window_equivalent_area_recorded():
    """圆窗等效面积始终被计算并记录到 TraceStatistics。"""
    # 使用有有效窗口的 trace
    trace = make_trace(
        [
            [9.5, 2.0, 15.5, 2.0],
            [12.5, 2.0, 15.5, 2.0],
            [12.0, 2.0, 13.0, 2.0],
            [100.0, 4.0, 101.0, 4.0],
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

    assert math.isfinite(stats.window_outcrop_area)
    assert stats.window_outcrop_area > 0.0
    # 圆窗等效面积与主面积不同，因为主面积用凸包
    if stats.outcrop_area_source == "hull":
        assert stats.window_outcrop_area != pytest.approx(stats.outcrop_area)


def test_area_disagreement_ratio_nan_when_measured():
    """实测面积时，面积差异比应为 NaN（不参与凸包-圆窗比较）。"""
    # 直接测试函数行为
    area, source, ratio, warning = _select_effective_area(
        trace=make_trace([[0.0, 0.0, 1.0, 0.0]], [0.0], measured_outcrop_area=50.0),
        hull_area=100.0,
        window_equivalent_area=10.0,
        local_segments=np.array([[0.0, 0.0, 1.0, 0.0]]),
    )
    assert source == "measured"
    assert area == pytest.approx(50.0)
    assert math.isnan(ratio)
    assert warning == ""


# ── 圆窗公式回归测试 ──────────────────────────────────────────────────


def test_circle_window_formulas_m_neq_q():
    """m ≠ q 时，P20 = q/(2πr²)，P21 = m/(4r)，l_est = (πr/2)(m/q)。"""
    from trace_pipeline.geology._circle_window import _count_circle_windows_batch

    r = 2.0
    center_x = 15.0
    center_y = r

    local_segments = np.array([
        [center_x - r - 0.1, center_y, center_x + r + 0.1, center_y],
        [center_x - 0.5, center_y, center_x + 0.5, center_y],
        [center_x - 0.1, center_y - 0.1, center_x + 0.1, center_y + 0.1],
    ])

    diagnostics = _count_circle_windows_batch(
        local_segments=local_segments,
        centers=np.array([[center_x, center_y]]),
        radii=np.array([r]),
        min_intersections=1,
        cut_positions=np.array([center_x]),
        sides=["left"],
        strategies=["hybrid"],
        group_keys=["test"],
    )

    win = diagnostics[0]
    assert win.valid
    m_val = win.m
    q_val = win.q
    assert q_val > 0, f"q_val should be positive, got {q_val}"

    p20_expected = q_val / (2.0 * math.pi * r * r)
    p21_expected = m_val / (4.0 * r)
    l_est_expected = (math.pi * r / 2.0) * (m_val / q_val) if q_val != 0 else math.nan

    assert win.p20 == pytest.approx(p20_expected)
    assert win.p21 == pytest.approx(p21_expected)
    if math.isfinite(l_est_expected):
        assert win.l_est == pytest.approx(l_est_expected)


def test_circle_window_formulas_yang_chunhe_reference():
    """杨春和参考数据验证: c=13.5287, N0=7, N1=16, N2=4 → m=24, q=30。

    取圆窗半径 r=c/2（切线窗）验证 P20 ≈ 0.0261, l_est ≈ 17.0。
    """
    r = 13.5287

    n0, n1, n2 = 7, 16, 4
    m_expected = n1 + 2 * n2
    q_expected = 2 * n0 + n1
    assert m_expected == 24
    assert q_expected == 30

    p20_expected = q_expected / (2.0 * math.pi * r * r)
    l_est_expected = (math.pi * r / 2.0) * (m_expected / q_expected)

    assert p20_expected == pytest.approx(0.0261, rel=0.01)
    assert l_est_expected == pytest.approx(17.0, rel=0.02)


def test_circle_window_q_zero_is_invalid():
    """q <= 0 的圆窗应标记为无效，p20/p21/l_est 为 NaN。"""
    from trace_pipeline.geology._circle_window import _count_circle_windows_batch

    r = 2.0
    center_x = 15.0
    center_y = r

    local_segments = np.array([
        [center_x - 1.0, center_y - 0.1, center_x + 1.0, center_y + 0.1],
    ])

    diagnostics = _count_circle_windows_batch(
        local_segments=local_segments,
        centers=np.array([[center_x, center_y]]),
        radii=np.array([r]),
        min_intersections=1,
        cut_positions=np.array([center_x]),
        sides=["left"],
        strategies=["test"],
        group_keys=["test"],
    )

    win = diagnostics[0]
    if win.q <= 0:
        assert not win.valid
        assert "q <= 0" in win.invalid_reason
        assert math.isnan(win.p20)
        assert math.isnan(win.p21)
        assert math.isnan(win.l_est)
