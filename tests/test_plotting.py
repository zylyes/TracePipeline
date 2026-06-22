"""绘图模块冒烟测试 — 验证 trace_plot 与 rose_plot 可正常渲染并输出文件。"""

from __future__ import annotations

import os

import pytest

from trace_pipeline.plotting.rose_plot import render_rose_plot
from trace_pipeline.plotting.style import apply_style_overrides
from trace_pipeline.plotting.trace_plot import render_trace_plot
from trace_pipeline.utils.mpl_init import force_noninteractive_backend

# 确保在导入绘图模块前已设置非交互后端
force_noninteractive_backend()


class TestRenderRosePlot:
    def test_renders_and_writes_png(self, sample_strikes, tmp_output_dir):
        path = render_rose_plot(
            sample_strikes,
            "测试玫瑰图",
            str(tmp_output_dir),
            "test_rose.png",
            bin_width=15.0,
            dpi=72,
        )
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 100  # 非空白 PNG

    def test_empty_strikes_does_not_crash(self, tmp_output_dir):
        import numpy as np

        path = render_rose_plot(
            np.array([], dtype=float),
            "空数据",
            str(tmp_output_dir),
            "empty_rose.png",
            dpi=72,
        )
        assert os.path.isfile(path)


class TestRenderTracePlot:
    def test_renders_and_writes_png(self, sample_endpoints, tmp_output_dir):
        path = render_trace_plot(
            sample_endpoints,
            "测试迹线图",
            str(tmp_output_dir),
            "test_trace.png",
            dpi=72,
            north_angle_deg=90.0,
        )
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 100

    def test_with_circle_windows(self, sample_endpoints, tmp_output_dir):
        """带圆窗覆盖层的迹线图渲染。"""
        from trace_pipeline.plotting.trace_plot import CircleWindowOverlay

        circles = [
            CircleWindowOverlay(center_x=1.0, center_y=1.0, radius=1.5),
        ]
        path = render_trace_plot(
            sample_endpoints,
            "带圆窗",
            str(tmp_output_dir),
            "test_trace_circles.png",
            dpi=72,
            circle_windows=circles,
        )
        assert os.path.isfile(path)

    def test_with_statistics_lines(self, sample_endpoints, tmp_output_dir):
        """带统计信息框的迹线图渲染。"""
        path = render_trace_plot(
            sample_endpoints,
            "带统计",
            str(tmp_output_dir),
            "test_trace_stats.png",
            dpi=72,
            statistics_lines=["P10 = 1.23 m⁻¹", "P20 = 0.45 m⁻²", "P21 = 0.89 m⁻²"],
            area_source="measured",
        )
        assert os.path.isfile(path)

    def test_render_inside_style_overrides_does_not_deadlock(self, sample_endpoints, tmp_output_dir):
        with apply_style_overrides({"trace_line_width": 1.2}):
            path = render_trace_plot(
                sample_endpoints,
                "样式覆盖",
                str(tmp_output_dir),
                "test_trace_style_override.png",
                dpi=72,
            )

        assert os.path.isfile(path)
