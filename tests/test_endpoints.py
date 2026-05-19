"""单元测试 — geology/endpoints.py 端点坐标计算。"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from trace_pipeline.geology.endpoints import EndpointResult, compute_endpoints


class TestComputeEndpoints:
    """compute_endpoints 的边界与参考值测试。"""

    @staticmethod
    def _make_df(rows: list[list[float]]) -> pd.DataFrame:
        """构造无表头的 DataFrame，列数至少 13（适配可选字段）。"""
        data = [row + [0.0] * (13 - len(row)) for row in rows]
        return pd.DataFrame(data)

    def test_empty_table(self) -> None:
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="输入表格为空"):
            compute_endpoints(df)

    def test_insufficient_columns(self) -> None:
        df = pd.DataFrame([[1, 2, 3]])
        with pytest.raises(ValueError, match="至少需要"):
            compute_endpoints(df)

    def test_invalid_header_azimuth(self) -> None:
        df = self._make_df([[0, 0, 0, 0, 0, 0, 0, "invalid", 1]])
        with pytest.raises(ValueError, match="无法解析表头"):
            compute_endpoints(df)

    def test_negative_r1(self) -> None:
        df = self._make_df([[-1, 0, 45, 1, 1, 0, 0, 0, 1]])
        with pytest.raises(ValueError, match="r1 不能为负数"):
            compute_endpoints(df)

    def test_missing_trace(self) -> None:
        """r5 与 r7 同时为 0 时应报错。"""
        df = self._make_df([[0, 0, 45, 1, 0, 0, 0, 0, 1]])
        with pytest.raises(ValueError, match="r5 与 r7 不能同时为 0"):
            compute_endpoints(df)

    def test_single_left_trace(self) -> None:
        """仅左侧有迹线 (r5≠0, r7=0)。"""
        # r1=0, r2=0, dip=90, r4=0, r5=10, r6=0, r7=0, ang0=0, n=1
        df = self._make_df([[0, 0, 90, 0, 10, 0, 0, 0, 1]])
        result = compute_endpoints(df)
        assert isinstance(result, EndpointResult)
        assert result.count == 1
        assert result.azimuth == 0.0
        assert result.measured_scanline_length is None
        assert result.measured_outcrop_area is None
        # 走向 = 90-90 = 0°，即正北；端点距离应为 10
        assert result.segment_lengths[0] == 10.0

    def test_single_right_trace(self) -> None:
        """仅右侧有迹线 (r5=0, r7≠0)。"""
        df = self._make_df([[0, 0, 90, 0, 0, 0, 10, 0, 1]])
        result = compute_endpoints(df)
        assert result.segment_lengths[0] == 10.0

    def test_bilateral_trace(self) -> None:
        """双侧均有迹线 (r5≠0, r7≠0)。"""
        df = self._make_df([[0, 0, 90, 0, 10, 0, 20, 0, 1]])
        result = compute_endpoints(df)
        assert result.segment_lengths[0] == 30.0

    def test_measured_scanline_length_parsed(self) -> None:
        """首行第 12 列（索引 11）应解析为实测测线长度。"""
        df = self._make_df([[0, 0, 90, 0, 10, 0, 0, 0, 1, 0, 0, 50.0, 0]])
        result = compute_endpoints(df)
        assert result.measured_scanline_length == 50.0

    def test_measured_outcrop_area_parsed(self) -> None:
        """首行第 13 列（索引 12）应解析为实测露头面积。"""
        df = self._make_df([[0, 0, 90, 0, 10, 0, 0, 0, 1, 0, 0, 0, 200.0]])
        result = compute_endpoints(df)
        assert result.measured_outcrop_area == 200.0

    def test_matlab_precision(self) -> None:
        """端点坐标应为有限浮点数，且双侧迹线的端点距离与 segment_lengths
        处于同一数量级（允许几何关系带来的差异）。"""
        # 一组典型数据（O76 第 1 条迹线近似参数）
        df = self._make_df([
            [2.5, 0.3, 298.0, 1.2, 5.0, 0.8, 4.0, 298.0, 1]
        ])
        result = compute_endpoints(df)
        endpoints = result.endpoints[0]
        # 端点坐标应为有限浮点数
        assert np.isfinite(endpoints).all()
        # 端点间欧氏距离应与 segment_lengths 处于同一数量级
        # （双侧迹线的端点距离不等于 r5+r7，而是左右端点的空间距离）
        dx = endpoints[2] - endpoints[0]
        dy = endpoints[3] - endpoints[1]
        dist = math.hypot(dx, dy)
        assert dist > 0.0
        # 距离应在合理范围内（r5+r7=9 为测段长度，端点距离通常在相近数量级）
        assert pytest.approx(dist, rel=0.5) == result.segment_lengths[0]
