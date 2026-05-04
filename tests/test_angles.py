"""单元测试：geology.angles"""
import math

import numpy as np
import pytest

from trace_pipeline.geology.angles import (
    dip_to_strike,
    fold_strike_angle,
    fold_strikes_to_semicircle,
    fold_to_halfplane,
)


class TestDipToStrike:
    def test_lt_90(self):
        assert dip_to_strike(np.array([0.0, 45.0, 89.0]))[0] == 90.0
        np.testing.assert_allclose(
            dip_to_strike(np.array([0.0, 45.0, 89.0])),
            [90.0, 135.0, 179.0],
        )

    def test_mid(self):
        np.testing.assert_allclose(
            dip_to_strike(np.array([90.0, 180.0, 269.0])),
            [0.0, 90.0, 179.0],
        )

    def test_ge_270(self):
        np.testing.assert_allclose(
            dip_to_strike(np.array([270.0, 315.0, 359.0])),
            [0.0, 45.0, 89.0],
        )


class TestFoldStrikeAngle:
    def test_quadrants(self):
        assert fold_strike_angle(45.0) == pytest.approx(math.radians(45.0))
        assert fold_strike_angle(135.0) == pytest.approx(math.radians(-45.0))
        assert fold_strike_angle(225.0) == pytest.approx(math.radians(45.0))
        assert fold_strike_angle(315.0) == pytest.approx(math.radians(-45.0))

    def test_modulo(self):
        assert fold_strike_angle(405.0) == pytest.approx(math.radians(45.0))


class TestFoldToHalfplane:
    def test_base_le_180(self):
        res = fold_to_halfplane(90.0, np.array([135.0]))
        # 90 < 135 < 270 → keep 135
        assert res[0] == pytest.approx(math.radians(135.0))

    def test_base_gt_180(self):
        # base=270, target=90 → not in (90,270) so +180 → 270
        res = fold_to_halfplane(270.0, np.array([90.0]))
        assert res[0] == pytest.approx(math.radians(270.0))

    def test_invert(self):
        r1 = fold_to_halfplane(90.0, np.array([135.0]), invert=False)
        r2 = fold_to_halfplane(90.0, np.array([135.0]), invert=True)
        # 反向后应差 180°
        diff = (r2[0] - r1[0]) % (2 * math.pi)
        assert diff == pytest.approx(math.pi, abs=1e-9)


class TestFoldStrikesToSemicircle:
    def test_basic(self):
        res = fold_strikes_to_semicircle(np.array([0.0, 90.0, 180.0, 270.0, 359.0]))
        np.testing.assert_allclose(res, [0.0, 90.0, 0.0, 90.0, 179.0])
