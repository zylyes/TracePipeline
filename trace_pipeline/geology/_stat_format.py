"""统计结果格式化输出。"""
from __future__ import annotations

import math

from ._stat_types import TraceStatistics

__all__ = ["format_statistics_box_lines"]

_UNIT_M = "m"
_UNIT_M2 = "m²"
_UNIT_M_INV = "m⁻¹"
_UNIT_M2_INV = "m⁻²"


def _format_stat_display_value(value: float, unit: str = "") -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.3f} {unit}".rstrip()


def _format_angle(value: float) -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.1f}°"


def format_statistics_box_lines(stats: TraceStatistics) -> tuple[str, ...]:
    """格式化迹线统计框文本，仅输出核心指标。"""
    return (
        f"测线走向: {_format_angle(stats.scanline_azimuth)}",
        f"迹线数量: {stats.total_count}",
        f"平均迹线长度: {_format_stat_display_value(stats.mean_trace_length, _UNIT_M)}",
        f"I/II/III型裂隙数: {stats.type_i_count}/{stats.type_ii_count}/{stats.type_iii_count}",
        f"测线长度: {_format_stat_display_value(stats.scanline_length, _UNIT_M)}",
        f"露头面积: {_format_stat_display_value(stats.outcrop_area, _UNIT_M2)}",
        f"线密度（$P_{{10}}$）: {_format_stat_display_value(stats.p10, _UNIT_M_INV)}",
        f"面密度（$P_{{20}}$）: {_format_stat_display_value(stats.p20, _UNIT_M2_INV)}",
        f"面累计长度密度（$P_{{21}}$）: {_format_stat_display_value(stats.p21, _UNIT_M_INV)}",
    )
