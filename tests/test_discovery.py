"""单元测试：io.discovery"""
import pandas as pd

from trace_pipeline.io.discovery import TraceFile, find_trace_tables


def _make_xlsx(path):
    pd.DataFrame([[0] * 9]).to_excel(path, header=False, index=False)


class TestFindTraceTables:
    def test_nonexistent_dir(self, tmp_path):
        assert find_trace_tables(str(tmp_path / "nope")) == []

    def test_empty_dir(self, tmp_path):
        assert find_trace_tables(str(tmp_path)) == []

    def test_discovers_xlsx(self, tmp_path):
        _make_xlsx(tmp_path / "O76_process.xlsx")
        _make_xlsx(tmp_path / "O77_process.xlsx")
        _make_xlsx(tmp_path / "not_matching.xlsx")

        result = find_trace_tables(str(tmp_path))
        assert len(result) == 2
        assert all(isinstance(tf, TraceFile) for tf in result)
        stems = [tf.stem for tf in result]
        outcrops = [tf.outcrop for tf in result]
        assert "O76_process" in stems
        assert "O76" in outcrops

    def test_tuple_unpacking_compat(self, tmp_path):
        """TraceFile 应可按 (stem, outcrop) 元组方式解包。"""
        _make_xlsx(tmp_path / "Foo_process.xlsx")
        [(stem, outcrop)] = find_trace_tables(str(tmp_path))
        assert stem == "Foo_process"
        assert outcrop == "Foo"
