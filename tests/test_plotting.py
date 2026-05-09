"""单元测试：绘图辅助与玫瑰图分箱。"""
import logging

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Circle

from trace_pipeline.plotting import render_trace_plot, segments_to_xy
from trace_pipeline.plotting import style as style_module
from trace_pipeline.plotting.rose_plot import _compute_rose_histogram
from trace_pipeline.plotting.trace_plot import (
    CircleWindowOverlay,
    _add_circle_window_overlays,
    _add_statistics_box,
    _build_decoration_layout,
    _valid_circles,
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


def test_configure_style_prefers_times_new_roman_and_simsun(monkeypatch):
    with matplotlib.rc_context():
        monkeypatch.setattr(
            style_module,
            "_get_font_cache",
            lambda: {
                "western": ["Times New Roman"],
                "cjk_serif": ["SimSun"],
                "cjk_sans": [],
            },
        )

        style_module.configure_style()

        assert matplotlib.rcParams["font.family"][:2] == ["Times New Roman", "SimSun"]
        assert matplotlib.rcParams["mathtext.fontset"] == "custom"
        assert matplotlib.rcParams["mathtext.rm"] == "Times New Roman"


def test_configure_style_warns_but_handles_missing_fonts(monkeypatch, caplog):
    with matplotlib.rc_context():
        monkeypatch.setattr(
            style_module,
            "_get_font_cache",
            lambda: {"western": [], "cjk_serif": [], "cjk_sans": []},
        )

        with caplog.at_level(logging.WARNING):
            style_module.configure_style()

        assert matplotlib.rcParams["font.family"][:2] == ["Times New Roman", "SimSun"]
        assert "Times New Roman" in caplog.text
        assert "SimSun" in caplog.text


def test_circle_window_overlays_draw_valid_dark_dashed_auxiliary_circles():
    fig, ax = plt.subplots()
    try:
        valid = _valid_circles(
            (
                CircleWindowOverlay(1.0, 2.0, 3.0),
                CircleWindowOverlay(np.nan, 2.0, 3.0),
                CircleWindowOverlay(4.0, 5.0, -1.0),
            ),
        )
        _add_circle_window_overlays(ax, valid)

        circles = [patch for patch in ax.patches if isinstance(patch, Circle)]
        assert len(circles) == 1
        circle = circles[0]
        assert circle.center == pytest.approx((1.0, 2.0))
        assert circle.radius == pytest.approx(3.0)
        assert circle.get_fill() is False
        assert circle.get_edgecolor()[:3] == pytest.approx((0.25, 0.25, 0.25))
        assert circle.get_linestyle() == "--"
    finally:
        plt.close(fig)


def test_statistics_box_draws_fixed_grid_with_compact_labels():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        has_annotation_panel=True,
    )
    fig, ax = plt.subplots()
    try:
        _add_statistics_box(
            ax,
            layout,
            (
                "迹线数量: 1",
                "平均迹线长度（圆窗）: 9.060 $\\mathrm{m}$",
                "面密度（$P_{20}$）（圆窗）: 0.034 $\\mathrm{m}^{-2}$",
                "面累计长度密度（$P_{21}$）（圆窗）: 0.307 $\\mathrm{m}^{-1}$",
            ),
        )

        assert ax.texts[0].get_text() == "统计信息"
        assert ax.texts[0].get_transform() == ax.transAxes
        assert len(ax.patches) == 1
        assert ax.patches[0].get_facecolor()[:3] == pytest.approx((1.0, 1.0, 1.0))
        assert len(ax.lines) == 1

        label_texts = [
            text for text in ax.texts
            if text.get_ha() == "left" and text.get_text() != "统计信息"
        ]
        value_texts = [text for text in ax.texts if text.get_ha() == "right"]

        assert [text.get_text() for text in label_texts] == [
            "迹线数量",
            "平均迹长（圆窗）",
            "P20 面密度（圆窗）",
            "P21 长度密度（圆窗）",
        ]
        assert len(value_texts) == 4
        assert all(text.get_transform() == ax.transAxes for text in label_texts + value_texts)

        label_y = [text.get_position()[1] for text in label_texts]
        value_y = [text.get_position()[1] for text in value_texts]
        np.testing.assert_allclose(label_y, value_y)
        steps = np.diff(label_y)
        np.testing.assert_allclose(steps, np.full_like(steps, steps[0]))
    finally:
        plt.close(fig)


def test_trace_layout_uses_fixed_scale_length():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        has_annotation_panel=True,
    )

    assert layout.scale_length == 5.0


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
