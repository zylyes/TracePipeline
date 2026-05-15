"""几何运算子包。"""
from __future__ import annotations

from .segments import (
    SegmentIntersection,
    collinear_overlap,
    cross2d,
    is_degenerate_segment,
    point_segment_distance,
    segment_intersection,
)

__all__ = [
    "SegmentIntersection",
    "collinear_overlap",
    "cross2d",
    "is_degenerate_segment",
    "point_segment_distance",
    "segment_intersection",
]
