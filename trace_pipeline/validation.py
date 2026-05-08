"""通用校验与类型强制转换工具。

本模块提供纯校验函数，不依赖任何业务模块，
供 config.py 与 models.py 共同使用，避免循环概念依赖。
"""
from __future__ import annotations

import math
from typing import Any

__all__ = [
    "coerce_bool",
    "coerce_positive_float",
    "coerce_positive_int",
    "coerce_rose_bin_width",
    "coerce_window_strategy",
]


def coerce_bool(value: Any, name: str) -> bool:
    """将常见配置布尔写法规范化为 bool。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
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


def coerce_rose_bin_width(value: Any) -> float:
    """规范化玫瑰图分箱宽度。"""
    try:
        width = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < width <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")
    return width
