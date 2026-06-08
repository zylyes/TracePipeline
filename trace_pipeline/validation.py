"""通用校验与类型强制转换工具。

本模块提供纯校验函数，不依赖任何业务模块，
供 config.py 与 models.py 共同使用，避免循环概念依赖。
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

__all__ = [
    "coerce_bool",
    "coerce_positive_float",
    "coerce_positive_int",
    "coerce_node_label_mode",
    "coerce_rose_bin_width",
    "coerce_scalar_config_fields",
    "coerce_window_strategy",
]

_ScalarHandler = Callable[[Any], Any]


def coerce_bool(value: Any, name: str) -> bool:
    """将常见配置布尔写法规范化为 bool。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"{name} 必须为布尔值")


def coerce_positive_int(value: Any, name: str) -> int:
    """将 DPI 等正整数配置规范化为 int。"""
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为正整数") from exc
    if number <= 0:
        raise ValueError(f"{name} 必须为正整数")
    return number


def coerce_positive_float(value: Any, name: str) -> float:
    """将正浮点配置规范化为 float。"""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为正数") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} 必须为正数")
    return number


def coerce_window_strategy(value: Any) -> str:
    """规范化圆窗策略配置。"""
    strategy = str(value).strip().lower()
    if strategy not in {"auto", "tangent", "hybrid", "concentric"}:
        raise ValueError("window_strategy 必须为 auto/tangent/hybrid/concentric")
    return strategy


def coerce_node_label_mode(value: Any) -> str:
    """Normalize node label display mode."""
    mode = str(value).strip().lower()
    if mode not in {"none", "type", "id"}:
        raise ValueError("node_label_mode must be one of none/type/id")
    return mode


def coerce_rose_bin_width(value: Any) -> float:
    """规范化玫瑰图分箱宽度。"""
    try:
        width = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < width <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")
    return width


_SCALAR_COERCIONS: Mapping[str, _ScalarHandler] = {
    "export_rose_plot": lambda v: coerce_bool(v, "export_rose_plot"),
    "rose_bin_width": coerce_rose_bin_width,
    "rose_dpi": lambda v: coerce_positive_int(v, "rose_dpi"),
    "trace_dpi": lambda v: coerce_positive_int(v, "trace_dpi"),
    "rotated_trace_dpi": lambda v: coerce_positive_int(v, "rotated_trace_dpi"),
    "tangent_window_count": lambda v: coerce_positive_int(v, "tangent_window_count"),
    "min_intersections": lambda v: coerce_positive_int(v, "min_intersections"),
    "window_strategy": coerce_window_strategy,
    "auto_density_threshold": lambda v: coerce_positive_float(v, "auto_density_threshold"),
    "enable_node_recognition": lambda v: coerce_bool(v, "enable_node_recognition"),
    "node_merge_tolerance": lambda v: coerce_positive_float(v, "node_merge_tolerance"),
    "show_node_overlay": lambda v: coerce_bool(v, "show_node_overlay"),
    "node_label_mode": coerce_node_label_mode,
}


def coerce_scalar_config_fields(cfg: dict[str, Any]) -> None:
    """就地规范化配置字典中的标量字段（供 config 与 RunConfig 共用）。"""
    for key in _SCALAR_COERCIONS:
        if key in cfg:
            cfg[key] = _SCALAR_COERCIONS[key](cfg[key])
