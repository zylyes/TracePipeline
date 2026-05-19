"""单元测试 — geology/angles.py 角度转换逻辑。"""
from __future__ import annotations

import math

import numpy as np
import pytest

from trace_pipeline.geology.angles import (
    azimuth_to_cartesian_deg,
    dip_to_strike,
    fold_strike_angle,
    fold_strikes_to_semicircle,
    fold_to_halfplane,
)


class TestAzimuthToCartesianDeg:
    """方位角 → 笛卡尔角转换。"""

    def test_north(self) -> None:
        assert azimuth_to_cartesian_deg(0.0) == 90.0

    def test_east(self) -> None:
        # 90° 时走 else 分支: 450 - 90 = 360，与 0° 等价
        assert azimuth_to_cartesian_deg(90.0) == pytest.approx(360.0)

    def test_south(self) -> None:
        assert azimuth_to_cartesian_deg(180.0) == pytest.approx(270.0)

    def test_west(self) -> None:
        assert azimuth_to_cartesian_deg(270.0) == pytest.approx(180.0)


class TestDipToStrike:
    """倾向 → 走向向量化转换。"""

    def test_scalar(self) -> None:
        # dd=0 -> strike=90
        assert dip_to_strike(np.array([0.0]))[0] == pytest.approx(90.0)

    def test_vectorized(self) -> None:
        dips = np.array([0.0, 90.0, 180.0, 270.0, 360.0])
        expected = np.array([90.0, 0.0, 90.0, 0.0, 90.0])
        result = dip_to_strike(dips)
        np.testing.assert_allclose(result, expected, atol=1e-10)

    def test_matlab_reference(self) -> None:
        """与 MATLAB Coordinate.m 公式一致的参考值。"""
        # dd >= 270: strike = dd - 270
        assert dip_to_strike(np.array([298.0]))[0] == pytest.approx(28.0)
        # 90 <= dd < 270: strike = dd - 90
        assert dip_to_strike(np.array([165.0]))[0] == pytest.approx(75.0)
        # dd < 90: strike = dd + 90
        assert dip_to_strike(np.array([45.0]))[0] == pytest.approx(135.0)


class TestFoldStrikeAngle:
    """走向角折叠到 [-π/2, π/2]。"""

    def test_quadrant1(self) -> None:
        assert fold_strike_angle(45.0) == pytest.approx(math.radians(45.0))

    def test_quadrant2(self) -> None:
        assert fold_strike_angle(135.0) == pytest.approx(math.radians(-45.0))

    def test_quadrant3(self) -> None:
        assert fold_strike_angle(225.0) == pytest.approx(math.radians(45.0))

    def test_quadrant4(self) -> None:
        assert fold_strike_angle(315.0) == pytest.approx(math.radians(-45.0))

    def test_boundary_90(self) -> None:
        assert fold_strike_angle(90.0) == pytest.approx(math.radians(90.0))

    def test_boundary_270(self) -> None:
        # 270° 恰好不满足 "ang > 270.0"，走第二个分支 ang - 180° = 90°
        assert fold_strike_angle(270.0) == pytest.approx(math.radians(90.0))

    def test_modulo(self) -> None:
        """超出 [0, 360) 的值自动取模。"""
        assert fold_strike_angle(405.0) == pytest.approx(math.radians(45.0))


class TestFoldToHalfplane:
    """半平面折叠。"""

    def test_inside(self) -> None:
        base = 0.0
        targets = np.array([10.0, 45.0, 90.0])
        result = fold_to_halfplane(base, targets)
        np.testing.assert_allclose(result, np.radians(targets), atol=1e-10)

    def test_outside(self) -> None:
        base = 0.0
        targets = np.array([200.0, 270.0])
        result = fold_to_halfplane(base, targets)
        expected = np.radians(np.array([20.0, 90.0]))  # +180 后取模
        np.testing.assert_allclose(result, expected, atol=1e-10)

    def test_invert(self) -> None:
        base = 0.0
        targets = np.array([10.0, 200.0])
        result = fold_to_halfplane(base, targets, invert=True)
        # invert=True: 原本在内部的翻转 +180°，外部的保持不变
        expected_10 = np.radians(10.0 + 180.0)
        expected_200 = np.radians(200.0)
        assert result[0] == pytest.approx(expected_10 % (2 * math.pi))
        assert result[1] == pytest.approx(expected_200 % (2 * math.pi))


class TestFoldStrikesToSemicircle:
    """走向角折叠到 [0°, 180°)。"""

    def test_basic(self) -> None:
        strikes = np.array([0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 315.0])
        result = fold_strikes_to_semicircle(strikes)
        expected = np.array([0.0, 45.0, 90.0, 135.0, 0.0, 45.0, 135.0])
        np.testing.assert_allclose(result, expected, atol=1e-10)

    def test_180_becomes_0(self) -> None:
        """180° 应折叠为 0°（通过 isclose 判断）。"""
        result = fold_strikes_to_semicircle(np.array([180.0]))
        assert result[0] == pytest.approx(0.0, abs=1e-10)
