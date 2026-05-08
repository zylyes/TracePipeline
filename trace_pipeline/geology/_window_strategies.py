"""圆形取样窗策略 — 三种策略布局与分发。"""
from __future__ import annotations

import math

import numpy as np

from ._circle_window import (
    _count_circle_windows_batch,
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
    # 收集有效窗口参数与无效窗口
    invalid_diagnostics: list[tuple[int, CircleWindowDiagnostic]] = []
    batch_centers: list[list[float]] = []
    batch_radii: list[float] = []
    batch_cut_positions: list[float] = []
    batch_sides: list[str] = []
    batch_strategies: list[str] = []
    batch_group_keys: list[str] = []
    order: list[tuple[str, int]] = []  # ("invalid", idx) or ("batch", idx)

    for cut_fraction in config.cut_fractions:
        cut_position = scanline_length * cut_fraction
        edge_limit = min(cut_position, scanline_length - cut_position)
        for side, sign in (("left", 1.0), ("right", -1.0)):
            side_height = _side_height(local_segments, sign)
            radius_max = min(side_height / 2.0, edge_limit)
            group_key = f"hybrid:{cut_fraction:.12g}:{side}"
            if radius_max <= _EPS:
                idx = len(invalid_diagnostics)
                invalid_diagnostics.append((idx, _invalid_window(
                    cut_position, side, "可用侧向高度或端部距离不足",
                    strategy="hybrid", group_key=group_key,
                )))
                order.append(("invalid", idx))
                continue
            for radius_fraction in config.radius_fractions:
                radius = radius_max * radius_fraction
                idx = len(batch_centers)
                batch_centers.append([cut_position, sign * radius])
                batch_radii.append(radius)
                batch_cut_positions.append(cut_position)
                batch_sides.append(side)
                batch_strategies.append("hybrid")
                batch_group_keys.append(group_key)
                order.append(("batch", idx))

    # 批量计算
    if batch_centers:
        batch_results = _count_circle_windows_batch(
            local_segments,
            np.array(batch_centers, dtype=float),
            np.array(batch_radii, dtype=float),
            config.min_intersections,
            np.array(batch_cut_positions, dtype=float),
            batch_sides,
            batch_strategies,
            batch_group_keys,
        )
    else:
        batch_results = []

    # 按原始顺序组装结果
    diagnostics = []
    for kind, idx in order:
        if kind == "invalid":
            diagnostics.append(invalid_diagnostics[idx][1])
        else:
            diagnostics.append(batch_results[idx])
    return tuple(diagnostics)


def _compute_tangent_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    radius = _tangent_radius(scanline_length, config)

    invalid_diagnostics: list[tuple[int, CircleWindowDiagnostic]] = []
    batch_centers: list[list[float]] = []
    batch_radii: list[float] = []
    batch_cut_positions: list[float] = []
    batch_sides: list[str] = []
    batch_strategies: list[str] = []
    batch_group_keys: list[str] = []
    order: list[tuple[str, int]] = []

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
                idx = len(invalid_diagnostics)
                invalid_diagnostics.append((idx, _invalid_window(
                    0.0, side, "测线长度不足",
                    strategy="tangent", group_key=group_key,
                )))
                order.append(("invalid", idx))
                continue
            if side_height + _EPS < 2.0 * radius:
                idx = len(invalid_diagnostics)
                invalid_diagnostics.append((idx, _invalid_window(
                    cut_position, side, "可用侧向高度不足",
                    strategy="tangent", group_key=group_key,
                    center_x=cut_position, center_y=center_y, radius=radius,
                )))
                order.append(("invalid", idx))
                continue
            idx = len(batch_centers)
            batch_centers.append([cut_position, center_y])
            batch_radii.append(radius)
            batch_cut_positions.append(cut_position)
            batch_sides.append(side)
            batch_strategies.append("tangent")
            batch_group_keys.append(group_key)
            order.append(("batch", idx))

    if batch_centers:
        batch_results = _count_circle_windows_batch(
            local_segments,
            np.array(batch_centers, dtype=float),
            np.array(batch_radii, dtype=float),
            config.min_intersections,
            np.array(batch_cut_positions, dtype=float),
            batch_sides,
            batch_strategies,
            batch_group_keys,
        )
    else:
        batch_results = []

    diagnostics = []
    for kind, idx in order:
        if kind == "invalid":
            diagnostics.append(invalid_diagnostics[idx][1])
        else:
            diagnostics.append(batch_results[idx])
    return tuple(diagnostics)


def _compute_concentric_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    cut_position = scanline_length / 2.0 if math.isfinite(float(scanline_length)) else 0.0
    radius_max = min(scanline_length / 2.0, _max_abs_y(local_segments))
    group_key = "concentric:center"
    if not math.isfinite(float(radius_max)) or radius_max <= _EPS:
        return (
            _invalid_window(
                cut_position, "center", "可用半径不足",
                strategy="concentric", group_key=group_key,
                center_x=cut_position, center_y=0.0,
            ),
        )

    centers = []
    radii = []
    for radius_fraction in config.radius_fractions:
        radius = radius_max * radius_fraction
        centers.append([cut_position, 0.0])
        radii.append(radius)

    batch_results = _count_circle_windows_batch(
        local_segments,
        np.array(centers, dtype=float),
        np.array(radii, dtype=float),
        config.min_intersections,
        np.full(len(radii), cut_position, dtype=float),
        ["center"] * len(radii),
        ["concentric"] * len(radii),
        [group_key] * len(radii),
    )
    return tuple(batch_results)


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
