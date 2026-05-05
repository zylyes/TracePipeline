"""迹线图统计指标计算。

本模块基于测线局部坐标系计算综合法 I/II/III 分型、圆形取样窗计数
以及 P10/P20/P21 相关指标。测线有限段按 [0, L_hat] 处理。
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from ..models import TraceData

__all__ = [
    "CircleWindowDiagnostic",
    "TraceStatistics",
    "TraceStatisticsConfig",
    "compute_trace_statistics",
    "format_statistics_box_lines",
]

_EPS = 1e-9


@dataclass(frozen=True)
class TraceStatisticsConfig:
    """迹线统计计算参数。"""

    cut_fractions: Sequence[float] = (0.25, 0.5, 0.75)
    radius_fractions: Sequence[float] = (1.0, 0.75, 0.5)
    min_intersections: int = 5
    terzaghi_correction: bool = False

    def __post_init__(self) -> None:
        cut_fractions = tuple(float(v) for v in self.cut_fractions)
        radius_fractions = tuple(float(v) for v in self.radius_fractions)
        if not cut_fractions:
            raise ValueError("cut_fractions 不能为空")
        if not radius_fractions:
            raise ValueError("radius_fractions 不能为空")
        if any((not math.isfinite(v)) or v <= 0.0 or v >= 1.0 for v in cut_fractions):
            raise ValueError("cut_fractions 必须位于 (0, 1) 范围内")
        if any((not math.isfinite(v)) or v <= 0.0 for v in radius_fractions):
            raise ValueError("radius_fractions 必须为正数")
        if int(self.min_intersections) <= 0:
            raise ValueError("min_intersections 必须为正整数")
        object.__setattr__(self, "cut_fractions", cut_fractions)
        object.__setattr__(self, "radius_fractions", radius_fractions)
        object.__setattr__(self, "min_intersections", int(self.min_intersections))


@dataclass(frozen=True)
class CircleWindowDiagnostic:
    """单个圆形取样窗的计数和有效性诊断。"""

    cut_position: float
    side: str
    center_x: float
    center_y: float
    radius: float
    intersection_count: int
    n0: int
    n1: int
    n2: int
    m: int
    q: int
    p20: float
    l_est: float
    valid: bool
    reason: str = ""


@dataclass(frozen=True)
class TraceStatistics:
    """迹线图统计结果。"""

    total_count: int
    type_i_count: int
    type_ii_count: int
    type_iii_count: int
    scanline_length_estimate: float
    observed_mean_length_all: float
    observed_mean_length_i: float
    estimated_mean_trace_length: float
    p10_i: float
    p10_all: float
    p20: float
    p21_est: float
    p21_obs: float
    trace_types: tuple[str, ...]
    diagnostics: tuple[CircleWindowDiagnostic, ...]

    @property
    def valid_window_count(self) -> int:
        return sum(1 for diagnostic in self.diagnostics if diagnostic.valid)


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


def _cross(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _bbox_overlaps(p1: np.ndarray, p2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> bool:
    return (
        max(min(p1[0], p2[0]), min(q1[0], q2[0])) <= min(max(p1[0], p2[0]), max(q1[0], q2[0])) + _EPS
        and max(min(p1[1], p2[1]), min(q1[1], q2[1])) <= min(max(p1[1], p2[1]), max(q1[1], q2[1])) + _EPS
    )


def _segment_intersects_segment(
    p1: np.ndarray,
    p2: np.ndarray,
    q1: np.ndarray,
    q2: np.ndarray,
) -> bool:
    r = p2 - p1
    s = q2 - q1
    r_norm = float(np.linalg.norm(r))
    s_norm = float(np.linalg.norm(s))
    if r_norm <= _EPS or s_norm <= _EPS:
        return False

    denom = _cross(r, s)
    qp = q1 - p1
    if abs(denom) <= _EPS:
        if abs(_cross(qp, r)) > _EPS:
            return False
        return _bbox_overlaps(p1, p2, q1, q2)

    t = _cross(qp, s) / denom
    u = _cross(qp, r) / denom
    return -_EPS <= t <= 1.0 + _EPS and -_EPS <= u <= 1.0 + _EPS


def _line_intersects_scanline_segment(p1: np.ndarray, p2: np.ndarray, length: float) -> bool:
    if length <= _EPS:
        return False

    q1 = np.array([0.0, 0.0], dtype=float)
    q2 = np.array([length, 0.0], dtype=float)
    r = p2 - p1
    s = q2 - q1
    if float(np.linalg.norm(r)) <= _EPS:
        return False

    denom = _cross(r, s)
    qp = q1 - p1
    if abs(denom) <= _EPS:
        return abs(_cross(qp, r)) <= _EPS

    u = _cross(qp, r) / denom
    return -_EPS <= u <= 1.0 + _EPS


def _classify_trace_types(local_segments: np.ndarray, scanline_length: float) -> tuple[str, ...]:
    q1 = np.array([0.0, 0.0], dtype=float)
    q2 = np.array([scanline_length, 0.0], dtype=float)
    labels = []
    for segment in local_segments:
        p1 = segment[0:2]
        p2 = segment[2:4]
        if _segment_intersects_segment(p1, p2, q1, q2):
            labels.append("I")
        elif _line_intersects_scanline_segment(p1, p2, scanline_length):
            labels.append("II")
        else:
            labels.append("III")
    return tuple(labels)


def _distance_point_to_segment(point: np.ndarray, p1: np.ndarray, p2: np.ndarray) -> float:
    segment = p2 - p1
    length_sq = float(segment @ segment)
    if length_sq <= _EPS:
        return float(np.linalg.norm(point - p1))
    t = float(((point - p1) @ segment) / length_sq)
    t = min(1.0, max(0.0, t))
    closest = p1 + t * segment
    return float(np.linalg.norm(point - closest))


def _segment_intersects_circle(segment: np.ndarray, center: np.ndarray, radius: float) -> bool:
    p1 = segment[0:2]
    p2 = segment[2:4]
    if np.linalg.norm(p1 - center) <= radius + _EPS:
        return True
    if np.linalg.norm(p2 - center) <= radius + _EPS:
        return True
    return _distance_point_to_segment(center, p1, p2) <= radius + _EPS


def _count_circle_window(
    local_segments: np.ndarray,
    cut_position: float,
    side: str,
    radius: float,
    min_intersections: int,
) -> CircleWindowDiagnostic:
    sign = 1.0 if side == "left" else -1.0
    center = np.array([cut_position, sign * radius], dtype=float)
    n0 = n1 = n2 = intersection_count = 0

    for segment in local_segments:
        if not _segment_intersects_circle(segment, center, radius):
            continue
        intersection_count += 1
        endpoint_distances = (
            float(np.linalg.norm(segment[0:2] - center)),
            float(np.linalg.norm(segment[2:4] - center)),
        )
        inside_count = sum(distance <= radius + _EPS for distance in endpoint_distances)
        if inside_count == 0:
            n0 += 1
        elif inside_count == 1:
            n1 += 1
        else:
            n2 += 1

    m = n1 + 2 * n2
    q = 2 * n0 + n1
    p20 = math.nan
    l_est = math.nan
    reason = ""
    valid = True
    if intersection_count < min_intersections:
        valid = False
        reason = f"相交迹线数不足: {intersection_count} < {min_intersections}"
    elif m <= 0:
        valid = False
        reason = "m <= 0"
    else:
        p20 = m / (2.0 * math.pi * radius * radius)
        l_est = (math.pi * radius / 2.0) * (q / m)

    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=float(center[0]),
        center_y=float(center[1]),
        radius=float(radius),
        intersection_count=intersection_count,
        n0=n0,
        n1=n1,
        n2=n2,
        m=m,
        q=q,
        p20=float(p20),
        l_est=float(l_est),
        valid=valid,
        reason=reason,
    )


def _invalid_window(cut_position: float, side: str, reason: str) -> CircleWindowDiagnostic:
    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=float(cut_position),
        center_y=math.nan,
        radius=math.nan,
        intersection_count=0,
        n0=0,
        n1=0,
        n2=0,
        m=0,
        q=0,
        p20=math.nan,
        l_est=math.nan,
        valid=False,
        reason=reason,
    )


def _side_height(local_segments: np.ndarray, sign: float) -> float:
    y_values = local_segments[:, [1, 3]].ravel()
    side_values = y_values[y_values * sign > _EPS]
    if side_values.size == 0:
        return 0.0
    return float(np.max(np.abs(side_values)))


def _compute_circle_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    diagnostics = []
    for cut_fraction in config.cut_fractions:
        cut_position = scanline_length * cut_fraction
        edge_limit = min(cut_position, scanline_length - cut_position)
        for side, sign in (("left", 1.0), ("right", -1.0)):
            side_height = _side_height(local_segments, sign)
            radius_max = min(side_height / 2.0, edge_limit)
            if radius_max <= _EPS:
                diagnostics.append(
                    _invalid_window(cut_position, side, "可用侧向高度或端部距离不足")
                )
                continue
            for radius_fraction in config.radius_fractions:
                radius = radius_max * radius_fraction
                diagnostics.append(
                    _count_circle_window(
                        local_segments,
                        cut_position,
                        side,
                        radius,
                        config.min_intersections,
                    )
                )
    return tuple(diagnostics)


def _aggregate_window_metric(
    diagnostics: Sequence[CircleWindowDiagnostic],
    attr: str,
) -> float:
    grouped: Mapping[tuple[float, str], list[float]] = defaultdict(list)
    for diagnostic in diagnostics:
        if diagnostic.valid:
            value = float(getattr(diagnostic, attr))
            if math.isfinite(value):
                grouped[(diagnostic.cut_position, diagnostic.side)].append(value)
    if not grouped:
        return math.nan

    group_means = [float(np.mean(values)) for values in grouped.values() if values]
    return float(np.mean(group_means)) if group_means else math.nan


def compute_trace_statistics(
    trace: TraceData,
    config: TraceStatisticsConfig | None = None,
) -> TraceStatistics:
    """计算迹线图统计指标。"""
    if config is None:
        config = TraceStatisticsConfig()
    # Terzaghi 修正接口已预留；本轮无论开关状态均不改变数值。

    scanline_length = _estimate_scanline_length(trace.scanline_positions)
    local_segments = _to_local_segments(trace)
    trace_types = _classify_trace_types(local_segments, scanline_length)
    diagnostics = _compute_circle_windows(local_segments, scanline_length, config)

    type_i_count = trace_types.count("I")
    type_ii_count = trace_types.count("II")
    type_iii_count = trace_types.count("III")
    observed_mean_all = float(trace.lengths.mean()) if trace.count else math.nan
    i_mask = np.array([label == "I" for label in trace_types], dtype=bool)
    observed_mean_i = float(trace.lengths[i_mask].mean()) if np.any(i_mask) else math.nan

    p10_i = type_i_count / scanline_length if scanline_length > _EPS else math.nan
    p10_all = trace.count / scanline_length if scanline_length > _EPS else math.nan
    p20 = _aggregate_window_metric(diagnostics, "p20")
    estimated_mean_length = _aggregate_window_metric(diagnostics, "l_est")
    p21_est = p20 * estimated_mean_length if math.isfinite(p20) and math.isfinite(estimated_mean_length) else math.nan
    p21_obs = p20 * observed_mean_all if math.isfinite(p20) and math.isfinite(observed_mean_all) else math.nan

    return TraceStatistics(
        total_count=trace.count,
        type_i_count=type_i_count,
        type_ii_count=type_ii_count,
        type_iii_count=type_iii_count,
        scanline_length_estimate=float(scanline_length),
        observed_mean_length_all=observed_mean_all,
        observed_mean_length_i=observed_mean_i,
        estimated_mean_trace_length=estimated_mean_length,
        p10_i=float(p10_i),
        p10_all=float(p10_all),
        p20=float(p20),
        p21_est=float(p21_est),
        p21_obs=float(p21_obs),
        trace_types=trace_types,
        diagnostics=diagnostics,
    )


def _format_value(value: float, unit: str = "") -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.3f}{unit}"


def format_statistics_box_lines(stats: TraceStatistics) -> tuple[str, ...]:
    """格式化迹线统计框文本。"""
    return (
        f"总裂隙数: {stats.total_count}",
        f"I/II/III型数量: {stats.type_i_count}/{stats.type_ii_count}/{stats.type_iii_count}",
        f"估算测线长度（$L_{{\\mathrm{{hat}}}}$）: {_format_value(stats.scanline_length_estimate, ' $\\mathrm{m}$')}",
        f"全部实测平均迹长（$L_{{\\mathrm{{obs,all}}}}$）: {_format_value(stats.observed_mean_length_all, ' $\\mathrm{m}$')}",
        f"I型实测平均迹长（$L_{{\\mathrm{{obs,I}}}}$）: {_format_value(stats.observed_mean_length_i, ' $\\mathrm{m}$')}",
        f"估算平均迹长（$L_{{\\mathrm{{est}}}}$）: {_format_value(stats.estimated_mean_trace_length, ' $\\mathrm{m}$')}",
        f"I型线密度（$P_{{10,I}}$）: {_format_value(stats.p10_i, ' $\\mathrm{m}^{-1}$')}",
        f"全部线密度（$P_{{10,\\mathrm{{all}}}}$）: {_format_value(stats.p10_all, ' $\\mathrm{m}^{-1}$')}",
        f"面密度（$P_{{20}}$）: {_format_value(stats.p20, ' $\\mathrm{m}^{-2}$')}",
        f"估算体密度（$P_{{21,\\mathrm{{est}}}}$）: {_format_value(stats.p21_est, ' $\\mathrm{m}^{-1}$')}",
        f"实测体密度（$P_{{21,\\mathrm{{obs}}}}$）: {_format_value(stats.p21_obs, ' $\\mathrm{m}^{-1}$')}",
    )
