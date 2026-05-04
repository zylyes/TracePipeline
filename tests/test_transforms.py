"""单元测试：geology.transforms"""
import numpy as np
import pytest

from trace_pipeline.geology.transforms import (
    normalize_coordinates,
    rotate_and_shift,
    shift_to_positive,
)


class TestShiftToPositive:
    def test_already_positive(self):
        arr = np.array([[5.0, 5.0, 10.0, 10.0]])
        out = shift_to_positive(arr, margin=1.0)
        np.testing.assert_allclose(out, arr)

    def test_shifts_negative(self):
        arr = np.array([[-2.0, -3.0, 5.0, 5.0]])
        out = shift_to_positive(arr, margin=1.0)
        # min_x=-2 → dx=3; min_y=-3 → dy=4
        np.testing.assert_allclose(out, [[1.0, 1.0, 8.0, 9.0]])

    def test_empty(self):
        arr = np.zeros((0, 4))
        out = shift_to_positive(arr)
        assert out.shape == (0, 4)

    def test_invalid_shape(self):
        with pytest.raises(ValueError):
            shift_to_positive(np.zeros((3, 3)))


class TestRotateAndShift:
    def test_zero_rotation(self):
        # azimuth=90 → fold_strike_angle(90)=π/2，旋转 90°
        arr = np.array([[1.0, 0.0, 2.0, 0.0]])
        out = rotate_and_shift(arr, azimuth_deg=90.0)
        # 旋转 90° 后 (1,0)→(0,1)、(2,0)→(0,2)；min_x=0 → 不再平移
        np.testing.assert_allclose(out, [[0.0, 1.0, 0.0, 2.0]], atol=1e-9)

    def test_empty(self):
        arr = np.zeros((0, 4))
        out = rotate_and_shift(arr, 45.0)
        assert out.shape == (0, 4)


class TestNormalizeCoordinates:
    def test_shape_preserved(self):
        arr = np.array([[1.0, 1.0, 3.0, 4.0], [2.0, 2.0, 5.0, 6.0]])
        out = normalize_coordinates(arr, azimuth_deg=45.0)
        assert out.shape == arr.shape
        # 所有坐标 >= 0
        assert (out >= -1e-9).all()
