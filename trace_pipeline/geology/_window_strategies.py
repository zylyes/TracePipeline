"""圆形取样窗策略 — 三种策略布局与分发。"""
from __future__ import annotations

import math

import numpy as np

from ._circle_window import (
    _count_circle_window,
    _invalid_window,
    _max_abs_y,
    _side_height,
    _tangent_radius,
)
from ._geometry_utils import _EPS
from ._stat_types import CircleWindowDiagnostic, TraceStatisticsConfig

__all__ = ["compute_circle_windows"]


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
