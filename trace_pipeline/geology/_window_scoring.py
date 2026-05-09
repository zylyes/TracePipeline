"""圆形取样窗评分 — 6 因子加权评分与自动策略选择。"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ._circle_window import _tangent_radius
from ._stat_types import _EPS, CircleWindowDiagnostic, TraceStatisticsConfig
from ._window_strategies import compute_circle_windows

__all__: list[str] = []

logger = logging.getLogger(__name__)
_WINDOW_STRATEGIES = ("tangent", "hybrid", "concentric")
_AUTO_TIE_TOLERANCE = 0.12

# 6 因子加权评分权重（基于 O76–O83 八个露头的对比调参确定）:
#   有效分组得分权重最高，因为有效分组是一切指标可信度的前提；
#   空间覆盖（侧向 + 沿测线）保证代表性；
#   稳定性和样本充分性保证统计指标方差受控。
_WEIGHT_VALID_GROUP = 1.45
_WEIGHT_GROUP_RATIO = 1.00
_WEIGHT_SPATIAL_COVERAGE = 1.35
_WEIGHT_STABILITY = 1.10
_WEIGHT_RADIUS = 1.00
_WEIGHT_SUFFICIENCY = 1.10


def _aggregate_window_metric(
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
    score = (
        _WEIGHT_VALID_GROUP * valid_group_score
        + _WEIGHT_GROUP_RATIO * valid_group_ratio
        + _WEIGHT_SPATIAL_COVERAGE * _spatial_coverage_score(diagnostics, scanline_length)
        + _WEIGHT_STABILITY * _stability_score(diagnostics)
        + _WEIGHT_RADIUS * _radius_score(diagnostics, max_radius)
        + _WEIGHT_SUFFICIENCY * _sample_sufficiency_score(diagnostics, config.min_intersections)
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


def _select_window_diagnostics(
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
