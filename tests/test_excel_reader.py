"""Excel 读取回退行为测试。"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from trace_pipeline.io.excel_reader import TraceValidationError, read_trace_excel


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


def test_rejects_large_excel_file(tmp_path) -> None:
    """超过 50 MiB 的 Excel 文件应被拒绝，不调用 pandas 读取。"""
    path = tmp_path / "huge.xlsx"
    # 创建一个刚好超过 50 MiB 的文件
    with open(path, "wb") as f:
        f.write(b"\0" * (51 * 1024 * 1024))

    with pytest.raises(TraceValidationError) as excinfo:
        read_trace_excel(str(tmp_path), "huge", None)

    msg = str(excinfo.value)
    assert "huge.xlsx" in msg
    assert "MiB" in msg
