"""凸包面积计算。"""
from __future__ import annotations

import math

import numpy as np

from ._geometry_utils import _EPS, cross_2d

__all__ = ["convex_hull_area"]


def convex_hull_area(local_segments: np.ndarray) -> float:
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
            while len(half) >= 2 and cross_2d(half[-1] - half[-2], point - half[-1]) <= _EPS:
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
