"""Excel 读取回退行为测试。"""

from __future__ import annotations

import logging

import pandas as pd

from trace_pipeline.io.excel_reader import read_trace_excel


def test_missing_named_sheet_reads_first_sheet_without_failed_attempt(tmp_path, caplog) -> None:
    records = [
        [0.0, 0.1, 30.0, 1.5],
        [2.0, 0.2, 35.0, 3.5],
    ]
    pd.DataFrame(records).to_excel(
        tmp_path / "O76_process.xlsx",
        index=False,
        header=False,
        sheet_name="Data",
    )

    caplog.set_level(logging.DEBUG, logger="trace_pipeline.io.excel_reader")
    df = read_trace_excel(str(tmp_path), "O76_process", "O76")

    assert df.shape == (2, 4)
    assert "工作表 'O76' 不存在，直接读取首个 sheet" in caplog.text
    assert "失败（将尝试回退）" not in caplog.text
