"""单元测试 — geology/transforms.py 坐标变换流水线。"""
from __future__ import annotations

import numpy as np
import pytest

from trace_pipeline.geology.transforms import (
    normalize_coordinates,
    normalize_points_like_lines,
    rotate_and_shift,
    shift_to_positive,
)


class TestShiftToPositive:
    """正象限平移。"""

    def test_already_positive(self) -> None:
        lines = np.array([[1, 1, 2, 2]])
        result = shift_to_positive(lines, margin=1.0)
        # min_x=1.0, margin=1.0 → dx=max(0, 1-1)=0，坐标不变
        assert result[0, 0] == pytest.approx(1.0)
        assert result[0, 1] == pytest.approx(1.0)

    def test_negative_shift(self) -> None:
        lines = np.array([[-5, -3, -1, -1]])
        result = shift_to_positive(lines, margin=2.0)
        # min_x=-5, margin=2 → dx=max(0, 2-(-5))=7 → x_new = -5+7 = 2
        assert result[0, 0] == pytest.approx(2.0)
        # min_y=-3, margin=2 → dy=max(0, 2-(-3))=5 → y_new = -3+5 = 2
        assert result[0, 1] == pytest.approx(2.0)

    def test_invalid_margin(self) -> None:
        with pytest.raises(ValueError, match="margin 必须 ≥ 0"):
            shift_to_positive(np.array([[0, 0, 1, 1]]), margin=-1.0)

    def test_empty(self) -> None:
        result = shift_to_positive(np.array([]).reshape(0, 4))
        assert result.shape == (0, 4)


class TestRotateAndShift:
    """旋转 + 平移。"""

    def test_horizontal_line(self) -> None:
        lines = np.array([[0, 0, 10, 0]])
        result = rotate_and_shift(lines, azimuth_deg=0.0)
        # 走向 0° → 折叠为 0° → 不旋转，只需平移到非负
        assert result[0, 0] >= 0.0
        assert result[0, 1] == pytest.approx(0.0, abs=1e-10)

    def test_vertical_line_90(self) -> None:
        lines = np.array([[0, 0, 0, 10]])
        result = rotate_and_shift(lines, azimuth_deg=90.0)
        # 走向 90° → 折叠为 90° → 旋转 -90°，垂直线变为水平
        assert result[0, 0] >= 0.0
        assert result[0, 1] >= 0.0

    def test_empty(self) -> None:
        result = rotate_and_shift(np.array([]).reshape(0, 4), azimuth_deg=0.0)
        assert result.shape == (0, 4)


class TestNormalizeCoordinates:
    """规范化流水线：平移 → 旋转 → 再平移。"""

    def test_roundtrip_shape(self) -> None:
        lines = np.array([[1, 2, 3, 4], [5, 6, 7, 8]])
        result = normalize_coordinates(lines, azimuth_deg=45.0, margin=1.0)
        assert result.shape == (2, 4)
        assert np.isfinite(result).all()
        assert (result >= 0.0).all()

    def test_nonfinite_input(self) -> None:
        lines = np.array([[1, np.nan, 3, 4]])
        with pytest.raises(ValueError, match="包含 NaN 或 inf"):
            normalize_coordinates(lines, azimuth_deg=0.0)

    def test_invalid_shape(self) -> None:
        with pytest.raises(ValueError, match="必须为 \\(N,4\\) 形状"):
            normalize_coordinates(np.array([1, 2, 3]), azimuth_deg=0.0)


class TestNormalizePointsLikeLines:
    """用与线段相同的变换流程转换点坐标。"""

    def test_consistency(self) -> None:
        lines = np.array([[0, 0, 10, 0], [5, 5, 15, 5]])
        points = np.array([[2, 1], [7, 1]])
        result = normalize_points_like_lines(points, lines, azimuth_deg=0.0, margin=1.0)
        assert result.shape == (2, 2)
        assert np.isfinite(result).all()
