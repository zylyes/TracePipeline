"""集成测试：端到端流水线验证（读取 → 计算 → 写入 → 绘图）。"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.conftest import make_trace
from trace_pipeline.geology._convex_hull import _shoelace_area
from trace_pipeline.geology.statistics import TraceStatistics
from trace_pipeline.models import RunConfig
from trace_pipeline.pipeline import _selected_hull_overlays, run_pipeline


def _make_test_excel(tmp_path: Path, stem: str, sheet: str) -> None:
    """在 tmp_path 下创建合成的迹线 Excel 文件。

    数据布局参照 endpoints.py：
        列 0-6: r1, r2, dip, r4, r5, r6, r7
        列 7:   测线走向角（仅首行）
        列 8:   迹线条数（仅首行）
    """
    n_traces = 5
    rng = np.random.default_rng(42)

    rows = []
    for i in range(n_traces):
        r1 = float(i * 2.0)       # 沿测线位移
        r2 = rng.uniform(-1, 1)   # 垂直测线位移
        dip = rng.uniform(0, 180) # 倾向
        r4 = rng.uniform(0.5, 3)  # 左侧迹长 1
        r5 = rng.uniform(0.5, 3)  # 左侧迹长 2
        r6 = rng.uniform(0.5, 3)  # 右侧迹长 1
        r7 = rng.uniform(0.5, 3)  # 右侧迹长 2

        row = [r1, r2, dip, r4, r5, r6, r7]
        if i == 0:
            row.extend([90.0, float(n_traces)])  # azimuth, count
        else:
            row.extend([np.nan, np.nan])
        rows.append(row)

    df = pd.DataFrame(rows)
    excel_path = tmp_path / f"{stem}.xlsx"
    df.to_excel(str(excel_path), index=False, header=False, engine="openpyxl")


def test_selected_hull_overlays_match_area_source():
    trace = make_trace(
        [
            [0.0, 0.0, 4.0, 0.0],
            [4.0, 0.0, 4.0, 3.0],
            [4.0, 3.0, 0.0, 3.0],
            [0.0, 3.0, 0.0, 0.0],
        ],
        [0.0, 1.0, 2.0, 3.0],
        scanline_azimuth=90.0,
    )
    base_stats = dict(
        scanline_azimuth=90.0,
        total_count=4,
        type_i_count=4,
        type_ii_count=0,
        type_iii_count=0,
        scanline_length=4.0,
        outcrop_area=12.0,
        mean_trace_length=2.0,
        trace_length_total=8.0,
        p10=1.0,
        p20=4 / 12.0,
        p21=8 / 12.0,
        scanline_length_source="estimated",
        trace_length_source="segment",
        p20_source="hull",
        p21_source="hull",
        window_strategy="auto",
        trace_types=("I", "I", "I", "I"),
        diagnostics=(),
        hull_buffer_ratio=0.25,
    )

    hull_stats = TraceStatistics(outcrop_area_source="hull", **base_stats)
    raw_hull, rotated_hull = _selected_hull_overlays(trace, hull_stats)
    assert raw_hull is not None
    assert rotated_hull is not None
    assert _shoelace_area(raw_hull.vertices) == pytest.approx(12.0)

    buffered_stats = TraceStatistics(
        outcrop_area_source="hull_buffered",
        hull_buffered_area=20.0,
        **base_stats,
    )
    raw_buffered, rotated_buffered = _selected_hull_overlays(trace, buffered_stats)
    assert raw_buffered is not None
    assert rotated_buffered is not None
    assert _shoelace_area(raw_buffered.vertices) > _shoelace_area(raw_hull.vertices)
    assert rotated_buffered.vertices[:, 0].min() <= rotated_hull.vertices[:, 0].min()
    assert rotated_buffered.vertices[:, 0].max() >= rotated_hull.vertices[:, 0].max()

    measured_stats = TraceStatistics(outcrop_area_source="measured", **base_stats)
    assert _selected_hull_overlays(trace, measured_stats) == (None, None)


@pytest.fixture()
def pipeline_dirs(tmp_path: Path) -> tuple[Path, Path, str, str]:
    """创建输入/输出目录和测试 Excel 文件，返回 (input_dir, output_dir, stem, outcrop)。"""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    stem = "test_trace"
    outcrop = "T01"
    _make_test_excel(input_dir, stem, outcrop)
    return input_dir, output_dir, stem, outcrop


class TestEndToEndPipeline:
    """端到端集成测试。"""

    def test_successful_pipeline_produces_all_outputs(self, pipeline_dirs):
        input_dir, output_dir, stem, outcrop = pipeline_dirs
        cfg = RunConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            output_prefix=outcrop,
            table_stem=stem,
            outcrop=outcrop,
            export_rose_plot=True,
            rose_bin_width=10.0,
            rose_dpi=72,
            trace_dpi=72,
            rotated_trace_dpi=72,
        )

        result = run_pipeline(cfg)

        assert result.status == "success", f"流水线失败: {result.error}"
        assert result.trace_count == 5
        assert result.scanline_azimuth == 90.0
        assert result.mean_length > 0.0
        # Excel 输出
        assert result.excel_path
        assert Path(result.excel_path).is_file()
        # 原始迹线图
        assert result.raw_plot_path
        assert Path(result.raw_plot_path).is_file()
        # 旋转迹线图
        assert result.rotated_plot_path
        assert Path(result.rotated_plot_path).is_file()
        # 玫瑰图
        assert result.rose_plot_path
        assert Path(result.rose_plot_path).is_file()

    def test_pipeline_without_rose_plot(self, pipeline_dirs):
        input_dir, output_dir, stem, outcrop = pipeline_dirs
        cfg = RunConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            output_prefix=outcrop,
            table_stem=stem,
            outcrop=outcrop,
            export_rose_plot=False,
            trace_dpi=72,
            rotated_trace_dpi=72,
        )

        result = run_pipeline(cfg)

        assert result.status == "success"
        assert result.rose_plot_path == ""
        assert Path(result.excel_path).is_file()
        assert Path(result.raw_plot_path).is_file()

    def test_pipeline_missing_file_returns_failure(self, tmp_path):
        input_dir = tmp_path / "empty_input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        cfg = RunConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            output_prefix="missing",
            table_stem="nonexistent",
            outcrop="X",
            trace_dpi=72,
            rotated_trace_dpi=72,
        )

        result = run_pipeline(cfg)

        assert result.status == "error"
        assert result.error  # 应包含错误信息

    def test_pipeline_output_file_sizes_are_nonzero(self, pipeline_dirs):
        input_dir, output_dir, stem, outcrop = pipeline_dirs
        cfg = RunConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            output_prefix=outcrop,
            table_stem=stem,
            outcrop=outcrop,
            export_rose_plot=True,
            rose_dpi=72,
            trace_dpi=72,
            rotated_trace_dpi=72,
        )

        result = run_pipeline(cfg)

        assert result.status == "success"
        for path_str in (result.excel_path, result.raw_plot_path, result.rotated_plot_path, result.rose_plot_path):
            if path_str:
                assert os.path.getsize(path_str) > 0, f"输出文件为空: {path_str}"

    def test_pipeline_window_strategy_options(self, pipeline_dirs):
        input_dir, output_dir, stem, outcrop = pipeline_dirs
        for strategy in ("auto", "tangent", "hybrid", "concentric"):
            cfg = RunConfig(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                output_prefix=f"{outcrop}_{strategy}",
                table_stem=stem,
                outcrop=outcrop,
                export_rose_plot=False,
                trace_dpi=72,
                rotated_trace_dpi=72,
                window_strategy=strategy,
            )

            result = run_pipeline(cfg)

            assert result.status == "success", f"策略 {strategy} 失败: {result.error}"
            assert result.window_strategy in ("auto", "tangent", "hybrid", "concentric")
