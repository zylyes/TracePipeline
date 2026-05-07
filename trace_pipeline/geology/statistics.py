"""迹线图统计指标计算。

本模块基于测线局部坐标系计算综合法 I/II/III 分型、圆形取样窗计数
以及 P10/P20/P21 相关指标。测线有限段按 [0, L_hat] 处理。
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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
logger = logging.getLogger(__name__)
_WINDOW_STRATEGIES = ("tangent", "hybrid", "concentric")
_AUTO_TIE_TOLERANCE = 0.12


@dataclass(frozen=True)
class TraceStatisticsConfig:
    """迹线统计计算参数。"""

    cut_fractions: Sequence[float] = (0.25, 0.5, 0.75)
    radius_fractions: Sequence[float] = (1.0, 0.75, 0.5)
    min_intersections: int = 5
    window_strategy: str = "auto"
    auto_density_threshold: float = 5.0
    tangent_window_count: int = 3

    def __post_init__(self) -> None:
        cut_fractions = tuple(float(v) for v in self.cut_fractions)
        radius_fractions = tuple(float(v) for v in self.radius_fractions)
        window_strategy = str(self.window_strategy).strip().lower()
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
        if window_strategy not in {"auto", "tangent", "hybrid", "concentric"}:
            raise ValueError("window_strategy 必须为 auto/tangent/hybrid/concentric")
        auto_density_threshold = float(self.auto_density_threshold)
        if not math.isfinite(auto_density_threshold) or auto_density_threshold <= 0.0:
            raise ValueError("auto_density_threshold 必须为正数")
        tangent_window_count = int(self.tangent_window_count)
        if tangent_window_count <= 0:
            raise ValueError("tangent_window_count 必须为正整数")
        object.__setattr__(self, "cut_fractions", cut_fractions)
        object.__setattr__(self, "radius_fractions", radius_fractions)
        object.__setattr__(self, "min_intersections", int(self.min_intersections))
        object.__setattr__(self, "window_strategy", window_strategy)
        object.__setattr__(self, "auto_density_threshold", auto_density_threshold)
        object.__setattr__(self, "tangent_window_count", tangent_window_count)


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
    p21: float
    l_est: float
    strategy: str
    group_key: str
    valid: bool
    reason: str = ""


@dataclass(frozen=True)
class _WindowStrategyScore:
    strategy: str
    score: float
    valid_group_count: int
    valid_window_count: int


@dataclass(frozen=True)
class TraceStatistics:
    """迹线图统计结果。"""

    scanline_azimuth: float
    total_count: int
    type_i_count: int
    type_ii_count: int
    type_iii_count: int
    scanline_length: float
    outcrop_area: float
    mean_trace_length: float
    trace_length_total: float
    p10: float
    p20: float
    p21: float
    scanline_length_source: str
    outcrop_area_source: str
    trace_length_source: str
    p20_source: str
    p21_source: str
    window_strategy: str
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


def _convex_hull_area(local_segments: np.ndarray) -> float:
    """返回端点凸包面积；点数不足或共线时返回 NaN。"""
    if local_segments.size == 0:
        return math.nan

    points = np.asarray(local_segments, dtype=float).reshape(-1, 2)
    if points.shape[0] < 3 or not np.isfinite(points).all():
        return math.nan

    points = np.unique(points, axis=0)
    if points.shape[0] < 3:
        return math.nan

    order = np.lexsort((points[:, 1], points[:, 0]))
    points = points[order]

    def build_half(iterable: np.ndarray) -> list[np.ndarray]:
        half: list[np.ndarray] = []
        for point in iterable:
            while len(half) >= 2 and _cross(half[-1] - half[-2], point - half[-1]) <= _EPS:
                half.pop()
            half.append(point)
        return half

    lower = build_half(points)
    upper = build_half(points[::-1])
    hull = np.asarray(lower[:-1] + upper[:-1], dtype=float)
    if hull.shape[0] < 3:
        return math.nan

    x = hull[:, 0]
    y = hull[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    return area if math.isfinite(area) and area > _EPS else math.nan


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
    center: np.ndarray,
    radius: float,
    min_intersections: int,
    strategy: str,
    group_key: str,
) -> CircleWindowDiagnostic:
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
    p21 = math.nan
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
        p21 = q / (4.0 * radius)
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
        p21=float(p21),
        l_est=float(l_est),
        strategy=strategy,
        group_key=group_key,
        valid=valid,
        reason=reason,
    )


def _invalid_window(
    cut_position: float,
    side: str,
    reason: str,
    *,
    strategy: str,
    group_key: str,
    center_x: float | None = None,
    center_y: float | None = None,
    radius: float | None = None,
) -> CircleWindowDiagnostic:
    return CircleWindowDiagnostic(
        cut_position=cut_position,
        side=side,
        center_x=float(cut_position if center_x is None else center_x),
        center_y=float(math.nan if center_y is None else center_y),
        radius=float(math.nan if radius is None else radius),
        intersection_count=0,
        n0=0,
        n1=0,
        n2=0,
        m=0,
        q=0,
        p20=math.nan,
        p21=math.nan,
        l_est=math.nan,
        strategy=strategy,
        group_key=group_key,
        valid=False,
        reason=reason,
    )


def _side_height(local_segments: np.ndarray, sign: float) -> float:
    y_values = local_segments[:, [1, 3]].ravel()
    side_values = y_values[y_values * sign > _EPS]
    if side_values.size == 0:
        return 0.0
    return float(np.max(np.abs(side_values)))


def _max_abs_y(local_segments: np.ndarray) -> float:
    if local_segments.size == 0:
        return 0.0
    y_values = np.asarray(local_segments[:, [1, 3]].ravel(), dtype=float)
    if y_values.size == 0:
        return 0.0
    return float(np.max(np.abs(y_values)))


def _tangent_radius(scanline_length: float, config: TraceStatisticsConfig) -> float:
    if not math.isfinite(float(scanline_length)) or scanline_length <= _EPS:
        return math.nan
    return float(scanline_length) / (2.0 * config.tangent_window_count)


def _density_preferred_strategy(
    scanline_length: float,
    trace_count: int,
    config: TraceStatisticsConfig,
    hull_area: float,
) -> str:
    rough_density = (
        trace_count / hull_area
        if math.isfinite(float(hull_area)) and hull_area > _EPS
        else math.nan
    )
    radius = _tangent_radius(scanline_length, config)
    expected_intersections = (
        rough_density * math.pi * radius * radius
        if math.isfinite(rough_density) and math.isfinite(radius)
        else 0.0
    )
    if expected_intersections < config.min_intersections:
        return "tangent"
    if rough_density < config.auto_density_threshold:
        return "hybrid"
    return "concentric"


def _select_window_strategy(
    local_segments: np.ndarray,
    scanline_length: float,
    trace_count: int,
    config: TraceStatisticsConfig,
    hull_area: float,
) -> str:
    selected_strategy, _diagnostics = _select_window_diagnostics(
        local_segments,
        scanline_length,
        trace_count,
        config,
        hull_area,
    )
    return selected_strategy


def _compute_hybrid_windows(
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
            group_key = f"hybrid:{cut_fraction:.12g}:{side}"
            if radius_max <= _EPS:
                diagnostics.append(
                    _invalid_window(
                        cut_position,
                        side,
                        "可用侧向高度或端部距离不足",
                        strategy="hybrid",
                        group_key=group_key,
                    )
                )
                continue
            for radius_fraction in config.radius_fractions:
                radius = radius_max * radius_fraction
                center = np.array([cut_position, sign * radius], dtype=float)
                diagnostics.append(
                    _count_circle_window(
                        local_segments,
                        cut_position,
                        side,
                        center,
                        radius,
                        config.min_intersections,
                        "hybrid",
                        group_key,
                    )
                )
    return tuple(diagnostics)


def _compute_tangent_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    diagnostics = []
    radius = _tangent_radius(scanline_length, config)
    for side, sign in (("left", 1.0), ("right", -1.0)):
        side_height = _side_height(local_segments, sign)
        for index in range(config.tangent_window_count):
            group_key = f"tangent:{side}:{index}"
            cut_position = (
                radius * (2 * index + 1)
                if math.isfinite(radius)
                else math.nan
            )
            center_y = sign * radius if math.isfinite(radius) else math.nan
            if not math.isfinite(radius) or radius <= _EPS:
                diagnostics.append(
                    _invalid_window(
                        0.0,
                        side,
                        "测线长度不足",
                        strategy="tangent",
                        group_key=group_key,
                    )
                )
                continue
            if side_height + _EPS < 2.0 * radius:
                diagnostics.append(
                    _invalid_window(
                        cut_position,
                        side,
                        "可用侧向高度不足",
                        strategy="tangent",
                        group_key=group_key,
                        center_x=cut_position,
                        center_y=center_y,
                        radius=radius,
                    )
                )
                continue
            center = np.array([cut_position, center_y], dtype=float)
            diagnostics.append(
                _count_circle_window(
                    local_segments,
                    cut_position,
                    side,
                    center,
                    radius,
                    config.min_intersections,
                    "tangent",
                    group_key,
                )
            )
    return tuple(diagnostics)


def _compute_concentric_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    diagnostics = []
    cut_position = scanline_length / 2.0 if math.isfinite(float(scanline_length)) else 0.0
    center = np.array([cut_position, 0.0], dtype=float)
    radius_max = min(scanline_length / 2.0, _max_abs_y(local_segments))
    group_key = "concentric:center"
    if not math.isfinite(float(radius_max)) or radius_max <= _EPS:
        return (
            _invalid_window(
                cut_position,
                "center",
                "可用半径不足",
                strategy="concentric",
                group_key=group_key,
                center_x=cut_position,
                center_y=0.0,
            ),
        )

    for radius_fraction in config.radius_fractions:
        radius = radius_max * radius_fraction
        diagnostics.append(
            _count_circle_window(
                local_segments,
                cut_position,
                "center",
                center,
                radius,
                config.min_intersections,
                "concentric",
                group_key,
            )
        )
    return tuple(diagnostics)


def _compute_circle_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
    strategy: str,
) -> tuple[CircleWindowDiagnostic, ...]:
    if strategy == "tangent":
        return _compute_tangent_windows(local_segments, scanline_length, config)
    if strategy == "concentric":
        return _compute_concentric_windows(local_segments, scanline_length, config)
    return _compute_hybrid_windows(local_segments, scanline_length, config)


def _aggregate_window_metric(
    diagnostics: Sequence[CircleWindowDiagnostic],
    attr: str,
) -> float:
    grouped: Mapping[str, list[float]] = defaultdict(list)
    for diagnostic in diagnostics:
        if diagnostic.valid:
            value = float(getattr(diagnostic, attr))
            if math.isfinite(value):
                grouped[diagnostic.group_key].append(value)
    if not grouped:
        return math.nan

    group_means = [float(np.mean(values)) for values in grouped.values() if values]
    return float(np.mean(group_means)) if group_means else math.nan


def _valid_group_keys(diagnostics: Sequence[CircleWindowDiagnostic]) -> set[str]:
    return {diagnostic.group_key for diagnostic in diagnostics if diagnostic.valid}


def _valid_group_metric_values(
    diagnostics: Sequence[CircleWindowDiagnostic],
    attr: str,
) -> list[float]:
    grouped: Mapping[str, list[float]] = defaultdict(list)
    for diagnostic in diagnostics:
        if not diagnostic.valid:
            continue
        value = float(getattr(diagnostic, attr))
        if math.isfinite(value):
            grouped[diagnostic.group_key].append(value)
    return [float(np.mean(values)) for values in grouped.values() if values]


def _side_coverage_score(diagnostics: Sequence[CircleWindowDiagnostic]) -> float:
    valid = [diagnostic for diagnostic in diagnostics if diagnostic.valid]
    if not valid:
        return 0.0

    if any(diagnostic.side == "center" for diagnostic in valid):
        return 0.85

    left_groups = {
        diagnostic.group_key for diagnostic in valid if diagnostic.side == "left"
    }
    right_groups = {
        diagnostic.group_key for diagnostic in valid if diagnostic.side == "right"
    }
    covered_side_count = int(bool(left_groups)) + int(bool(right_groups))
    if covered_side_count == 0:
        return 0.0
    if covered_side_count == 1:
        return 0.25

    balance = min(len(left_groups), len(right_groups)) / max(
        len(left_groups),
        len(right_groups),
    )
    return 0.5 + 0.5 * balance


def _along_coverage_score(
    diagnostics: Sequence[CircleWindowDiagnostic],
    scanline_length: float,
) -> float:
    if scanline_length <= _EPS:
        return 0.0

    bins = set()
    for diagnostic in diagnostics:
        if not diagnostic.valid or not math.isfinite(float(diagnostic.cut_position)):
            continue
        position = diagnostic.cut_position / scanline_length
        if position < 1.0 / 3.0:
            bins.add(0)
        elif position <= 2.0 / 3.0:
            bins.add(1)
        else:
            bins.add(2)
    return len(bins) / 3.0


def _spatial_coverage_score(
    diagnostics: Sequence[CircleWindowDiagnostic],
    scanline_length: float,
) -> float:
    return (
        _side_coverage_score(diagnostics)
        + _along_coverage_score(diagnostics, scanline_length)
    ) / 2.0


def _stability_score(diagnostics: Sequence[CircleWindowDiagnostic]) -> float:
    scores = []
    for attr in ("l_est", "p20", "p21"):
        values = np.asarray(_valid_group_metric_values(diagnostics, attr), dtype=float)
        if values.size == 0:
            continue
        if values.size == 1:
            scores.append(1.0)
            continue
        mean_abs = abs(float(np.mean(values)))
        if mean_abs <= _EPS:
            continue
        coefficient_of_variation = float(np.std(values)) / mean_abs
        scores.append(1.0 / (1.0 + coefficient_of_variation))
    return float(np.mean(scores)) if scores else 0.0


def _sample_sufficiency_score(
    diagnostics: Sequence[CircleWindowDiagnostic],
    min_intersections: int,
) -> float:
    valid_counts = [
        diagnostic.intersection_count for diagnostic in diagnostics if diagnostic.valid
    ]
    if not valid_counts:
        return 0.0
    target = max(1, 2 * int(min_intersections))
    ratios = [min(1.0, count / target) for count in valid_counts]
    return float(np.mean(ratios))


def _radius_score(
    diagnostics: Sequence[CircleWindowDiagnostic],
    max_radius: float,
) -> float:
    if not math.isfinite(max_radius) or max_radius <= _EPS:
        return 0.0
    radii = [
        float(diagnostic.radius)
        for diagnostic in diagnostics
        if diagnostic.valid and math.isfinite(float(diagnostic.radius))
    ]
    if not radii:
        return 0.0
    return min(1.0, float(np.median(radii)) / max_radius)


def _score_window_strategy(
    strategy: str,
    diagnostics: tuple[CircleWindowDiagnostic, ...],
    scanline_length: float,
    config: TraceStatisticsConfig,
    *,
    max_valid_groups: int,
    max_radius: float,
) -> _WindowStrategyScore:
    valid_groups = _valid_group_keys(diagnostics)
    valid_group_count = len(valid_groups)
    valid_window_count = sum(1 for diagnostic in diagnostics if diagnostic.valid)
    all_groups = {diagnostic.group_key for diagnostic in diagnostics}
    valid_group_score = (
        valid_group_count / max_valid_groups
        if max_valid_groups > 0
        else 0.0
    )
    valid_group_ratio = (
        valid_group_count / len(all_groups)
        if all_groups
        else 0.0
    )
    score = (
        1.45 * valid_group_score
        + 1.00 * valid_group_ratio
        + 1.35 * _spatial_coverage_score(diagnostics, scanline_length)
        + 1.10 * _stability_score(diagnostics)
        + 1.00 * _radius_score(diagnostics, max_radius)
        + 1.10 * _sample_sufficiency_score(diagnostics, config.min_intersections)
    )
    return _WindowStrategyScore(
        strategy=strategy,
        score=float(score),
        valid_group_count=valid_group_count,
        valid_window_count=valid_window_count,
    )


def _select_window_diagnostics(
    local_segments: np.ndarray,
    scanline_length: float,
    trace_count: int,
    config: TraceStatisticsConfig,
    hull_area: float,
) -> tuple[str, tuple[CircleWindowDiagnostic, ...]]:
    if config.window_strategy != "auto":
        selected = config.window_strategy
        return selected, _compute_circle_windows(
            local_segments,
            scanline_length,
            config,
            selected,
        )

    diagnostics_by_strategy = {
        strategy: _compute_circle_windows(
            local_segments,
            scanline_length,
            config,
            strategy,
        )
        for strategy in _WINDOW_STRATEGIES
    }
    preferred = _density_preferred_strategy(
        scanline_length,
        trace_count,
        config,
        hull_area,
    )
    max_valid_groups = max(
        len(_valid_group_keys(diagnostics))
        for diagnostics in diagnostics_by_strategy.values()
    )
    finite_radii = [
        float(diagnostic.radius)
        for diagnostics in diagnostics_by_strategy.values()
        for diagnostic in diagnostics
        if diagnostic.valid and math.isfinite(float(diagnostic.radius))
    ]
    max_radius = max(finite_radii) if finite_radii else math.nan
    scores = [
        _score_window_strategy(
            strategy,
            diagnostics,
            scanline_length,
            config,
            max_valid_groups=max_valid_groups,
            max_radius=max_radius,
        )
        for strategy, diagnostics in diagnostics_by_strategy.items()
    ]
    viable_scores = [score for score in scores if score.valid_group_count > 0]
    if not viable_scores:
        logger.debug("auto 圆窗策略无有效候选，回退到密度偏好: %s", preferred)
        return preferred, diagnostics_by_strategy[preferred]

    best = max(
        viable_scores,
        key=lambda item: (item.score, item.valid_group_count, item.valid_window_count),
    )
    tolerance = max(_AUTO_TIE_TOLERANCE, abs(best.score) * 0.03)
    preferred_score = next(
        (score for score in viable_scores if score.strategy == preferred),
        None,
    )
    selected = (
        preferred
        if preferred_score is not None and best.score - preferred_score.score <= tolerance
        else best.strategy
    )
    logger.debug(
        "auto 圆窗策略评分: %s；密度偏好=%s；选择=%s",
        ", ".join(
            f"{score.strategy}={score.score:.3f}"
            f"(groups={score.valid_group_count}, windows={score.valid_window_count})"
            for score in scores
        ),
        preferred,
        selected,
    )
    return selected, diagnostics_by_strategy[selected]


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


def _format_value(value: float, unit: str = "") -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.3f}{unit}"


_SOURCE_LABELS = {
    "window": "W",
    "measured": "M",
    "endpoint": "M",
    "hull": "E",
    "segment": "E",
    "estimated": "E",
}


def _source_suffix(source: str) -> str:
    label = _SOURCE_LABELS.get(source)
    return f"({label})" if label else ""


def format_statistics_box_lines(stats: TraceStatistics) -> tuple[str, ...]:
    """格式化迹线统计框文本。"""
    return (
        f"测线走向: {_format_value(stats.scanline_azimuth, '°')}",
        f"迹线数量: {stats.total_count}",
        f"平均迹线长度{_source_suffix(stats.trace_length_source)}: {_format_value(stats.mean_trace_length, ' $\\mathrm{m}$')}",
        f"I/II/III型裂隙数: {stats.type_i_count}/{stats.type_ii_count}/{stats.type_iii_count}",
        f"测线长度: {_format_value(stats.scanline_length, ' $\\mathrm{m}$')}",
        f"露头面积: {_format_value(stats.outcrop_area, ' $\\mathrm{m}^{2}$')}",
        f"圆窗策略: {stats.window_strategy}",
        f"线密度（$P_{{10}}$）: {_format_value(stats.p10, ' $\\mathrm{m}^{-1}$')}",
        f"面密度（$P_{{20}}$）{_source_suffix(stats.p20_source)}: {_format_value(stats.p20, ' $\\mathrm{m}^{-2}$')}",
        f"面累计长度密度（$P_{{21}}$）{_source_suffix(stats.p21_source)}: {_format_value(stats.p21, ' $\\mathrm{m}^{-1}$')}",
    )
