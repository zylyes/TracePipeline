"""几何运算 — 线段校验、叉积、参数化相交、点到线段距离。"""
from __future__ import annotations

import logging
from typing import NamedTuple

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "SegmentIntersection",
    "cross2d",
    "segment_intersection",
    "point_segment_distance",
    "collinear_overlap",
    "is_degenerate_segment",
]


class SegmentIntersection(NamedTuple):
    """线段相交事件。"""

    t: float  # 在线段 A 上的参数 [0, 1]
    u: float  # 在线段 B 上的参数 [0, 1]
    px: float  # 交点 x 坐标
    py: float  # 交点 y 坐标
    kind: str  # "endpoint" | "internal" | "parallel_overlap"


def cross2d(ax: float, ay: float, bx: float, by: float) -> float:
    """二维叉积。"""
    return ax * by - ay * bx


def is_degenerate_segment(x1: float, y1: float, x2: float, y2: float, tol: float = 1e-9) -> bool:
    """判断线段是否退化（长度小于容差）。"""
    return (x2 - x1) ** 2 + (y2 - y1) ** 2 < tol * tol


def segment_intersection(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    tol: float = 1e-9,
) -> SegmentIntersection | None:
    """计算两条线段的相交事件。

    使用参数化方法求解:
        A(t) = a1 + t*(a2-a1)
        B(u) = b1 + u*(b2-b1)

    Returns:
        SegmentIntersection 若两线段存在有效相交/接触;
        None 若平行无交或退化。
    """
    x1, y1 = a1
    x2, y2 = a2
    x3, y3 = b1
    x4, y4 = b2

    dx1 = x2 - x1
    dy1 = y2 - y1
    dx2 = x4 - x3
    dy2 = y4 - y3
    dx3 = x3 - x1
    dy3 = y3 - y1

    denom = cross2d(dx1, dy1, dx2, dy2)

    # 平行（含共线）
    if abs(denom) < tol:
        # 检查是否共线
        if abs(cross2d(dx3, dy3, dx1, dy1)) < tol:
            return collinear_overlap(a1, a2, b1, b2, tol)
        return None

    t = cross2d(dx3, dy3, dx2, dy2) / denom
    u = cross2d(dx3, dy3, dx1, dy1) / denom

    # 容差范围内视为有效相交
    if -tol <= t <= 1.0 + tol and -tol <= u <= 1.0 + tol:
        px = x1 + t * dx1
        py = y1 + t * dy1
        # clamp 到 [0,1]
        t_clamped = max(0.0, min(1.0, t))
        u_clamped = max(0.0, min(1.0, u))
        kind = "endpoint" if (t_clamped <= tol or t_clamped >= 1.0 - tol or u_clamped <= tol or u_clamped >= 1.0 - tol) else "internal"
        return SegmentIntersection(t=t_clamped, u=u_clamped, px=px, py=py, kind=kind)

    return None


def collinear_overlap(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    tol: float = 1e-9,
) -> list[tuple[tuple[float, float], float, float]]:
    """对两条共线线段计算重叠边界点。

    返回重叠区间的两个端点（若存在重叠），每个端点附带其在两条线段上的投影参数。
    若完全无重叠，返回空列表。
    """
    x1, y1 = a1
    x2, y2 = a2
    x3, y3 = b1
    x4, y4 = b2

    # 投影到一维参数
    def _project(p: tuple[float, float], ref: tuple[float, float], dir_vec: tuple[float, float]) -> float:
        dx = dir_vec[0]
        dy = dir_vec[1]
        norm2 = dx * dx + dy * dy
        if norm2 < tol * tol:
            return 0.0
        return ((p[0] - ref[0]) * dx + (p[1] - ref[1]) * dy) / norm2

    dir_vec = (x2 - x1, y2 - y1)
    t1 = 0.0
    t2 = 1.0
    t3 = _project((x3, y3), (x1, y1), dir_vec)
    t4 = _project((x4, y4), (x1, y1), dir_vec)

    a_min, a_max = min(t1, t2), max(t1, t2)
    b_min, b_max = min(t3, t4), max(t3, t4)

    ov_min = max(a_min, b_min)
    ov_max = min(a_max, b_max)

    # 使用相对容差判断重叠：当线段较长时，绝对容差可能误判
    span = max(abs(a_max - a_min), abs(b_max - b_min), 1.0)
    if ov_max - ov_min > tol * max(1.0, span):
        p_min = (x1 + ov_min * dir_vec[0], y1 + ov_min * dir_vec[1])
        p_max = (x1 + ov_max * dir_vec[0], y1 + ov_max * dir_vec[1])
        # 边界点在迹线 A 上的参数
        t_min_a = ov_min
        t_max_a = ov_max
        # 边界点在迹线 B 上的参数：通过点到 b1 的向量与 b2-b1 的点积计算
        b_dir = (x4 - x3, y4 - y3)
        b_norm2 = b_dir[0] * b_dir[0] + b_dir[1] * b_dir[1]
        if b_norm2 < tol * tol:
            t_min_b = 0.0
            t_max_b = 1.0
        else:
            t_min_b = ((p_min[0] - x3) * b_dir[0] + (p_min[1] - y3) * b_dir[1]) / b_norm2
            t_max_b = ((p_max[0] - x3) * b_dir[0] + (p_max[1] - y3) * b_dir[1]) / b_norm2
        return [
            (p_min, t_min_a, t_min_b),
            (p_max, t_max_a, t_max_b),
        ]
    return []


def point_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> float:
    """点到线段的最短距离。"""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        return np.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return np.hypot(px - proj_x, py - proj_y)
