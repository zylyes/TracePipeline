"""单元测试：交互选择解析。"""
import pytest

from trace_pipeline.cli.interactive import _parse_selection


def test_parse_selection_defaults_to_all():
    assert _parse_selection("", 3) == [0, 1, 2]
    assert _parse_selection("all", 3) == [0, 1, 2]


def test_parse_selection_comma_range_and_deduplicate():
    assert _parse_selection("1, 3-5, 3", 5) == [0, 2, 3, 4]


def test_parse_selection_rejects_out_of_range_index():
    with pytest.raises(ValueError, match="索引 4 超出范围"):
        _parse_selection("4", 3)


def test_parse_selection_rejects_out_of_range_range():
    with pytest.raises(ValueError, match="区间 2-4 超出范围"):
        _parse_selection("2-4", 3)


def test_parse_selection_rejects_invalid_token():
    with pytest.raises(ValueError, match="无效索引"):
        _parse_selection("x", 3)
