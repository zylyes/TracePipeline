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
