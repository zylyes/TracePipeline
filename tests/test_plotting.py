"""单元测试：绘图辅助与玫瑰图分箱。"""
import numpy as np
import pytest

from trace_pipeline.plotting.rose_plot import _compute_rose_histogram
from trace_pipeline.plotting.trace_plot import (
    _add_statistics_box,
    _build_decoration_layout,
    _panel_bounds,
    render_trace_plot,
    segments_to_xy,
)


def test_segments_to_xy_accepts_array_like():
    x, y = segments_to_xy([[0.0, 0.0, 1.0, 1.0]])

    np.testing.assert_allclose(x[:2], [0.0, 1.0])
    np.testing.assert_allclose(y[:2], [0.0, 1.0])
    assert np.isnan(x[2])
    assert np.isnan(y[2])


def test_render_trace_plot_rejects_nonfinite_before_writing(tmp_path):
    with pytest.raises(ValueError, match="NaN 或 inf"):
        render_trace_plot(
            np.array([[0.0, 0.0, np.nan, 1.0]]),
            "bad",
            str(tmp_path),
            "bad.png",
        )

    assert not (tmp_path / "bad.png").exists()


def test_render_trace_plot_accepts_statistics_box(tmp_path):
    out = render_trace_plot(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        "stats",
        str(tmp_path),
        "stats.png",
        statistics_lines=("迹线数量: 1", "面累计长度密度（$P_{21}$）: 0.100 $\\mathrm{m}^{-1}$"),
    )

    assert out.endswith("stats.png")
    assert (tmp_path / "stats.png").is_file()


def test_statistics_box_is_anchored_to_panel_bottom_right():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        has_annotation_panel=True,
    )
    panel_x0, panel_x1, panel_y0, panel_y1 = _panel_bounds(layout)
    panel_width = panel_x1 - panel_x0
    panel_height = panel_y1 - panel_y0
    calls = []

    class AxStub:
        def text(self, *args, **kwargs):
            calls.append((args, kwargs))

    _add_statistics_box(AxStub(), layout, ("line 1", "line 2"))

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[0] == pytest.approx(panel_x1 - panel_width * 0.04)
    assert args[1] == pytest.approx(panel_y0 + panel_height * 0.04)
    assert kwargs["ha"] == "right"
    assert kwargs["va"] == "bottom"


def test_trace_layout_uses_adaptive_scale_length():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        has_annotation_panel=True,
    )

    assert layout.scale_length > 0
    assert layout.scale_length in (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0)


def test_rose_histogram_keeps_non_divisible_final_bin_width():
    theta, radii, widths = _compute_rose_histogram(
        np.array([1.0, 8.0, 179.0]),
        bin_width=7.0,
    )

    assert theta.shape == radii.shape == widths.shape
    assert radii.sum() == 6
    np.testing.assert_allclose(np.rad2deg(widths[:2]), [7.0, 7.0])
    assert np.rad2deg(widths[len(widths) // 2 - 1]) == pytest.approx(5.0)


def test_rose_histogram_rejects_nonfinite_values():
    with pytest.raises(ValueError, match="strike_deg 包含"):
        _compute_rose_histogram(np.array([10.0, np.nan]), bin_width=10.0)
