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
    "hull_buffered": "缓冲凸包",
    "segment": "测段",
    "estimated": "估算",
    "window_equivalent": "圆窗等效",
    "weighted": "方向修正",
    "unbiased": "无偏估计",
    "terzaghi": "Terzaghi修正",
}

_WINDOW_STRATEGY_LABELS = {
    "auto": "自动",
    "tangent": "切线圆窗",
    "hybrid": "混合圆窗",
    "concentric": "同心圆窗",
}

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


def _source_suffix(source: str) -> str:
    label = _SOURCE_LABELS.get(source)
    return f"（{label}）" if label else ""


def _window_strategy_label(strategy: str) -> str:
    return _WINDOW_STRATEGY_LABELS.get(strategy, strategy)


def _p20_p21_source_suffix(source: str, strategy: str) -> str:
    """P20/P21 来源为 window 时嵌入策略名。"""
    if source == "window":
        label = _WINDOW_STRATEGY_LABELS.get(strategy, "圆窗")
        return f"（{label}）"
    return _source_suffix(source)


def format_statistics_box_lines(stats: TraceStatistics) -> tuple[str, ...]:
    """格式化迹线统计框文本。"""
    return (
        f"测线走向: {_format_angle(stats.scanline_azimuth)}",
        f"迹线数量: {stats.total_count}",
        f"平均迹线长度{_source_suffix(stats.trace_length_source)}: {_format_stat_display_value(stats.mean_trace_length, _UNIT_M)}",
        f"I/II/III型裂隙数: {stats.type_i_count}/{stats.type_ii_count}/{stats.type_iii_count}",
        f"测线长度: {_format_stat_display_value(stats.scanline_length, _UNIT_M)}",
        f"露头面积{_source_suffix(stats.outcrop_area_source)}: {_format_stat_display_value(stats.outcrop_area, _UNIT_M2)}",
        f"线密度（$P_{{10}}$）: {_format_stat_display_value(stats.p10, _UNIT_M_INV)}",
        f"面密度（$P_{{20}}$）{_p20_p21_source_suffix(stats.p20_source, stats.window_strategy)}: {_format_stat_display_value(stats.p20, _UNIT_M2_INV)}",
        f"面累计长度密度（$P_{{21}}$）{_p20_p21_source_suffix(stats.p21_source, stats.window_strategy)}: {_format_stat_display_value(stats.p21, _UNIT_M_INV)}",
    )
