"""单元测试：绘图辅助与玫瑰图分箱。"""
import logging
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.patches import Circle, Polygon, Rectangle

import trace_pipeline.plotting.trace_plot as trace_plot_module
import trace_pipeline.plotting.rose_plot as rose_plot_module
from trace_pipeline.plotting import render_trace_plot, segments_to_xy
from trace_pipeline.plotting import style as style_module
from trace_pipeline.plotting._decoration_layout import resolve_decoration_positions
from trace_pipeline.plotting.rose_plot import _compute_rose_histogram, render_rose_plot
from trace_pipeline.plotting.trace_plot import (
    CircleWindowOverlay,
    ConvexHullOverlay,
    TracePlotLayout,
    _add_circle_window_overlays,
    _add_statistics_box,
    _build_decoration_layout,
    _split_statistics_line,
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
        assert matplotlib.rcParams["mathtext.default"] == "regular"
        assert matplotlib.rcParams["lines.linewidth"] <= 0.9


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
        assert circle.get_fill() is True
        assert circle.get_edgecolor()[:3] == pytest.approx((0.902, 0.318, 0.0), abs=0.01)
        assert circle.get_linestyle() == "--"
    finally:
        plt.close(fig)


def test_statistics_box_draws_fixed_grid_with_compact_labels():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
    )
    fig, ax = plt.subplots()
    try:
        _add_statistics_box(
            ax,
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


def test_statistics_values_normalize_units_to_mathtext():
    assert _split_statistics_line("露头面积: 92.936 m²") == (
        "露头面积",
        "92.936 $\\mathrm{m}^{2}$",
    )
    assert _split_statistics_line("P10 线密度: 2.204 m⁻¹") == (
        "P10 线密度",
        "2.204 $\\mathrm{m}^{-1}$",
    )
    assert _split_statistics_line("P20 面密度: 0.204 m^-2") == (
        "P20 面密度",
        "0.204 $\\mathrm{m}^{-2}$",
    )
    assert _split_statistics_line("平均迹线长度: 6.541 $\\mathrm{m}$") == (
        "平均迹长",
        "6.541 $\\mathrm{m}$",
    )


def test_statistics_box_keeps_many_rows_separated():
    layout = _build_decoration_layout(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
    )
    fig, ax = plt.subplots()
    try:
        lines = tuple(f"指标{idx}: {idx:.3f} m²" for idx in range(14))
        _add_statistics_box(ax, lines)

        value_texts = [text for text in ax.texts if text.get_ha() == "right"]
        assert len(value_texts) == 14
        value_y = np.array([text.get_position()[1] for text in value_texts])
        assert np.min(np.abs(np.diff(value_y))) > 0.025
        assert all(text.get_fontsize() <= 5.8 for text in value_texts)
    finally:
        plt.close(fig)


def test_render_trace_plot_draws_only_selected_hull_overlay(tmp_path, monkeypatch):
    calls = []

    def record_hull(ax, hull_overlay):
        calls.append(("hull", hull_overlay.vertices.copy()))
        ax.add_patch(Polygon(hull_overlay.vertices))

    def record_circles(ax, valid_circles):
        calls.append(("circles", len(valid_circles)))

    monkeypatch.setattr(trace_plot_module, "_add_convex_hull_overlay", record_hull)
    monkeypatch.setattr(trace_plot_module, "_add_circle_window_overlays", record_circles)

    render_trace_plot(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        "hull",
        str(tmp_path),
        "hull.png",
        statistics_lines=("迹线数量: 1",),
        circle_windows=(CircleWindowOverlay(0.0, 0.0, 5.0),),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])),
        area_source="hull",
    )

    assert [kind for kind, _value in calls] == ["hull"]


def test_render_trace_plot_draws_only_window_overlay(tmp_path, monkeypatch):
    calls = []

    def record_hull(ax, hull_overlay):
        calls.append(("hull", hull_overlay.vertices.copy()))

    def record_circles(ax, valid_circles):
        calls.append(("circles", len(valid_circles)))

    monkeypatch.setattr(trace_plot_module, "_add_convex_hull_overlay", record_hull)
    monkeypatch.setattr(trace_plot_module, "_add_circle_window_overlays", record_circles)

    render_trace_plot(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        "window",
        str(tmp_path),
        "window.png",
        statistics_lines=("迹线数量: 1",),
        circle_windows=(CircleWindowOverlay(0.0, 0.0, 5.0),),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])),
        area_source="window_equivalent",
    )

    assert calls == [("circles", 1)]


def test_render_trace_plot_draws_legend_in_info_band(tmp_path, monkeypatch):
    legend_calls = []
    original = trace_plot_module._add_legend

    def record_legend(ax, area_source, has_hull, has_circles, **kwargs):
        legend_calls.append((area_source, has_hull, has_circles, ax.get_label()))
        return original(ax, area_source, has_hull, has_circles, **kwargs)

    monkeypatch.setattr(trace_plot_module, "_add_legend", record_legend)

    render_trace_plot(
        np.array([[0.0, 0.0, 1.0, 1.0]]),
        "panel",
        str(tmp_path),
        "panel.png",
        statistics_lines=("迹线数量: 1",),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])),
        area_source="hull",
    )

    # 图例位于同一外框内的独立信息区，且 area_source 正确传递
    assert len(legend_calls) == 1
    assert legend_calls[0] == ("hull", True, False, "trace_legend")


def test_render_trace_plot_keeps_decorations_outside_data_axes(tmp_path, monkeypatch):
    inspected = {}
    artist_bounds = {}

    def fake_save_figure(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        axes_by_label = {ax.get_label(): ax for ax in fig.axes}
        inspected.update(axes_by_label)
        for label in ("trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
            ax = axes_by_label[label]
            ax_bbox = ax.get_window_extent(renderer)
            bounds = []
            for artist in (*ax.texts, *ax.patches, *ax.lines):
                if not artist.get_visible():
                    continue
                bbox = artist.get_window_extent(renderer)
                if bbox.width == 0 and bbox.height == 0:
                    continue
                bounds.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1, ax_bbox.bounds))
            artist_bounds[label] = bounds
        assert bbox_inches is None
        plt.close(fig)
        return str(tmp_path / filename)

    monkeypatch.setattr(trace_plot_module, "save_figure", fake_save_figure)

    render_trace_plot(
        np.array([[0.0, 0.0, 8.0, 8.0], [2.0, 0.0, 9.0, 7.0]]),
        "layout",
        str(tmp_path),
        "layout.png",
        statistics_lines=tuple(f"指标{idx}: {idx}" for idx in range(20)),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [9.0, 0.0], [9.0, 8.0], [0.0, 8.0]])),
        area_source="hull",
    )

    assert {
        "trace_outer_frame",
        "trace_data",
        "trace_statistics",
        "trace_compass",
        "trace_scale",
        "trace_legend",
    } <= set(inspected)

    frame = inspected["trace_outer_frame"].get_position().bounds
    for label in ("trace_data", "trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
        bounds = inspected[label].get_position().bounds
        assert bounds[0] >= frame[0]
        assert bounds[1] >= frame[1]
        assert bounds[0] + bounds[2] <= frame[0] + frame[2]
        assert bounds[1] + bounds[3] <= frame[1] + frame[3]

    data_ax = inspected["trace_data"]
    assert len(data_ax.lines) == 1
    assert any(isinstance(patch, Polygon) for patch in data_ax.patches)
    assert not any(isinstance(patch, Rectangle) for patch in data_ax.patches)
    assert len(data_ax.texts) == 0
    assert data_ax.get_legend() is None

    stats_ax = inspected["trace_statistics"]
    assert any(isinstance(patch, Rectangle) for patch in stats_ax.patches)
    assert stats_ax.get_position().x0 > data_ax.get_position().x1

    for bounds in artist_bounds.values():
        for x0, y0, x1, y1, ax_bounds in bounds:
            ax_x0, ax_y0, ax_w, ax_h = ax_bounds
            assert x0 >= ax_x0 - 1.0
            assert y0 >= ax_y0 - 1.0
            assert x1 <= ax_x0 + ax_w + 1.0
            assert y1 <= ax_y0 + ax_h + 1.0


def test_trace_layout_uses_adaptive_scale_length():
    # 小数据范围 -> 自适应选择较小比例尺
    layout_small = _build_decoration_layout(np.array([[0.0, 0.0, 1.0, 1.0]]))
    assert layout_small.scale_length == 0.2  # base_span=1 -> target=0.2 -> scale=0.2

    # 大数据范围 -> 自适应选择较大比例尺
    layout_large = _build_decoration_layout(np.array([[0.0, 0.0, 100.0, 100.0]]))
    assert layout_large.scale_length == 20.0  # base_span=100 -> target=20 -> scale=20


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


def test_render_rose_plot_uses_academic_style(tmp_path, monkeypatch):
    inspected = {}

    def fake_save(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        ax = fig.axes[0]
        inspected["ax"] = ax
        inspected["title"] = ax.title
        inspected["bars"] = list(ax.patches)
        inspected["gridlines"] = [line for line in (*ax.xaxis.get_gridlines(), *ax.yaxis.get_gridlines())]
        assert pad_inches <= 0.08
        plt.close(fig)
        return str(tmp_path / filename)

    monkeypatch.setattr(rose_plot_module, "save_figure", fake_save)

    out = render_rose_plot(
        np.array([10.0, 20.0, 30.0, 200.0]),
        "产状玫瑰花瓣图（数量=4，分箱=10.0°）",
        str(tmp_path),
        "rose.png",
    )

    assert out.endswith("rose.png")
    title = inspected["title"]
    assert title.get_fontfamily()[:2] == ["Times New Roman", "SimSun"]
    assert title.get_fontsize() <= 11.0
    assert inspected["bars"]
    assert all(bar.get_alpha() <= 0.7 for bar in inspected["bars"])
    assert inspected["ax"].spines["polar"].get_linewidth() <= 0.75
    assert all(line.get_linewidth() <= 0.5 for line in inspected["gridlines"] if line.get_visible())


# ── 新增测试：旋转凸包坐标系一致性 ────────────────────────────────────


def test_rotated_hull_matches_trace_coordinate_system():
    """验证旋转后的凸包顶点与迹线端点处于同一坐标系（通过相同旋转矩阵）。"""
    from trace_pipeline.geology._convex_hull import _compute_convex_hull
    from trace_pipeline.geology.transforms import normalize_coordinates, normalize_points_like_lines

    # 简单矩形迹线
    segments = np.array([
        [0.0, 0.0, 10.0, 0.0],
        [10.0, 0.0, 10.0, 5.0],
        [10.0, 5.0, 0.0, 5.0],
        [0.0, 5.0, 0.0, 0.0],
    ])

    # 原始凸包
    raw_hull = _compute_convex_hull(segments)
    assert raw_hull is not None
    assert raw_hull.shape[0] == 4  # 矩形凸包 = 4 个顶点

    # 迹线旋转后的坐标
    rotated_segments = normalize_coordinates(segments, 90.0)

    # 凸包顶点通过相同旋转矩阵变换（与 _rotated_circle_overlays 一致）
    rotated_hull = normalize_points_like_lines(raw_hull, segments, 90.0)
    assert rotated_hull is not None
    assert rotated_hull.shape[0] == 4

    # 旋转后的凸包应包围旋转后的迹线端点
    rotated_seg_xs = rotated_segments[:, [0, 2]].ravel()
    rotated_seg_ys = rotated_segments[:, [1, 3]].ravel()

    hull_x_min, hull_x_max = rotated_hull[:, 0].min(), rotated_hull[:, 0].max()
    hull_y_min, hull_y_max = rotated_hull[:, 1].min(), rotated_hull[:, 1].max()

    assert hull_x_min <= rotated_seg_xs.min() + 1e-6
    assert hull_x_max >= rotated_seg_xs.max() - 1e-6
    assert hull_y_min <= rotated_seg_ys.min() + 1e-6
    assert hull_y_max >= rotated_seg_ys.max() - 1e-6


# ── 装饰元素自动避让 ────────────────────────────────────


def _quadrant_segments(quadrant: str, n: int = 60) -> np.ndarray:
    """在指定象限生成密集线段，xlim/ylim 覆盖 [0,10]×[0,10]。"""
    rng = np.random.default_rng(0)
    if quadrant == "TR":
        x_lo, x_hi, y_lo, y_hi = 6.0, 10.0, 6.0, 10.0
    elif quadrant == "BL":
        x_lo, x_hi, y_lo, y_hi = 0.0, 4.0, 0.0, 4.0
    elif quadrant == "TL":
        x_lo, x_hi, y_lo, y_hi = 0.0, 4.0, 6.0, 10.0
    else:  # BR
        x_lo, x_hi, y_lo, y_hi = 6.0, 10.0, 0.0, 4.0
    pts = rng.uniform(
        low=[x_lo, y_lo, x_lo, y_lo],
        high=[x_hi, y_hi, x_hi, y_hi],
        size=(n, 4),
    )
    return pts


def _rect_overlap_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    dy = max(0.0, min(ay1, by1) - max(ay0, by0))
    return dx * dy


def test_decoration_avoids_dense_top_right_quadrant():
    """迹线集中在右上 → 装饰元素去左/下。"""
    segments = _quadrant_segments("TR")
    layout = TracePlotLayout()
    pos = resolve_decoration_positions(
        segments,
        xlim=(0.0, 10.0),
        ylim=(0.0, 10.0),
        layout=layout,
        stats_row_count=5,
        scale_length_data=2.0,
    )
    # legend 锚点应落在底/左侧
    anchor_x, anchor_y, loc = pos["legend"]
    assert anchor_y <= 0.5 or anchor_x <= 0.5
    assert "right" not in loc or "lower" in loc
    # stats 矩形应不与右上象限大量重叠
    stats = pos["stats"]
    assert stats[0] < 0.6 or stats[3] < 0.6
    # scale bar data 坐标 y 应在下半数据区
    _, scale_y = pos["scale"]
    assert scale_y < 5.0


def test_decoration_avoids_dense_bottom_left_quadrant():
    """迹线集中在左下 → 装饰元素去右/上。"""
    segments = _quadrant_segments("BL")
    layout = TracePlotLayout()
    pos = resolve_decoration_positions(
        segments,
        xlim=(0.0, 10.0),
        ylim=(0.0, 10.0),
        layout=layout,
        stats_row_count=5,
        scale_length_data=2.0,
    )
    anchor_x, anchor_y, _loc = pos["legend"]
    # 左下密集时图例必须避开左下角
    assert not (anchor_x < 0.3 and anchor_y < 0.3)
    stats = pos["stats"]
    assert stats[2] > 0.4 or stats[1] > 0.4


def test_decoration_deterministic_and_independent_of_extra_args():
    """同输入两次调用结果相同；不依赖 area_source（resolve 不接受 area_source）。"""
    segments = _quadrant_segments("TR")
    layout = TracePlotLayout()
    p1 = resolve_decoration_positions(
        segments, xlim=(0.0, 10.0), ylim=(0.0, 10.0),
        layout=layout, stats_row_count=8, scale_length_data=2.0,
    )
    p2 = resolve_decoration_positions(
        segments, xlim=(0.0, 10.0), ylim=(0.0, 10.0),
        layout=layout, stats_row_count=8, scale_length_data=2.0,
    )
    assert p1["legend"] == p2["legend"]
    assert p1["stats"] == p2["stats"]
    assert p1["scale"] == p2["scale"]


def test_decorations_do_not_mutually_overlap():
    """三个装饰元素的轴坐标矩形两两 IoU=0（含 legend 矩形）。"""
    segments = _quadrant_segments("TR", n=120)
    layout = TracePlotLayout()
    pos = resolve_decoration_positions(
        segments, xlim=(0.0, 10.0), ylim=(0.0, 10.0),
        layout=layout, stats_row_count=8, scale_length_data=2.0,
    )
    stats = pos["stats"]
    legend_rect = pos["_legend_rect"]
    scale_rect = pos["_scale_rect"]
    assert _rect_overlap_area(stats, legend_rect) == pytest.approx(0.0, abs=1e-9)
    assert _rect_overlap_area(stats, scale_rect) == pytest.approx(0.0, abs=1e-9)
    assert _rect_overlap_area(legend_rect, scale_rect) == pytest.approx(0.0, abs=1e-9)


def test_auto_placement_disabled_returns_legacy_positions():
    """auto_placement=False 时回退到原硬编码位置。"""
    segments = _quadrant_segments("TR")
    layout = TracePlotLayout(auto_placement=False)
    pos = resolve_decoration_positions(
        segments, xlim=(0.0, 10.0), ylim=(0.0, 10.0),
        layout=layout, stats_row_count=5, scale_length_data=2.0,
    )
    assert pos["auto"] is False
    anchor_x, anchor_y, loc = pos["legend"]
    assert (anchor_x, anchor_y, loc) == (layout.legend_rel_x, layout.legend_rel_y, "lower left")
    assert pos["stats"] == (
        layout.stats_box_rel_x0,
        layout.stats_box_rel_y0,
        layout.stats_box_rel_x1,
        layout.stats_box_rel_y1,
    )


# ── 新增布局测试：标题间距与代表性图幅 ────────────────────────────────


def _fake_save_inspector(inspected: dict, artist_bounds: dict, tmp_path):
    """返回一个 monkeypatch 用的 fake save_figure，用于捕获布局信息。"""
    def fake_save_figure(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        axes_by_label = {ax.get_label(): ax for ax in fig.axes}
        inspected.update(axes_by_label)

        for label in ("trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
            ax = axes_by_label[label]
            ax_bbox = ax.get_window_extent(renderer)
            bounds = []
            for artist in (*ax.texts, *ax.patches, *ax.lines):
                if not artist.get_visible():
                    continue
                bbox = artist.get_window_extent(renderer)
                if bbox.width == 0 and bbox.height == 0:
                    continue
                bounds.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1, ax_bbox.bounds))
            artist_bounds[label] = bounds

        assert bbox_inches is None
        plt.close(fig)
        return str(tmp_path / filename)
    return fake_save_figure


def _assert_layout_invariants(inspected: dict, artist_bounds: dict) -> None:
    """断言各面板互不重叠、全部在 frame 内、artist 在各自轴内、数据轴清洁。"""
    assert {
        "trace_outer_frame",
        "trace_data",
        "trace_statistics",
        "trace_compass",
        "trace_scale",
        "trace_legend",
    } <= set(inspected)

    frame = inspected["trace_outer_frame"].get_position().bounds
    for label in ("trace_data", "trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
        bounds = inspected[label].get_position().bounds
        assert bounds[0] >= frame[0]
        assert bounds[1] >= frame[1]
        assert bounds[0] + bounds[2] <= frame[0] + frame[2]
        assert bounds[1] + bounds[3] <= frame[1] + frame[3]

    # 数据轴清洁：无文本、无 legend、无 Rectangle patch
    data_ax = inspected["trace_data"]
    assert len(data_ax.texts) == 0
    assert data_ax.get_legend() is None
    assert not any(isinstance(p, Rectangle) for p in data_ax.patches)

    # 统计框在数据轴右侧
    assert inspected["trace_statistics"].get_position().x0 > data_ax.get_position().x1

    # artist 全部落在各自轴内
    for bounds in artist_bounds.values():
        for x0, y0, x1, y1, ax_bounds in bounds:
            ax_x0, ax_y0, ax_w, ax_h = ax_bounds
            assert x0 >= ax_x0 - 1.0
            assert y0 >= ax_y0 - 1.0
            assert x1 <= ax_x0 + ax_w + 1.0
            assert y1 <= ax_y0 + ax_h + 1.0

    # 面板间互不重叠（IoU ≈ 0）
    def _rect_overlap(a, b):
        dx = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
        dy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
        return dx * dy

    panel_labels = ("trace_statistics", "trace_legend", "trace_compass", "trace_scale")
    for i, a_label in enumerate(panel_labels):
        for b_label in panel_labels[i + 1 :]:
            a = inspected[a_label].get_position().bounds
            b = inspected[b_label].get_position().bounds
            assert _rect_overlap(a, b) == pytest.approx(0.0, abs=1e-9)


def test_double_line_title_frame_spacing(tmp_path, monkeypatch):
    """双行标题时 suptitle 不与 outer_frame 相交，且保留 >= 2 px 间距。"""
    inspected = {}
    artist_bounds = {}
    gaps = {}

    def fake_save(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        axes_by_label = {ax.get_label(): ax for ax in fig.axes}
        inspected.update(axes_by_label)

        for label in ("trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
            ax = axes_by_label[label]
            ax_bbox = ax.get_window_extent(renderer)
            bounds = []
            for artist in (*ax.texts, *ax.patches, *ax.lines):
                if not artist.get_visible():
                    continue
                bbox = artist.get_window_extent(renderer)
                if bbox.width == 0 and bbox.height == 0:
                    continue
                bounds.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1, ax_bbox.bounds))
            artist_bounds[label] = bounds

        suptitle = fig._suptitle
        suptitle_bbox = suptitle.get_window_extent(renderer)
        frame_bbox = axes_by_label["trace_outer_frame"].get_window_extent(renderer)
        gaps["vertical"] = suptitle_bbox.y0 - frame_bbox.y1
        gaps["overlap"] = suptitle_bbox.overlaps(frame_bbox)

        assert bbox_inches is None
        plt.close(fig)
        return str(tmp_path / filename)

    monkeypatch.setattr(trace_plot_module, "save_figure", fake_save)

    render_trace_plot(
        np.array([[0.0, 0.0, 8.0, 8.0], [2.0, 0.0, 9.0, 7.0]]),
        "迹线长度图\n标尺（走向=75.0°）",
        str(tmp_path),
        "double.png",
        statistics_lines=tuple(f"指标{idx}: {idx}" for idx in range(9)),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [9.0, 0.0], [9.0, 8.0], [0.0, 8.0]])),
        area_source="hull",
    )

    _assert_layout_invariants(inspected, artist_bounds)
    assert not gaps["overlap"], "双行标题 suptitle 不应与 outer_frame 相交"
    assert gaps["vertical"] >= 2.0, f"双行标题间距应 >= 2 px, 实际 {gaps['vertical']}"


def test_single_line_title_gap_measured(tmp_path, monkeypatch):
    """单行标题时同样断言 suptitle 与 outer_frame 保留 >= 2 px 间距。"""
    inspected = {}
    artist_bounds = {}
    gaps = {}

    def fake_save(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        axes_by_label = {ax.get_label(): ax for ax in fig.axes}
        inspected.update(axes_by_label)

        for label in ("trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
            ax = axes_by_label[label]
            ax_bbox = ax.get_window_extent(renderer)
            bounds = []
            for artist in (*ax.texts, *ax.patches, *ax.lines):
                if not artist.get_visible():
                    continue
                bbox = artist.get_window_extent(renderer)
                if bbox.width == 0 and bbox.height == 0:
                    continue
                bounds.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1, ax_bbox.bounds))
            artist_bounds[label] = bounds

        suptitle = fig._suptitle
        suptitle_bbox = suptitle.get_window_extent(renderer)
        frame_bbox = axes_by_label["trace_outer_frame"].get_window_extent(renderer)
        gaps["vertical"] = suptitle_bbox.y0 - frame_bbox.y1
        gaps["overlap"] = suptitle_bbox.overlaps(frame_bbox)

        assert bbox_inches is None
        plt.close(fig)
        return str(tmp_path / filename)

    monkeypatch.setattr(trace_plot_module, "save_figure", fake_save)

    render_trace_plot(
        np.array([[0.0, 0.0, 8.0, 8.0], [2.0, 0.0, 9.0, 7.0]]),
        "迹线长度图",
        str(tmp_path),
        "single_gap.png",
        statistics_lines=tuple(f"指标{idx}: {idx}" for idx in range(9)),
        hull_overlay=ConvexHullOverlay(np.array([[0.0, 0.0], [9.0, 0.0], [9.0, 8.0], [0.0, 8.0]])),
        area_source="hull",
    )

    _assert_layout_invariants(inspected, artist_bounds)
    assert not gaps["overlap"], "单行标题 suptitle 不应与 outer_frame 相交"
    assert gaps["vertical"] >= 2.0, f"单行标题间距应 >= 2 px, 实际 {gaps['vertical']}"


@pytest.mark.parametrize("title", ["迹线长度图", "迹线长度图\n标尺（走向=273.0°）"])
def test_representative_wide_layout_o81_style(tmp_path, monkeypatch, title):
    """宽图 + 9 行统计 + 凸包，覆盖 O81/O82/O83 代表性布局，并断言 PNG 文件特征。"""
    inspected = {}
    artist_bounds = {}
    original_save = trace_plot_module.save_figure

    def fake_save(fig, output_dir, filename, dpi=300, pad_inches=0.12, bbox_inches="tight"):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        axes_by_label = {ax.get_label(): ax for ax in fig.axes}
        inspected.update(axes_by_label)

        for label in ("trace_statistics", "trace_compass", "trace_scale", "trace_legend"):
            ax = axes_by_label[label]
            ax_bbox = ax.get_window_extent(renderer)
            bounds = []
            for artist in (*ax.texts, *ax.patches, *ax.lines):
                if not artist.get_visible():
                    continue
                bbox = artist.get_window_extent(renderer)
                if bbox.width == 0 and bbox.height == 0:
                    continue
                bounds.append((bbox.x0, bbox.y0, bbox.x1, bbox.y1, ax_bbox.bounds))
            artist_bounds[label] = bounds

        assert bbox_inches is None
        return original_save(fig, output_dir, filename, dpi=dpi, pad_inches=pad_inches, bbox_inches=bbox_inches)

    monkeypatch.setattr(trace_plot_module, "save_figure", fake_save)

    # 模拟 20 条迹线的宽矩形露头
    rng = np.random.default_rng(42)
    segments = rng.uniform(
        low=[0.0, 0.0, 0.0, 0.0],
        high=[30.0, 8.0, 30.0, 8.0],
        size=(20, 4),
    )
    hull = ConvexHullOverlay(np.array([
        [0.0, 0.0], [30.0, 0.0], [30.0, 8.0], [0.0, 8.0],
    ]))

    out_path = render_trace_plot(
        segments,
        title,
        str(tmp_path),
        "wide.png",
        figsize_cm=(36.0, 14.0),
        statistics_lines=tuple(f"指标{idx}: {idx:.3f}" for idx in range(9)),
        hull_overlay=hull,
        area_source="hull",
    )

    _assert_layout_invariants(inspected, artist_bounds)

    # 文件级断言
    assert Path(out_path).exists()
    assert Path(out_path).stat().st_size > 10 * 1024
    from PIL import Image
    with Image.open(out_path) as img:
        assert img.width > img.height, "代表性图幅应为宽图"
        assert img.width >= 4000  # 36cm @ 300dpi ≈ 4250px
