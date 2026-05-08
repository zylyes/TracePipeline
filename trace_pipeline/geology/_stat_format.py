"""统计结果格式化输出。"""
from __future__ import annotations

import math

from ._stat_types import TraceStatistics

__all__ = ["format_statistics_box_lines"]

_SOURCE_LABELS = {
    "window": "圆窗",
    "measured": "实测",
    "endpoint": "端点",
    "hull": "凸包",
    "segment": "测段",
    "estimated": "估算",
}

_WINDOW_STRATEGY_LABELS = {
    "auto": "自动",
    "tangent": "切线圆窗",
    "hybrid": "混合圆窗",
    "concentric": "同心圆窗",
}


def _format_value(value: float, unit: str = "") -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.3f}{unit}"


def _format_angle(value: float) -> str:
    if not math.isfinite(float(value)):
        return "N/A"
    return f"{value:.1f}°"


def _source_suffix(source: str) -> str:
    label = _SOURCE_LABELS.get(source)
    return f"（{label}）" if label else ""


def _window_strategy_label(strategy: str) -> str:
    return _WINDOW_STRATEGY_LABELS.get(strategy, strategy)


def format_statistics_box_lines(stats: TraceStatistics) -> tuple[str, ...]:
    """格式化迹线统计框文本。"""
    _u_m = r" $\mathrm{m}$"
    _u_m2 = r" $\mathrm{m}^{2}$"
    _u_m_inv = r" $\mathrm{m}^{-1}$"
    _u_m2_inv = r" $\mathrm{m}^{-2}$"
    return (
        f"测线走向: {_format_angle(stats.scanline_azimuth)}",
        f"迹线数量: {stats.total_count}",
        f"平均迹线长度{_source_suffix(stats.trace_length_source)}: {_format_value(stats.mean_trace_length, _u_m)}",
        f"I/II/III型裂隙数: {stats.type_i_count}/{stats.type_ii_count}/{stats.type_iii_count}",
        f"测线长度: {_format_value(stats.scanline_length, _u_m)}",
        f"露头面积: {_format_value(stats.outcrop_area, _u_m2)}",
        f"圆窗策略: {_window_strategy_label(stats.window_strategy)}",
        f"线密度（$P_{{10}}$）: {_format_value(stats.p10, _u_m_inv)}",
        f"面密度（$P_{{20}}$）{_source_suffix(stats.p20_source)}: {_format_value(stats.p20, _u_m2_inv)}",
        f"面累计长度密度（$P_{{21}}$）{_source_suffix(stats.p21_source)}: {_format_value(stats.p21, _u_m_inv)}",
    )
