"""pytest 共享 fixtures — 为后端及核心模块测试提供可复用的测试数据。"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def sample_endpoints() -> np.ndarray:
    """返回 4 条简单迹线的端点坐标 (4, 4)，用于绘图与统计测试。

    列序: [x1, y1, x2, y2]。
    """
    return np.array(
        [
            [0.0, 0.0, 2.0, 1.0],
            [1.0, 0.0, 3.0, 2.0],
            [0.0, 2.0, 2.0, 3.0],
            [3.0, 1.0, 5.0, 2.0],
        ],
        dtype=float,
    )


@pytest.fixture
def sample_strikes() -> np.ndarray:
    """返回与 sample_endpoints 对应的 4 个节理走向角（度）。"""
    return np.array([45.0, 60.0, 30.0, 75.0], dtype=float)


@pytest.fixture
def tmp_output_dir(tmp_path):
    """返回一个专用的临时输出目录，测试结束后自动清理。"""
    out = tmp_path / "output"
    out.mkdir()
    return out
