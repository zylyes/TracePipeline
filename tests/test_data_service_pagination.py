from __future__ import annotations

from backend.services.data_service import DataService


class TestDataServicePagination:
    """验证 DataService 分页参数规范化。"""

    def test_get_data_normalizes_page_zero(self, tmp_path, monkeypatch) -> None:
        """get_data 中 page=0 应被归一为 1。"""
        import pandas as pd
        from backend.services import data_service as data_module

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        excel_path = output_dir / "O76_traces.xlsx"
        excel_path.write_bytes(b"placeholder")

        calls = 0

        def fake_read_excel(path, *, sheet_name, header):
            nonlocal calls
            calls += 1
            return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(output_dir), input_dir=str(tmp_path))

        result = service.get_data("O76", "走向与长度", page=0, page_size=2)
        assert result["page"] == 1  # 归一化
        assert len(result["data"]) == 2

    def test_get_data_normalizes_page_negative(self, tmp_path, monkeypatch) -> None:
        """get_data 中 page 负数应被归一为 1。"""
        import pandas as pd
        from backend.services import data_service as data_module

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        excel_path = output_dir / "O76_traces.xlsx"
        excel_path.write_bytes(b"placeholder")

        def fake_read_excel(path, *, sheet_name, header):
            return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(output_dir), input_dir=str(tmp_path))

        result = service.get_data("O76", "走向与长度", page=-5, page_size=2)
        assert result["page"] == 1

    def test_get_data_normalizes_page_size_above_500(self, tmp_path, monkeypatch) -> None:
        """get_data 中 page_size 超大应被归一为 500。"""
        import pandas as pd
        from backend.services import data_service as data_module

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        excel_path = output_dir / "O76_traces.xlsx"
        excel_path.write_bytes(b"placeholder")

        def fake_read_excel(path, *, sheet_name, header):
            return pd.DataFrame({"A": list(range(1000)), "B": list(range(1000))})

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(output_dir), input_dir=str(tmp_path))

        result = service.get_data("O76", "走向与长度", page=1, page_size=9999)
        assert result["page_size"] == 500
        assert len(result["data"]) == 500

    def test_get_data_normalizes_page_size_below_1(self, tmp_path, monkeypatch) -> None:
        """get_data 中 page_size < 1 应被归一为 1。"""
        import pandas as pd
        from backend.services import data_service as data_module

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        excel_path = output_dir / "O76_traces.xlsx"
        excel_path.write_bytes(b"placeholder")

        def fake_read_excel(path, *, sheet_name, header):
            return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(output_dir), input_dir=str(tmp_path))

        result = service.get_data("O76", "走向与长度", page=1, page_size=0)
        assert result["page_size"] == 1
        assert len(result["data"]) == 1

    def test_get_input_data_normalizes_page_zero(self, tmp_path, monkeypatch) -> None:
        """_get_input_data 中 page=0 应被归一为 1。"""
        import pandas as pd
        from backend.services import data_service as data_module

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        excel_path = input_dir / "O76_process.xlsx"
        excel_path.write_bytes(b"placeholder")

        def fake_read_excel(path, *args, **kwargs):
            return pd.DataFrame(
                [[1, 2, 30, 4, 5, 6, 7, 8, 9],
                 [10, 11, 12, 13, 14, 15, 16, 17, 18]]
            )

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(tmp_path), input_dir=str(input_dir))

        result = service.get_data("O76", "原始输入", page=0, page_size=1, source="input")
        assert result["page"] == 1
        assert len(result["data"]) == 1

    def test_get_input_data_normalizes_page_size_above_500(self, tmp_path, monkeypatch) -> None:
        """_get_input_data 中 page_size 超大应被归一为 500。"""
        import pandas as pd
        from backend.services import data_service as data_module

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        excel_path = input_dir / "O76_process.xlsx"
        excel_path.write_bytes(b"placeholder")

        def fake_read_excel(path, *args, **kwargs):
            return pd.DataFrame(
                [[i] * 9 for i in range(600)]
            )

        monkeypatch.setattr(data_module.pd, "read_excel", fake_read_excel)
        service = DataService(output_dir=str(tmp_path), input_dir=str(input_dir))

        result = service.get_data("O76", "原始输入", page=1, page_size=9999, source="input")
        assert result["page_size"] == 500
        assert len(result["data"]) == 500
