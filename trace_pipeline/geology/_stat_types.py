"""统计相关数据类型定义。"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["CircleWindowDiagnostic", "TraceStatistics", "TraceStatisticsConfig"]

_EPS = 1e-9


@dataclass(frozen=True)
class TraceStatisticsConfig:
    """迹线统计计算参数。"""

    cut_fractions: Sequence[float] = (0.25, 0.5, 0.75)
    radius_fractions: Sequence[float] = (1.0, 0.75, 0.5)
    min_intersections: int = 5
    window_strategy: str = "auto"
    auto_density_threshold: float = 5.0
    tangent_window_count: int = 3
    hull_buffer_ratio: float = 0.25
    disagreement_threshold: float | None = None
    weighted_length_min_angle: float = 20.0
    min_trace_length: float = 0.3

    def __post_init__(self) -> None:
        cut_fractions = tuple(float(v) for v in self.cut_fractions)
        radius_fractions = tuple(float(v) for v in self.radius_fractions)
        window_strategy = str(self.window_strategy).strip().lower()
        if not cut_fractions:
            raise ValueError("cut_fractions 不能为空")
        if not radius_fractions:
            raise ValueError("radius_fractions 不能为空")
        if any((not math.isfinite(v)) or v <= 0.0 or v >= 1.0 for v in cut_fractions):
            raise ValueError("cut_fractions 必须位于 (0, 1) 范围内")
        if any((not math.isfinite(v)) or v <= 0.0 for v in radius_fractions):
            raise ValueError("radius_fractions 必须为正数")
        if int(self.min_intersections) <= 0:
            raise ValueError("min_intersections 必须为正整数")
        if window_strategy not in {"auto", "tangent", "hybrid", "concentric"}:
            raise ValueError("window_strategy 必须为 auto/tangent/hybrid/concentric")
        auto_density_threshold = float(self.auto_density_threshold)
        if not math.isfinite(auto_density_threshold) or auto_density_threshold <= 0.0:
            raise ValueError("auto_density_threshold 必须为正数")
        tangent_window_count = int(self.tangent_window_count)
        if tangent_window_count <= 0:
            raise ValueError("tangent_window_count 必须为正整数")
        hull_buffer_ratio = float(self.hull_buffer_ratio)
        if not math.isfinite(hull_buffer_ratio) or hull_buffer_ratio < 0.0:
            raise ValueError("hull_buffer_ratio 必须为非负数")
        weighted_length_min_angle = float(self.weighted_length_min_angle)
        if not math.isfinite(weighted_length_min_angle) or weighted_length_min_angle <= 0.0 or weighted_length_min_angle > 90.0:
            raise ValueError("weighted_length_min_angle 必须位于 (0, 90] 范围内")
        min_trace_length = float(self.min_trace_length)
        if not math.isfinite(min_trace_length) or min_trace_length <= 0.0:
            raise ValueError("min_trace_length 必须为正数")
        disagreement_threshold = self.disagreement_threshold
        if disagreement_threshold is not None:
            disagreement_threshold = float(disagreement_threshold)
            if not math.isfinite(disagreement_threshold) or disagreement_threshold <= 0.0:
                raise ValueError("disagreement_threshold 必须为正数或 None")
        object.__setattr__(self, "cut_fractions", cut_fractions)
        object.__setattr__(self, "radius_fractions", radius_fractions)
        object.__setattr__(self, "min_intersections", int(self.min_intersections))
        object.__setattr__(self, "window_strategy", window_strategy)
        object.__setattr__(self, "auto_density_threshold", auto_density_threshold)
        object.__setattr__(self, "tangent_window_count", tangent_window_count)
        object.__setattr__(self, "hull_buffer_ratio", hull_buffer_ratio)
        object.__setattr__(self, "disagreement_threshold", disagreement_threshold)
        object.__setattr__(self, "weighted_length_min_angle", weighted_length_min_angle)
        object.__setattr__(self, "min_trace_length", min_trace_length)


@dataclass(frozen=True)
class CircleWindowDiagnostic:
    """单个圆形取样窗的计数和有效性诊断。"""

    cut_position: float
    side: str
    center_x: float
    center_y: float
    radius: float
    intersection_count: int
    n0: int  # 两端点均在圆外的相交迹线数
    n1: int  # 一端在圆内的相交迹线数
    n2: int  # 两端均在圆内的相交迹线数
    m: int   # m = n1 + 2*n2
    q: int   # q = 2*n0 + n1
    p20: float
    p21: float
    l_est: float
    strategy: str
    group_key: str
    valid: bool
    invalid_reason: str = ""


@dataclass(frozen=True)
class TraceStatistics:
    """迹线图统计结果。"""

    scanline_azimuth: float
    total_count: int
    type_i_count: int
    type_ii_count: int
    type_iii_count: int
    scanline_length: float
    outcrop_area: float
    mean_trace_length: float
    trace_length_total: float
    p10: float
    p20: float
    p21: float
    scanline_length_source: str
    outcrop_area_source: str
    trace_length_source: str
    p20_source: str
    p21_source: str
    window_strategy: str
    trace_types: tuple[str, ...]
    diagnostics: tuple[CircleWindowDiagnostic, ...]
    # ── 圆窗校验诊断字段 ──────────────────────────
    window_outcrop_area: float = 0.0
    area_disagreement_ratio: float = 0.0
    window_validation_warning: str = ""
    # ── 新增无偏估计字段 ──────────────────────────
    weighted_mean_trace_length: float = math.nan
    unbiased_mean_trace_length: float = math.nan
    p10_terzaghi: float = math.nan
    mean_sin_alpha: float = math.nan
    hull_buffered_area: float = math.nan
    hull_buffer_ratio: float = 0.0

    @property
    def valid_window_count(self) -> int:
        return sum(1 for diagnostic in self.diagnostics if diagnostic.valid)
