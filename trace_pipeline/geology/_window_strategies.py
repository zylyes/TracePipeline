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


class _BatchCollector:
    """收集中间参数后统一批量计算并按序组装结果。"""

    def __init__(self) -> None:
        self._invalid: list[tuple[int, CircleWindowDiagnostic]] = []
        self._centers: list[list[float]] = []
        self._radii: list[float] = []
        self._cut_positions: list[float] = []
        self._sides: list[str] = []
        self._strategies: list[str] = []
        self._group_keys: list[str] = []
        self._order: list[tuple[str, int]] = []

    def add_invalid(self, *,
        cut_position: float, side: str, reason: str,
        strategy: str, group_key: str,
        center_x: float | None = None, center_y: float | None = None, radius: float | None = None,
    ) -> None:
        idx = len(self._invalid)
        self._invalid.append((idx, _invalid_window(
            cut_position, side, reason,
            strategy=strategy, group_key=group_key,
            center_x=center_x, center_y=center_y, radius=radius,
        )))
        self._order.append(("invalid", idx))

    def add_batch(self, *,
        cut_position: float, side: str, radius: float, center_x: float, center_y: float,
        strategy: str, group_key: str,
    ) -> None:
        idx = len(self._centers)
        self._centers.append([center_x, center_y])
        self._radii.append(radius)
        self._cut_positions.append(cut_position)
        self._sides.append(side)
        self._strategies.append(strategy)
        self._group_keys.append(group_key)
        self._order.append(("batch", idx))

    def resolve(self, local_segments: np.ndarray, min_intersections: int) -> tuple[CircleWindowDiagnostic, ...]:
        if self._centers:
            batch = _count_circle_windows_batch(
                local_segments,
                np.array(self._centers, dtype=float),
                np.array(self._radii, dtype=float),
                min_intersections,
                np.array(self._cut_positions, dtype=float),
                self._sides,
                self._strategies,
                self._group_keys,
            )
        else:
            batch = []
        diagnostics = []
        for kind, idx in self._order:
            if kind == "invalid":
                diagnostics.append(self._invalid[idx][1])
            else:
                diagnostics.append(batch[idx])
        return tuple(diagnostics)


def _compute_hybrid_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    coll = _BatchCollector()
    for cut_fraction in config.cut_fractions:
        cut_position = scanline_length * cut_fraction
        edge_limit = min(cut_position, scanline_length - cut_position)
        for side, sign in (("left", 1.0), ("right", -1.0)):
            side_height = _side_height(local_segments, sign)
            radius_max = min(side_height / 2.0, edge_limit)
            group_key = f"hybrid:{cut_fraction:.12g}:{side}"
            if radius_max <= _EPS:
                coll.add_invalid(
                    cut_position=cut_position, side=side,
                    reason="可用侧向高度或端部距离不足",
                    strategy="hybrid", group_key=group_key,
                )
                continue
            for radius_fraction in config.radius_fractions:
                radius = radius_max * radius_fraction
                coll.add_batch(
                    cut_position=cut_position, side=side, radius=radius,
                    center_x=cut_position, center_y=sign * radius,
                    strategy="hybrid", group_key=group_key,
                )
    return coll.resolve(local_segments, config.min_intersections)


def _compute_tangent_windows(
    local_segments: np.ndarray,
    scanline_length: float,
    config: TraceStatisticsConfig,
) -> tuple[CircleWindowDiagnostic, ...]:
    radius = _tangent_radius(scanline_length, config)
    coll = _BatchCollector()
    for side, sign in (("left", 1.0), ("right", -1.0)):
        side_height = _side_height(local_segments, sign)
        for index in range(config.tangent_window_count):
            group_key = f"tangent:{side}:{index}"
            cut_position = radius * (2 * index + 1) if math.isfinite(radius) else math.nan
            center_y = sign * radius if math.isfinite(radius) else math.nan
            if not math.isfinite(radius) or radius <= _EPS:
                coll.add_invalid(
                    cut_position=0.0, side=side, reason="测线长度不足",
                    strategy="tangent", group_key=group_key,
                )
                continue
            if side_height + _EPS < 2.0 * radius:
                coll.add_invalid(
                    cut_position=cut_position, side=side, reason="可用侧向高度不足",
                    strategy="tangent", group_key=group_key,
                    center_x=cut_position, center_y=center_y, radius=radius,
                )
                continue
            coll.add_batch(
                cut_position=cut_position, side=side, radius=radius,
                center_x=cut_position, center_y=center_y,
                strategy="tangent", group_key=group_key,
            )
    return coll.resolve(local_segments, config.min_intersections)


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
