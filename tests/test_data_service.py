from __future__ import annotations

import pandas as pd

from backend.services import data_service as data_module
from backend.services.data_service import DataService


def test_output_data_reuses_cached_sheet_between_pages(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    excel_path = output_dir / "O76_traces.xlsx"
    excel_path.write_bytes(b"placeholder")
    calls = 0

    def fake_read_excel(path, *, sheet_name, header):
        nonlocal calls
        calls += 1
        assert path == excel_path
        assert sheet_name == "走向与长度"
        assert header == 1
        return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
    service = DataService(output_dir=str(output_dir), input_dir=str(tmp_path))

    first = service.get_data("O76", "走向与长度", page=1, page_size=1)
    second = service.get_data("O76", "走向与长度", page=2, page_size=1)

    assert calls == 1
    assert first["total"] == 3
    assert first["data"] == [{"A": 1, "B": 4}]
    assert second["data"] == [{"A": 2, "B": 5}]


def test_input_data_reuses_cached_workbook_between_pages(tmp_path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    excel_path = input_dir / "O76_process.xlsx"
    excel_path.write_bytes(b"placeholder")
    calls = 0

    def fake_read_excel(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert path == excel_path
        return pd.DataFrame(
            [
                [1, 2, 30, 4, 5, 6, 7, 8, 9],
                [10, 11, 12, 13, 14, 15, 16, 17, 18],
            ]
        )

    monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
    service = DataService(output_dir=str(tmp_path), input_dir=str(input_dir))

    first = service.get_data("O76", "原始输入", page=1, page_size=1, source="input")
    second = service.get_data("O76", "原始输入", page=2, page_size=1, source="input")

    assert calls == 1
    assert first["total"] == 2
    assert first["data"][0]["r1-沿测线位移"] == 1.0
    assert second["data"][0]["r1-沿测线位移"] == 10.0
