"""圆形取样窗策略 — 窗口计数、策略选择与评分。"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ._stat_types import CircleWindowDiagnostic, TraceStatisticsConfig

__all__ = [
    "aggregate_window_metric",
    "classify_trace_types",
    "compute_circle_windows",
    "select_window_diagnostics",
]

_EPS = 1e-9
logger = logging.getLogger(__name__)
_WINDOW_STRATEGIES = ("tangent", "hybrid", "concentric")
_AUTO_TIE_TOLERANCE = 0.12


# ── 几何工具 ──────────────────────────────────────────────────────────


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


def classify_trace_types(local_segments: np.ndarray, scanline_length: float) -> tuple[str, ...]:
    """将迹线分为 I/II/III 型（向量化实现）。"""
    if local_segments.shape[0] == 0:
        return ()

    p1 = local_segments[:, 0:2]  # (N, 2)
    p2 = local_segments[:, 2:4]  # (N, 2)
    q1 = np.array([0.0, 0.0], dtype=float)
    q2 = np.array([scanline_length, 0.0], dtype=float)

    # ── I 型判定：迹线线段与测线线段相交 ──
    r = p2 - p1              # (N, 2)
    s = q2 - q1              # (2,)
    r_norm = np.linalg.norm(r, axis=1)  # (N,)
    s_norm = float(np.linalg.norm(s))
    qp = q1 - p1             # (N, 2)

    # 叉积
    cross_r_s = r[:, 0] * s[1] - r[:, 1] * s[0]  # (N,)
    cross_qp_s = qp[:, 0] * s[1] - qp[:, 1] * s[0]
    cross_qp_r = qp[:, 0] * r[:, 1] - qp[:, 1] * r[:, 0]

    # 退化情况：r 或 s 长度为零
    degenerate = (r_norm <= _EPS) | (s_norm <= _EPS)

    # 非平行情况
    safe_denom = np.where(np.abs(cross_r_s) > _EPS, cross_r_s, 1.0)
    t = cross_qp_s / safe_denom
    u = cross_qp_r / safe_denom
    non_parallel_intersect = (
        (np.abs(cross_r_s) > _EPS)
        & (t >= -_EPS) & (t <= 1.0 + _EPS)
        & (u >= -_EPS) & (u <= 1.0 + _EPS)
    )

    # 共线情况：叉积为零且 qp × r 也为零，检查 bbox 重叠
    collinear = (np.abs(cross_r_s) <= _EPS) & (np.abs(cross_qp_r) <= _EPS)
    # bbox 重叠检查（仅 x 轴即可，因为测线在 y=0）
    seg_x_min = np.minimum(p1[:, 0], p2[:, 0])
    seg_x_max = np.maximum(p1[:, 0], p2[:, 0])
    scanline_x_min = min(q1[0], q2[0])
    scanline_x_max = max(q1[0], q2[0])
    seg_y_min = np.minimum(p1[:, 1], p2[:, 1])
    seg_y_max = np.maximum(p1[:, 1], p2[:, 1])
    bbox_overlap = (
        (np.maximum(seg_x_min, scanline_x_min) <= np.minimum(seg_x_max, scanline_x_max) + _EPS)
        & (np.maximum(seg_y_min, 0.0) <= np.minimum(seg_y_max, 0.0) + _EPS)
    )
    collinear_intersect = collinear & bbox_overlap

    is_type_i = (~degenerate) & (non_parallel_intersect | collinear_intersect)

    # ── II 型判定：迹线所在直线与测线线段相交 ──
    # 只需检查 u 在 [0,1] 范围内（直线 vs 线段）
    line_non_parallel = (np.abs(cross_r_s) > _EPS) & (u >= -_EPS) & (u <= 1.0 + _EPS)
    # 共线情况视为直线相交
    line_collinear = (np.abs(cross_r_s) <= _EPS) & (np.abs(cross_qp_r) <= _EPS)
    is_line_intersect = (~degenerate) & (line_non_parallel | line_collinear)
    is_type_ii = (~is_type_i) & is_line_intersect

    # ── 构造标签 ──
    labels = np.where(is_type_i, "I", np.where(is_type_ii, "II", "III"))
    return tuple(labels.tolist())


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


# ── 圆窗计数 ─────────────────────────────────────────────────────────


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
    n_segs = local_segments.shape[0]
    if n_segs == 0:
        return _invalid_window(
            cut_position, side, "无迹线数据",
            strategy=strategy, group_key=group_key,
            center_x=float(center[0]), center_y=float(center[1]), radius=radius,
        )

    # 向量化：批量计算所有线段与圆的相交关系
    p1 = local_segments[:, 0:2]  # (N, 2)
    p2 = local_segments[:, 2:4]  # (N, 2)
    d1 = np.linalg.norm(p1 - center, axis=1)  # (N,)
    d2 = np.linalg.norm(p2 - center, axis=1)  # (N,)

    # 点到线段最近距离（向量化）
    seg_vec = p2 - p1  # (N, 2)
    length_sq = np.sum(seg_vec * seg_vec, axis=1)  # (N,)
    safe_length_sq = np.where(length_sq > _EPS, length_sq, 1.0)
    t = np.sum((center - p1) * seg_vec, axis=1) / safe_length_sq
    t = np.clip(t, 0.0, 1.0)
    t = np.where(length_sq > _EPS, t, 0.0)
    closest = p1 + t[:, np.newaxis] * seg_vec  # (N, 2)
    dist_to_seg = np.linalg.norm(center - closest, axis=1)  # (N,)

    # 相交判定：端点在圆内 或 线段最近点在圆内
    threshold = radius + _EPS
    intersects = (d1 <= threshold) | (d2 <= threshold) | (dist_to_seg <= threshold)

    intersection_count = int(np.sum(intersects))

    # 端点分类统计
    inside1 = d1[intersects] <= threshold
    inside2 = d2[intersects] <= threshold
    inside_count = inside1.astype(int) + inside2.astype(int)
    n0 = int(np.sum(inside_count == 0))
    n1 = int(np.sum(inside_count == 1))
    n2 = int(np.sum(inside_count == 2))

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


# ── 辅助度量 ─────────────────────────────────────────────────────────


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


# ── 三种窗口策略 ─────────────────────────────────────────────────────


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


def compute_circle_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
    strategy: str,
) -> tuple[CircleWindowDiagnostic, ...]:
    """按指定策略计算圆窗诊断。"""
    if strategy == "tangent":
        return _compute_tangent_windows(local_segments, scanline_length, config)
    if strategy == "concentric":
        return _compute_concentric_windows(local_segments, scanline_length, config)
    return _compute_hybrid_windows(local_segments, scanline_length, config)


# ── 聚合与评分 ────────────────────────────────────────────────────────


def aggregate_window_metric(
    diagnostics: Sequence[CircleWindowDiagnostic],
    attr: str,
) -> float:
    """按分组聚合诊断窗口的指标均值。"""
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


@dataclass(frozen=True)
class _WindowStrategyScore:
    strategy: str
    score: float
    valid_group_count: int
    valid_window_count: int


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
    # 圆窗策略评分因子（经验权重，基于各指标对最终迹长估计精度的影响系数）
    score = (
        1.45 * valid_group_score         # 有效组数贡献（最重要，决定样本量）
        + 1.00 * valid_group_ratio       # 有效组占比
        + 1.35 * _spatial_coverage_score(diagnostics, scanline_length)  # 空间覆盖
        + 1.10 * _stability_score(diagnostics)        # 窗口间稳定性
        + 1.00 * _radius_score(diagnostics, max_radius)  # 半径适配度
        + 1.10 * _sample_sufficiency_score(diagnostics, config.min_intersections)  # 样本充足率
    )
    return _WindowStrategyScore(
        strategy=strategy,
        score=float(score),
        valid_group_count=valid_group_count,
        valid_window_count=valid_window_count,
    )


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


def select_window_diagnostics(
    local_segments: np.ndarray,
    scanline_length: float,
    trace_count: int,
    config: TraceStatisticsConfig,
    hull_area: float,
) -> tuple[str, tuple[CircleWindowDiagnostic, ...]]:
    """选择最佳圆窗策略并返回诊断结果。"""
    if config.window_strategy != "auto":
        selected = config.window_strategy
        return selected, compute_circle_windows(
            local_segments,
            scanline_length,
            config,
            selected,
        )

    diagnostics_by_strategy = {
        strategy: compute_circle_windows(
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
