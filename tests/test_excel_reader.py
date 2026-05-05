"""单元测试：Excel 读取。"""
import pandas as pd
import pytest

from trace_pipeline.io.excel_reader import read_trace_excel


def test_read_trace_excel_falls_back_to_first_sheet(tmp_path):
    path = tmp_path / "O76_process.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([[1, 2, 3]]).to_excel(
            writer, sheet_name="First", header=False, index=False
        )

    df = read_trace_excel(str(tmp_path), "O76_process", sheet="Missing")

    assert df.iloc[0, 0] == 1


def test_read_trace_excel_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="未找到 O76_process"):
        read_trace_excel(str(tmp_path), "O76_process", sheet="O76")


def test_read_trace_excel_existing_bad_file_raises_value_error(tmp_path):
    (tmp_path / "O76_process.xlsx").write_text("not an excel file", encoding="utf-8")

    with pytest.raises(ValueError, match="找到 O76_process.xlsx，但读取失败"):
        read_trace_excel(str(tmp_path), "O76_process", sheet="O76")
