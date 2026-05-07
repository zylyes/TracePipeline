"""几何工具：公共常量和辅助函数。"""
from __future__ import annotations

import numpy as np

_EPS = 1e-9


def cross_2d(a: np.ndarray, b: np.ndarray) -> float:
    """二维向量叉积（标量值）。"""
    return float(a[0] * b[1] - a[1] * b[0])
