"""凸包面积计算。"""
from __future__ import annotations

import math

import numpy as np

from ._stat_types import _EPS

def _cross_2d(a: np.ndarray, b: np.ndarray) -> float:
    """二维向量叉积（标量值）。"""
    return float(a[0] * b[1] - a[1] * b[0])


def _compute_convex_hull(local_segments: np.ndarray) -> np.ndarray | None:
    """构建端点凸包，返回顶点数组；退化时返回 None。"""
    if local_segments.size == 0:
        return None

    points = np.asarray(local_segments, dtype=float).reshape(-1, 2)
    if points.shape[0] < 3 or not np.isfinite(points).all():
        return None

    points = np.unique(points, axis=0)
    if points.shape[0] < 3:
        return None

    order = np.lexsort((points[:, 1], points[:, 0]))
    points = points[order]

    def build_half(iterable: np.ndarray) -> list[np.ndarray]:
        half: list[np.ndarray] = []
        for point in iterable:
            while len(half) >= 2 and _cross_2d(half[-1] - half[-2], point - half[-1]) < -_EPS:
                half.pop()
            half.append(point)
        return half

    lower = build_half(points)
    upper = build_half(points[::-1])
    hull = np.asarray(lower[:-1] + upper[:-1], dtype=float)
    if hull.shape[0] < 3:
        return None
    return hull


def _shoelace_area(hull_vertices: np.ndarray) -> float:
    """中心化 Shoelace 公式计算凸包面积，提高大坐标精度。"""
    hull = np.asarray(hull_vertices, dtype=float)
    if hull.shape[0] < 3:
        return math.nan

    centered = hull - hull.mean(axis=0)
    area = abs(_signed_area(centered))
    return area if math.isfinite(area) and area > _EPS else math.nan


def _hull_perimeter(hull_vertices: np.ndarray) -> float:
    """计算凸包多边形周长（按顶点顺序）。"""
    points = np.asarray(hull_vertices, dtype=float)
    if points.shape[0] < 2:
        return 0.0
    diffs = np.diff(points, axis=0, append=points[:1])
    return float(np.sum(np.linalg.norm(diffs, axis=1)))


def _signed_area(hull_vertices: np.ndarray) -> float:
    """返回有符号多边形面积，逆时针为正。"""
    hull = np.asarray(hull_vertices, dtype=float)
    if hull.shape[0] < 3:
        return math.nan
    x = hull[:, 0]
    y = hull[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _convex_hull_area(local_segments: np.ndarray) -> float:
    """返回端点凸包面积；点数不足或共线时返回 NaN。"""
    hull = _compute_convex_hull(local_segments)
    if hull is None:
        return math.nan
    return _shoelace_area(hull)


def _aspect_ratio(points: np.ndarray) -> float:
    """计算点集的主轴长宽比（主成分分析）。"""
    pts = np.asarray(points, dtype=float)
    if pts.shape[0] < 3:
        return math.inf
    centered = pts - pts.mean(axis=0)
    cov = np.cov(centered.T)
    if cov.ndim < 2 or cov.shape != (2, 2):
        return math.inf
    eigenvalues = np.linalg.eigvalsh(cov)
    eigenvalues = np.sort(eigenvalues)[::-1]
    if eigenvalues[1] < _EPS:
        return math.inf
    return float(np.sqrt(eigenvalues[0] / eigenvalues[1]))


def _buffered_hull_area(hull_vertices: np.ndarray, buffer_distance: float) -> float:
    """基于 Minkowski 和近似计算缓冲后凸包面积。"""
    if buffer_distance <= _EPS:
        return _shoelace_area(hull_vertices)

    area = _shoelace_area(hull_vertices)
    if not math.isfinite(area):
        return math.nan

    perimeter = _hull_perimeter(hull_vertices)
    return area + perimeter * buffer_distance + math.pi * buffer_distance ** 2


def _buffered_hull_vertices(
    hull_vertices: np.ndarray,
    buffer_distance: float,
    *,
    max_arc_degrees: float = 6.0,
) -> np.ndarray | None:
    """生成用于绘图的缓冲凸包边界顶点。

    该边界是凸包与半径 ``buffer_distance`` 圆盘的 Minkowski 和的折线近似，
    面积与 ``_buffered_hull_area`` 的解析值在绘图精度内一致。
    """
    vertices = np.asarray(hull_vertices, dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 2 or vertices.shape[0] < 3:
        return None
    if not np.isfinite(vertices).all():
        return None

    distance = float(buffer_distance)
    if not math.isfinite(distance) or distance < 0.0:
        return None
    if distance <= _EPS:
        return vertices.copy()

    signed_area = _signed_area(vertices)
    if not math.isfinite(signed_area) or abs(signed_area) <= _EPS:
        return None
    if signed_area < 0.0:
        vertices = vertices[::-1]

    max_arc_radians = max(math.radians(max_arc_degrees), math.radians(1.0))
    buffered: list[np.ndarray] = []
    count = vertices.shape[0]
    for idx, current in enumerate(vertices):
        previous = vertices[(idx - 1) % count]
        following = vertices[(idx + 1) % count]

        prev_edge = current - previous
        next_edge = following - current
        prev_length = float(np.linalg.norm(prev_edge))
        next_length = float(np.linalg.norm(next_edge))
        if prev_length <= _EPS or next_length <= _EPS:
            continue

        prev_unit = prev_edge / prev_length
        next_unit = next_edge / next_length
        prev_normal = np.array([prev_unit[1], -prev_unit[0]], dtype=float)
        next_normal = np.array([next_unit[1], -next_unit[0]], dtype=float)

        start = math.atan2(prev_normal[1], prev_normal[0])
        end = math.atan2(next_normal[1], next_normal[0])
        while end < start:
            end += 2.0 * math.pi
        span = end - start
        if span > math.pi:
            span -= 2.0 * math.pi
            end = start + span

        steps = max(2, int(math.ceil(abs(span) / max_arc_radians)) + 1)
        for angle in np.linspace(start, end, steps):
            buffered.append(current + distance * np.array([math.cos(angle), math.sin(angle)]))

    if len(buffered) < 3:
        return None

    result = np.asarray(buffered, dtype=float)
    if not np.isfinite(result).all():
        return None
    return result


def _is_hull_geometrically_valid(
    local_segments: np.ndarray,
    hull_area: float,
    max_aspect_ratio: float = 15.0,
) -> bool:
    """检查凸包几何质量：点数足够、非退化、面积有限、非极度狭长。"""
    if not (math.isfinite(hull_area) and hull_area > _EPS):
        return False

    points = np.asarray(local_segments, dtype=float).reshape(-1, 2)
    if points.shape[0] < 3 or not np.isfinite(points).all():
        return False

    unique_points = np.unique(points, axis=0)
    if int(unique_points.shape[0]) < 3:
        return False

    hull = _compute_convex_hull(local_segments)
    if hull is None or hull.shape[0] < 3:
        return False

    return _aspect_ratio(hull) <= max_aspect_ratio
