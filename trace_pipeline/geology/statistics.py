"""迹线图统计指标计算。

本模块基于测线局部坐标系计算综合法 I/II/III 分型、圆形取样窗计数
以及 P10/P20/P21 相关指标。测线有限段按 [0, L_hat] 处理。

内部实现拆分为以下子模块：
- ``_stat_types``    — 数据类定义
- ``_convex_hull``   — 凸包面积计算
- ``_circle_window`` — 圆窗策略、计数与评分
- ``_stat_format``   — 格式化输出
"""
from __future__ import annotations

import logging
import math

import numpy as np

from ..models import TraceData
from ._circle_window import (
    aggregate_window_metric as _aggregate_window_metric,
)
from ._circle_window import (
    classify_trace_types as _classify_trace_types,
)
from ._circle_window import (
    select_window_diagnostics as _select_window_diagnostics,
)
from ._convex_hull import convex_hull_area as _convex_hull_area
from ._stat_format import format_statistics_box_lines
from ._stat_types import (
    CircleWindowDiagnostic,
    TraceStatistics,
    TraceStatisticsConfig,
)

__all__ = [
    "CircleWindowDiagnostic",
    "TraceStatistics",
    "TraceStatisticsConfig",
    "compute_trace_statistics",
    "format_statistics_box_lines",
]

_EPS = 1e-9
logger = logging.getLogger(__name__)


# ── 测线长度与坐标变换 ────────────────────────────────────────────────


def _estimate_scanline_length(scanline_positions: np.ndarray) -> float:
    positions = np.asarray(scanline_positions, dtype=float)
    if positions.size == 0:
        return 0.0
    if not np.isfinite(positions).all():
        raise ValueError("scanline_positions 包含 NaN 或 inf")

    unique = np.unique(positions)
    diffs = np.diff(unique)
    positive_diffs = diffs[diffs > _EPS]
    spacing = float(np.median(positive_diffs)) if positive_diffs.size else 0.0
    return float(np.max(positions) + 0.5 * spacing)


def _effective_scanline_length(trace: TraceData) -> tuple[float, str]:
    if trace.measured_scanline_length is not None:
        return float(trace.measured_scanline_length), "measured"
    return float(_estimate_scanline_length(trace.scanline_positions)), "estimated"


def _scanline_angle_rad(azimuth_deg: float) -> float:
    angle_deg = 90.0 - azimuth_deg if azimuth_deg < 90.0 else 450.0 - azimuth_deg
    return math.radians(angle_deg)


def _to_local_segments(trace: TraceData) -> np.ndarray:
    angle = _scanline_angle_rad(trace.scanline_azimuth)
    along = np.array([math.cos(angle), math.sin(angle)], dtype=float)
    left = np.array([-math.sin(angle), math.cos(angle)], dtype=float)

    points = trace.endpoints.reshape(-1, 2)
    local_points = np.column_stack((points @ along, points @ left))
    return local_points.reshape(trace.endpoints.shape)


# ── 露头面积与迹长 ────────────────────────────────────────────────────


def _estimate_outcrop_area(local_segments: np.ndarray) -> float:
    return _convex_hull_area(local_segments)


def _effective_outcrop_area(
    trace: TraceData,
    local_segments: np.ndarray,
    scanline_length: float,
) -> tuple[float, str]:
    if trace.measured_outcrop_area is not None:
        return float(trace.measured_outcrop_area), "measured"
    return _estimate_outcrop_area(local_segments), "hull"


def _finite_positive_total(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        return math.nan
    total = float(np.sum(array))
    return total if math.isfinite(total) and total > _EPS else math.nan


def _effective_trace_length_total(
    trace: TraceData,
    estimated_mean_length: float,
    observed_total: float,
    observed_source: str,
) -> tuple[float, str]:
    estimated_mean_length = float(estimated_mean_length)
    if trace.count > 0 and math.isfinite(estimated_mean_length) and estimated_mean_length >= 0.0:
        return float(estimated_mean_length * trace.count), "window"

    return observed_total, observed_source


def _observed_trace_length_total(trace: TraceData) -> tuple[float, str]:
    endpoint_total = _finite_positive_total(trace.lengths)
    if math.isfinite(endpoint_total):
        return endpoint_total, "endpoint"

    segment_total = _finite_positive_total(trace.segment_lengths)
    if math.isfinite(segment_total):
        return segment_total, "segment"

    return math.nan, "unavailable"


# ── 主入口 ────────────────────────────────────────────────────────────


def compute_trace_statistics(
    trace: TraceData,
    config: TraceStatisticsConfig | None = None,
) -> TraceStatistics:
    """计算迹线图统计指标。"""
    if config is None:
        config = TraceStatisticsConfig()

    scanline_length, scanline_length_source = _effective_scanline_length(trace)
    finite_scanline_length = (
        scanline_length
        if math.isfinite(float(scanline_length)) and scanline_length > _EPS
        else 0.0
    )
    local_segments = _to_local_segments(trace)
    trace_types = _classify_trace_types(local_segments, finite_scanline_length)
    hull_area = _estimate_outcrop_area(local_segments)
    selected_strategy, diagnostics = _select_window_diagnostics(
        local_segments,
        finite_scanline_length,
        trace.count,
        config,
        hull_area,
    )

    type_i_count = trace_types.count("I")
    type_ii_count = trace_types.count("II")
    type_iii_count = trace_types.count("III")
    estimated_mean_length = _aggregate_window_metric(diagnostics, "l_est")
    estimated_p20 = _aggregate_window_metric(diagnostics, "p20")
    estimated_p21 = _aggregate_window_metric(diagnostics, "p21")
    outcrop_area, outcrop_area_source = _effective_outcrop_area(
        trace,
        local_segments,
        scanline_length,
    )
    observed_total, observed_source = _observed_trace_length_total(trace)
    trace_length_total, trace_length_source = _effective_trace_length_total(
        trace,
        estimated_mean_length,
        observed_total,
        observed_source,
    )
    mean_trace_length = (
        trace_length_total / trace.count
        if trace.count > 0 and math.isfinite(trace_length_total)
        else math.nan
    )

    p10 = trace.count / scanline_length if scanline_length > _EPS else math.nan
    if trace.measured_outcrop_area is not None:
        p20 = trace.count / trace.measured_outcrop_area
        p20_source = "measured"
    elif math.isfinite(estimated_p20):
        p20 = estimated_p20
        p20_source = "window"
    elif outcrop_area > _EPS:
        p20 = trace.count / outcrop_area
        p20_source = "hull"
    else:
        p20 = math.nan
        p20_source = "unavailable"

    if math.isfinite(estimated_p21):
        p21 = estimated_p21
        p21_source = "window"
    elif (
        trace.measured_outcrop_area is not None
        and math.isfinite(observed_total)
    ):
        p21 = observed_total / trace.measured_outcrop_area
        p21_source = "measured"
    elif math.isfinite(observed_total) and outcrop_area > _EPS:
        p21 = observed_total / outcrop_area
        p21_source = "hull"
    else:
        p21 = math.nan
        p21_source = "unavailable"

    logger.debug(
        "统计来源: 策略=%s, 测线长度=%s, 露头面积=%s, 平均迹长=%s, P20=%s, P21=%s",
        selected_strategy,
        scanline_length_source,
        outcrop_area_source,
        trace_length_source,
        p20_source,
        p21_source,
    )

    return TraceStatistics(
        scanline_azimuth=float(trace.scanline_azimuth),
        total_count=trace.count,
        type_i_count=type_i_count,
        type_ii_count=type_ii_count,
        type_iii_count=type_iii_count,
        scanline_length=float(scanline_length),
        outcrop_area=float(outcrop_area),
        mean_trace_length=float(mean_trace_length),
        trace_length_total=float(trace_length_total),
        p10=float(p10),
        p20=float(p20),
        p21=float(p21),
        scanline_length_source=scanline_length_source,
        outcrop_area_source=outcrop_area_source,
        trace_length_source=trace_length_source,
        p20_source=p20_source,
        p21_source=p21_source,
        window_strategy=selected_strategy,
        trace_types=trace_types,
        diagnostics=diagnostics,
    )
