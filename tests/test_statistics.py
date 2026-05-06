"""单元测试：迹线统计指标。"""
import math

import numpy as np
import pytest

from trace_pipeline.geology.statistics import (
    TraceStatisticsConfig,
    _effective_trace_length_total,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from trace_pipeline.models import TraceData


def _trace(
    endpoints,
    scanline_positions,
    *,
    segment_lengths=None,
    measured_scanline_length=None,
    measured_outcrop_area=None,
):
    arr = np.asarray(endpoints, dtype=float)
    if segment_lengths is None:
        segment_lengths = np.ones(arr.shape[0])
    return TraceData(
        scanline_azimuth=90.0,
        count=arr.shape[0],
        endpoints=arr,
        joint_strikes=np.zeros(arr.shape[0]),
        segment_lengths=np.asarray(segment_lengths, dtype=float),
        scanline_positions=np.asarray(scanline_positions, dtype=float),
        measured_scanline_length=measured_scanline_length,
        measured_outcrop_area=measured_outcrop_area,
    )


def test_measured_scanline_length_outcrop_area_and_density_formulas():
    trace = _trace(
        [
            [5.0, -1.0, 5.0, 1.0],    # I：有限段与测线相交
            [10.0, 1.0, 12.0, 3.0],   # II：延长线与测线相交
            [0.0, 2.0, 1.0, 2.0],     # III：其余记录
        ],
        [0.0, 10.0, 20.0],
        measured_scanline_length=30.0,
        measured_outcrop_area=60.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))
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


def test_outcrop_area_estimates_from_scanline_envelope_rectangle():
    trace = _trace(
        [
            [5.0, -1.0, 5.0, 1.0],
            [10.0, 3.0, 12.0, 3.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        [0.0, 10.0, 20.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    assert stats.scanline_length == pytest.approx(25.0)
    assert stats.scanline_length_source == "estimated"
    assert stats.outcrop_area == pytest.approx(100.0)
    assert stats.outcrop_area_source == "estimated"
    assert stats.p10 == pytest.approx(3 / 25.0)
    assert stats.p20 == pytest.approx(3 / 100.0)


def test_p21_uses_endpoint_length_total_over_outcrop_area():
    trace = _trace(
        [
            [0.0, 0.0, 3.0, 4.0],
            [1.0, 0.0, 1.0, 5.0],
        ],
        [0.0, 10.0],
        measured_scanline_length=10.0,
        measured_outcrop_area=20.0,
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    assert stats.trace_length_total == pytest.approx(10.0)
    assert stats.mean_trace_length == pytest.approx(5.0)
    assert stats.p21 == pytest.approx(10.0 / 20.0)


def test_trace_length_total_falls_back_from_endpoint_to_segment_lengths():
    trace = _trace(
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
    trace = _trace(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 1.0],
        ],
        [0.0, 10.0],
        segment_lengths=[0.0, 0.0],
    )

    total, source = _effective_trace_length_total(trace, estimated_mean_length=2.5)

    assert source == "window_estimate"
    assert total == pytest.approx(5.0)


def test_circle_window_counts_stay_available_for_internal_diagnostics():
    trace = _trace(
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
    assert window.l_est == pytest.approx(math.pi)
    assert stats.p20 == pytest.approx(stats.total_count / stats.outcrop_area)


def test_invalid_circle_windows_record_reasons_and_format_na():
    trace = _trace([[5.0, -1.0, 5.0, 1.0]], [0.0])

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
    assert "面累计长度密度" in joined
    assert "体密度" not in joined
    assert "总裂隙数" not in joined


def test_terzaghi_correction_true_raises_not_implemented():
    trace = _trace([[5.0, -1.0, 5.0, 1.0]], [0.0])

    with pytest.raises(NotImplementedError, match="terzaghi_correction 暂未实现"):
        compute_trace_statistics(trace, TraceStatisticsConfig(terzaghi_correction=True))
