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
from ._circle_window import _classify_trace_types
from ._convex_hull import (
    _buffered_hull_area,
    _compute_convex_hull,
    _convex_hull_area,
    _is_hull_geometrically_valid,
)
from ._stat_format import format_statistics_box_lines
from ._stat_types import (
    _EPS,
    CircleWindowDiagnostic,
    TraceStatistics,
    TraceStatisticsConfig,
)
from ._window_scoring import _aggregate_window_metric, _select_window_diagnostics
from .angles import azimuth_to_cartesian_deg

__all__ = [
    "CircleWindowDiagnostic",
    "TraceStatistics",
    "TraceStatisticsConfig",
    "compute_trace_statistics",
    "format_statistics_box_lines",
]

logger = logging.getLogger(__name__)

# 测线长度与坐标变换


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


def _to_local_segments(trace: TraceData) -> np.ndarray:
    angle = math.radians(azimuth_to_cartesian_deg(trace.scanline_azimuth))
    along = np.array([math.cos(angle), math.sin(angle)], dtype=float)
    left = np.array([-math.sin(angle), math.cos(angle)], dtype=float)

    points = trace.endpoints.reshape(-1, 2)
    local_points = np.column_stack((points @ along, points @ left))
    return local_points.reshape(trace.endpoints.shape)


# 自适应阈值


def _adaptive_disagreement_threshold(trace_count: int) -> float:
    """自适应面积降级阈值：样本量越大越严格。"""
    n = max(0, trace_count)
    return 0.30 + 0.20 * math.exp(-n / 30.0)


def _adaptive_consistency_threshold(trace_count: int) -> float:
    """自适应 P20/P21 一致性校验阈值。"""
    n = max(0, trace_count)
    return 0.50 * (0.30 + 0.20 * math.exp(-n / 30.0))


# 露头面积


def _compute_window_equivalent_area(trace_count: int, window_p20: float) -> float:
    """由圆窗 P20 反推统计等效面积：area = trace_count / P20_window。"""
    if trace_count > 0 and math.isfinite(window_p20) and window_p20 > _EPS:
        return trace_count / window_p20
    return math.nan


def _select_effective_area(
    trace: TraceData,
    hull_area: float,
    hull_buffered_area: float,
    window_equivalent_area: float,
    local_segments: np.ndarray,
    config: TraceStatisticsConfig,
) -> tuple[float, str, float, str]:
    """四层回退：实测 -> 凸包 -> 缓冲凸包 -> 圆窗等效面积。

    Returns:
        (effective_area, area_source, disagreement_ratio, warning)
    """
    # 层 1：实测面积（最可靠，绝不降级）
    if trace.measured_outcrop_area is not None:
        return float(trace.measured_outcrop_area), "measured", math.nan, ""

    # 层 2：原始凸包（需几何质量合格）
    hull_valid = _is_hull_geometrically_valid(local_segments, hull_area)
    if hull_valid:
        if not math.isfinite(window_equivalent_area) or window_equivalent_area <= _EPS:
            return hull_area, "hull", 0.0, ""

        ratio_hull = abs(hull_area - window_equivalent_area) / max(
            hull_area, window_equivalent_area
        )
        threshold = (
            config.disagreement_threshold
            if config.disagreement_threshold is not None
            else _adaptive_disagreement_threshold(trace.count)
        )

        if ratio_hull <= threshold:
            # 差异小，信任原始凸包
            return hull_area, "hull", ratio_hull, ""

        # 差异大 → 尝试缓冲修正
        if math.isfinite(hull_buffered_area) and hull_buffered_area > _EPS:
            ratio_buffered = abs(hull_buffered_area - window_equivalent_area) / max(
                hull_buffered_area, window_equivalent_area
            )
            if ratio_buffered < ratio_hull:
                return hull_buffered_area, "hull_buffered", ratio_buffered, ""

        # 缓冲后仍差异大 → 降级到圆窗等效面积
        warning = (
            f"凸包面积({hull_area:.2f})与圆窗等效面积({window_equivalent_area:.2f})"
            f"差异达{ratio_hull:.0%}，已降级使用圆窗等效面积"
        )
        return window_equivalent_area, "window_equivalent", ratio_hull, warning

    # 层 3：缓冲凸包（兜底）
    if math.isfinite(hull_buffered_area) and hull_buffered_area > _EPS:
        return hull_buffered_area, "hull_buffered", math.nan, ""

    # 层 4：圆窗等效面积（兜底）
    if math.isfinite(window_equivalent_area) and window_equivalent_area > _EPS:
        return window_equivalent_area, "window_equivalent", math.nan, ""

    return math.nan, "unavailable", math.nan, ""


# 迹长


def _finite_positive_total(values: np.ndarray) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        return math.nan
    total = float(np.sum(array))
    return total if math.isfinite(total) and total > _EPS else math.nan


def _observed_trace_length_total(trace: TraceData) -> tuple[float, str]:
    """观测迹长优先链：segment(r5+r7) -> endpoint(端点欧氏距离)。"""
    segment_total = _finite_positive_total(trace.segment_lengths)
    if math.isfinite(segment_total):
        return segment_total, "segment"

    endpoint_total = _finite_positive_total(trace.lengths)
    if math.isfinite(endpoint_total):
        return endpoint_total, "endpoint"

    return math.nan, "unavailable"


def _effective_trace_length_total(
    trace: TraceData,
    estimated_mean_length: float,
    observed_total: float,
    observed_source: str,
) -> tuple[float, str]:
    """迹长总长度回退链：observed(segment/endpoint) -> window(l_est)。"""
    estimated_mean_length = float(estimated_mean_length)
    if trace.count > 0 and math.isfinite(observed_total) and observed_total > _EPS:
        return observed_total, observed_source

    if trace.count > 0 and math.isfinite(estimated_mean_length) and estimated_mean_length >= 0.0:
        return float(estimated_mean_length * trace.count), "window"

    return math.nan, "unavailable"


# 主入口


def compute_trace_statistics(
    trace: TraceData,
    config: TraceStatisticsConfig | None = None,
) -> TraceStatistics:
    """计算迹线图统计指标。"""
    if config is None:
        config = TraceStatisticsConfig()

    # 1. 基础几何与坐标转换
    scanline_length, scanline_length_source = _effective_scanline_length(trace)
    finite_scanline_length = (
        scanline_length if math.isfinite(float(scanline_length)) and scanline_length > _EPS else 0.0
    )
    local_segments = _to_local_segments(trace)
    trace_types = _classify_trace_types(local_segments, finite_scanline_length)

    # 2. 圆窗诊断（完全独立于凸包面积）
    # 数据依赖：endpoints -> circle_window_p20（独立路径）
    hull_area = _convex_hull_area(local_segments)
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

    # 3. 露头面积估算（复用第 2 步已计算的 hull_area）
    hull_vertices = _compute_convex_hull(local_segments)

    # 4. 观测迹长
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

    # 5. 缓冲凸包面积
    hull_buffered_area = math.nan
    if (
        hull_vertices is not None
        and math.isfinite(mean_trace_length)
        and mean_trace_length > _EPS
        and config.hull_buffer_ratio > _EPS
    ):
        buffer_distance = config.hull_buffer_ratio * mean_trace_length
        hull_buffered_area = _buffered_hull_area(hull_vertices, buffer_distance)

    # 6. 圆窗等效面积（独立路径）
    window_equivalent_area = _compute_window_equivalent_area(trace.count, estimated_p20)
    if not math.isfinite(window_equivalent_area):
        window_equivalent_area = math.nan

    # 7. 面积选择（四层回退，自适应阈值）
    effective_area, area_source, disagreement_ratio, area_warning = _select_effective_area(
        trace,
        hull_area,
        hull_buffered_area,
        window_equivalent_area,
        local_segments,
        config,
    )

    # 8. P10（观测线密度）
    p10 = trace.count / scanline_length if scanline_length > _EPS else math.nan

    # 9. P20 / P21
    if math.isfinite(effective_area) and effective_area > _EPS:
        p20 = trace.count / effective_area
        p20_source = area_source
        if math.isfinite(observed_total) and observed_total > 0:
            p21 = observed_total / effective_area
            p21_source = area_source
        else:
            p21 = math.nan
            p21_source = area_source
    elif math.isfinite(estimated_p20):
        p20 = estimated_p20
        p20_source = "window"
        p21 = estimated_p21 if math.isfinite(estimated_p21) else math.nan
        p21_source = "window"
    else:
        p20 = math.nan
        p20_source = "unavailable"
        p21 = math.nan
        p21_source = "unavailable"

    # 10. 一致性校验（自适应阈值）
    consistency_threshold = _adaptive_consistency_threshold(trace.count)
    window_validation_warning = area_warning
    if not window_validation_warning and p20_source != "window" and p21_source != "window":
        if math.isfinite(estimated_p20) and math.isfinite(p20) and p20 > _EPS:
            p20_disagreement = abs(p20 - estimated_p20) / max(p20, estimated_p20)
            if p20_disagreement > consistency_threshold:
                window_validation_warning = (
                    f"主 P20({p20:.4f})与圆窗 P20({estimated_p20:.4f})差异达{p20_disagreement:.0%}"
                )
        if (
            not window_validation_warning
            and math.isfinite(estimated_p21)
            and math.isfinite(p21)
            and p21 > _EPS
        ):
            p21_disagreement = abs(p21 - estimated_p21) / max(p21, estimated_p21)
            if p21_disagreement > consistency_threshold:
                window_validation_warning = (
                    f"主 P21({p21:.4f})与圆窗 P21({estimated_p21:.4f})差异达{p21_disagreement:.0%}"
                )

    if window_validation_warning:
        logger.warning("校验告警: %s", window_validation_warning)

    logger.debug(
        "统计来源: 策略=%s, 测线长度=%.3f(来源=%s), 露头面积=%.3f(来源=%s), "
        "平均迹长=%.3f(来源=%s), P20=%.4f(来源=%s), P21=%.4f(来源=%s), "
        "圆窗等效面积=%.3f, 缓冲面积=%.3f, 校验告警=%s",
        selected_strategy,
        scanline_length,
        scanline_length_source,
        effective_area,
        area_source,
        mean_trace_length,
        trace_length_source,
        p20,
        p20_source,
        p21,
        p21_source,
        window_equivalent_area,
        hull_buffered_area,
        window_validation_warning,
    )

    return TraceStatistics(
        scanline_azimuth=float(trace.scanline_azimuth),
        total_count=trace.count,
        type_i_count=type_i_count,
        type_ii_count=type_ii_count,
        type_iii_count=type_iii_count,
        scanline_length=float(scanline_length),
        outcrop_area=float(effective_area) if math.isfinite(effective_area) else math.nan,
        mean_trace_length=float(mean_trace_length),
        trace_length_total=float(trace_length_total),
        p10=float(p10),
        p20=float(p20),
        p21=float(p21),
        scanline_length_source=scanline_length_source,
        outcrop_area_source=area_source,
        trace_length_source=trace_length_source,
        p20_source=p20_source,
        p21_source=p21_source,
        window_strategy=selected_strategy,
        trace_types=trace_types,
        diagnostics=diagnostics,
        window_outcrop_area=float(window_equivalent_area)
        if math.isfinite(window_equivalent_area)
        else math.nan,
        area_disagreement_ratio=float(disagreement_ratio)
        if math.isfinite(disagreement_ratio)
        else math.nan,
        window_validation_warning=window_validation_warning,
        hull_buffered_area=float(hull_buffered_area)
        if math.isfinite(hull_buffered_area)
        else math.nan,
        hull_buffer_ratio=float(config.hull_buffer_ratio),
    )
