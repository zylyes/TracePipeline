"""凸包面积计算。"""
from __future__ import annotations

import math

import numpy as np

from ._stat_types import _EPS

__all__: list[str] = []


def _cross_2d(a: np.ndarray, b: np.ndarray) -> float:
    """二维向量叉积（标量值）。"""
    return float(a[0] * b[1] - a[1] * b[0])


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
            while len(half) >= 2 and _cross_2d(half[-1] - half[-2], point - half[-1]) <= _EPS:
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


def _is_hull_geometrically_valid(local_segments: np.ndarray, hull_area: float) -> bool:
    """检查凸包几何质量：点数足够、非退化、面积有限。"""
    if not (math.isfinite(hull_area) and hull_area > _EPS):
        return False
    points = np.asarray(local_segments, dtype=float).reshape(-1, 2)
    if points.shape[0] < 3 or not np.isfinite(points).all():
        return False
    unique_points = np.unique(points, axis=0)
    return int(unique_points.shape[0]) >= 3
