"""集成 smoke test — pipeline.py 全流程编排。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trace_pipeline.models import PipelineStatus, RunConfig
from trace_pipeline.pipeline import load_trace_data, run_pipeline


def _create_test_excel(tmp_dir: Path, stem: str, sheet: str) -> Path:
    """在临时目录中创建一个最小迹线 Excel 文件。

    格式：首行既是第一条迹线数据（第 0-6 列），也携带表头信息（第 7-12 列）。
    第 0-6 列：r1-r7, 第 7 列：走向角, 第 8 列：迹线条数,
    第 11 列：实测测线长度（可选）, 第 12 列：实测露头面积（可选）。
    """
    records = []
    for i in range(3):
        x_along = i * 2.0
        records.append(
            [
                x_along,  # 第 0 列: r1（测线位置）
                0.1,  # 第 1 列: r2
                30.0,  # 第 2 列: r3（倾向）
                x_along + 1.5,  # 第 3 列: r4
                0.8 + i * 0.1,  # 第 4 列: r5（左侧迹长）
                0.0,  # 第 5 列: r6（右侧迹长，0 表示无右侧）
                1.0 + i * 0.1,  # 第 6 列: r7（r5>0 时必须 >0）
                298.0 if i == 0 else None,  # 第 7 列: 走向角
                3 if i == 0 else None,  # 第 8 列: 迹线条数
                None,
                None,  # 第 9, 10 列
                5.0 if i == 0 else None,  # 第 11 列: 实测测线长度
                10.0 if i == 0 else None,  # 第 12 列: 实测露头面积
            ]
        )
    df = pd.DataFrame(records)
    path = tmp_dir / f"{stem}.xlsx"
    df.to_excel(path, index=False, header=False, sheet_name=sheet)
    return path


class TestLoadTraceData:
    def test_load_from_excel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            stem = "O76_process"
            _create_test_excel(tmp_dir, stem, "O76")
            td = load_trace_data(str(tmp_dir), stem, "O76")
            assert td.count == 3
            assert np.isfinite(td.scanline_azimuth)
            assert td.endpoints.shape == (3, 4)

    def test_load_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_trace_data("/nonexistent/dir", "nonexistent_table", "O76")


class TestRunPipeline:
    def test_successful_run(self) -> None:
        with (
            tempfile.TemporaryDirectory() as input_tmp,
            tempfile.TemporaryDirectory() as output_tmp,
        ):
            input_dir = Path(input_tmp)
            output_dir = Path(output_tmp)
            stem = "O76_process"
            _create_test_excel(input_dir, stem, "O76")

            cfg = RunConfig(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                output_prefix="O76",
                table_stem=stem,
                outcrop="O76",
                export_rose_plot=False,
            )
            result = run_pipeline(cfg)
            assert result.status is PipelineStatus.SUCCESS
            assert result.trace_count == 3

    def test_error_on_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as output_tmp:
            cfg = RunConfig(
                input_dir="/nonexistent/input",
                output_dir=str(Path(output_tmp)),
                output_prefix="Test",
                table_stem="missing_table",
                outcrop="O76",
            )
            result = run_pipeline(cfg)
            assert result.status is PipelineStatus.ERROR
            assert result.error is not None

    def test_run_result_structure(self) -> None:
        with (
            tempfile.TemporaryDirectory() as input_tmp,
            tempfile.TemporaryDirectory() as output_tmp,
        ):
            input_dir = Path(input_tmp)
            output_dir = Path(output_tmp)
            stem = "O76_process"
            _create_test_excel(input_dir, stem, "O76")

            cfg = RunConfig(
                input_dir=str(input_dir),
                output_dir=str(output_dir),
                output_prefix="O76",
                table_stem=stem,
                outcrop="O76",
                export_rose_plot=False,
            )
            result = run_pipeline(cfg)
            assert result.status is PipelineStatus.SUCCESS
            assert result.error is None  # 成功时应无错误
            assert result.trace_count == 3
            assert result.excel_path.endswith(".xlsx")
            assert result.window_strategy
