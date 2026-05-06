"""单元测试：迹线统计指标。"""
import math

import numpy as np
import pytest

from trace_pipeline.geology.statistics import (
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from trace_pipeline.models import TraceData


def _trace(endpoints, scanline_positions):
    arr = np.asarray(endpoints, dtype=float)
    return TraceData(
        scanline_azimuth=90.0,
        count=arr.shape[0],
        endpoints=arr,
        joint_strikes=np.zeros(arr.shape[0]),
        segment_lengths=np.ones(arr.shape[0]),
        scanline_positions=np.asarray(scanline_positions, dtype=float),
    )


def test_scanline_length_p10_and_type_classification():
    trace = _trace(
        [
            [5.0, -1.0, 5.0, 1.0],    # I：有限段与测线相交
            [10.0, 1.0, 12.0, 3.0],   # II：延长线与测线相交
            [0.0, 2.0, 1.0, 2.0],     # III：其余记录
        ],
        [0.0, 10.0, 20.0],
    )

    stats = compute_trace_statistics(trace, TraceStatisticsConfig(min_intersections=1))

    assert stats.scanline_length_estimate == pytest.approx(25.0)
    assert stats.trace_types == ("I", "II", "III")
    assert stats.type_i_count == 1
    assert stats.type_ii_count == 1
    assert stats.type_iii_count == 1
    assert stats.p10_i == pytest.approx(1 / 25.0)
    assert stats.p10_all == pytest.approx(3 / 25.0)


def test_circle_window_counts_and_density_formula():
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
    assert stats.p20 == pytest.approx(window.p20)
    assert stats.estimated_mean_trace_length == pytest.approx(window.l_est)
    assert stats.p21_est == pytest.approx(3 / 8)


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

    assert stats.valid_window_count == 0
    assert all(diagnostic.reason for diagnostic in stats.diagnostics)
    assert math.isnan(stats.p20)
    assert "I/II/III型数量: 0/0/1" in lines
    assert "估算测线长度（$L_{\\mathrm{hat}}$）: 0.000 $\\mathrm{m}$" in lines
    assert "面密度（$P_{20}$）: N/A" in lines


def test_terzaghi_correction_true_raises_not_implemented():
    trace = _trace([[5.0, -1.0, 5.0, 1.0]], [0.0])

    with pytest.raises(NotImplementedError, match="terzaghi_correction 暂未实现"):
        compute_trace_statistics(trace, TraceStatisticsConfig(terzaghi_correction=True))
