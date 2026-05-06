"""单元测试：geology.endpoints.compute_endpoints"""
import numpy as np
import pandas as pd
import pytest

from trace_pipeline.geology.endpoints import compute_endpoints


def _make_df(rows):
    """构造形如 compute_endpoints 期望的 DataFrame。

    rows: [[r1,r2,dip,r4,r5,r6,r7, ang0_or_nan, n_or_nan], ...]
    """
    return pd.DataFrame(rows)


class TestComputeEndpoints:
    def test_left_only(self):
        # 1 条迹线，仅左侧（r5=1, r7=0），azimuth=90, dip=0
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 90.0, 1]])
        az, n, ep, js, seg, r1 = compute_endpoints(df)
        assert az == 90.0
        assert n == 1
        assert ep.shape == (1, 4)
        assert js.shape == (1,)
        assert seg.shape == (1,)
        assert r1.shape == (1,)
        assert r1[0] == pytest.approx(0.0)
        assert seg[0] == pytest.approx(1.0)  # r5+r7 = 1+0

    def test_right_only(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 90.0, 1]])
        az, n, ep, js, seg, r1 = compute_endpoints(df)
        assert n == 1
        assert r1[0] == pytest.approx(0.0)
        assert seg[0] == pytest.approx(2.0)  # r5+r7 = 0+2

    def test_bilateral(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 3.0, 90.0, 1]])
        az, n, ep, js, seg, r1 = compute_endpoints(df)
        assert n == 1
        assert r1[0] == pytest.approx(0.0)
        assert seg[0] == pytest.approx(4.0)  # r5+r7 = 1+3

    def test_empty_df_raises(self):
        with pytest.raises(ValueError):
            compute_endpoints(pd.DataFrame())

    def test_too_few_columns(self):
        with pytest.raises(ValueError):
            compute_endpoints(pd.DataFrame([[0, 0, 0]]))

    def test_invalid_n(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 90.0, 0]])
        with pytest.raises(ValueError):
            compute_endpoints(df)

    def test_non_integer_n_raises(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 90.0, 1.5]])
        with pytest.raises(ValueError, match="迹线条数必须为整数"):
            compute_endpoints(df)

    def test_out_of_range_azimuth_raises(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 360.0, 1]])
        with pytest.raises(ValueError, match="走向角度必须位于"):
            compute_endpoints(df)

    def test_negative_scanline_position_raises_with_row_and_field(self):
        df = _make_df([[-1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 90.0, 1]])
        with pytest.raises(ValueError, match="第 1 行 r1 不能为负数"):
            compute_endpoints(df)

    def test_out_of_range_dip_raises_with_row_and_field(self):
        df = _make_df([[0.0, 0.0, 360.0, 0.0, 1.0, 0.0, 0.0, 90.0, 1]])
        with pytest.raises(ValueError, match="第 1 行 dip 必须位于"):
            compute_endpoints(df)

    def test_negative_length_raises_with_row_and_field(self):
        df = _make_df([[0.0, 0.0, 0.0, 0.0, 1.0, 0.0, -0.5, 90.0, 1]])
        with pytest.raises(ValueError, match="第 1 行 r7 不能为负数"):
            compute_endpoints(df)

    def test_zero_left_and_right_trace_lengths_raise(self):
        df = _make_df([[0.0, 0.0, 0.0, 1.0, 0.0, 2.0, 0.0, 90.0, 1]])
        with pytest.raises(ValueError, match="第 1 行 r5 与 r7 不能同时为 0"):
            compute_endpoints(df)
