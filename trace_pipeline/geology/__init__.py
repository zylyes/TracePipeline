"""地质/几何算法子包：角度转换、端点计算、坐标变换。"""
from .angles import (
    azimuth_to_cartesian_deg,
    dip_to_strike,
    fold_strike_angle,
    fold_strikes_to_semicircle,
    fold_to_halfplane,
)
from .endpoints import compute_endpoints
from .statistics import (
    CircleWindowDiagnostic,
    TraceStatistics,
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from .transforms import normalize_coordinates, rotate_and_shift, shift_to_positive

__all__ = [
    "CircleWindowDiagnostic",
    "TraceStatistics",
    "TraceStatisticsConfig",
    "azimuth_to_cartesian_deg",
    "compute_endpoints",
    "compute_trace_statistics",
    "dip_to_strike",
    "format_statistics_box_lines",
    "fold_strike_angle",
    "fold_strikes_to_semicircle",
    "fold_to_halfplane",
    "normalize_coordinates",
    "rotate_and_shift",
    "shift_to_positive",
]
