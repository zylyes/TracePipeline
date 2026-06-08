"""NumPy 类型兼容性工具。"""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = ["to_native"]


def to_native(val: Any, max_depth: int = 20, _depth: int = 0) -> Any:
    """递归将 numpy / pandas 等科学计算类型转换为原生 Python 类型。

    确保 JSON 序列化、日志记录等场景不会因 numpy 类型而失败。

    Args:
        val: 待转换的值。
        max_depth: 最大递归深度，防止循环引用导致栈溢出。
        _depth: 当前递归深度（内部使用）。

    Returns:
        转换后的原生 Python 值。
    """
    if _depth > max_depth:
        return str(val)

    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, np.bool_):
        return bool(val)

    try:
        import pandas as pd

        if isinstance(val, (pd.Timestamp,)):
            return val.isoformat()
        if isinstance(val, pd.Series):
            return val.tolist()
    except ImportError:
        pass

    if isinstance(val, dict):
        return {k: to_native(v, max_depth, _depth + 1) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [to_native(v, max_depth, _depth + 1) for v in val]

    return val
