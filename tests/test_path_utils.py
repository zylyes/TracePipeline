"""单元测试 — backend/utils/path_utils.py 露头名校验(防路径遍历)。"""
from __future__ import annotations

import pytest

from backend.utils.path_utils import validate_outcrop_name


class TestValidateOutcropName:
    """validate_outcrop_name 的白名单校验(C3 路径遍历防护)。"""

    @pytest.mark.parametrize("name", ["outcrop1", "露头_01", "site-A", "测点3"])
    def test_valid_names(self, name: str) -> None:
        assert validate_outcrop_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "..",
            "../secret",
            "..\\..\\secret",
            "a/b",
            "a\\b",
            "a.b",
            "a b",
            "a*b",
        ],
    )
    def test_invalid_names_raise(self, name: str) -> None:
        with pytest.raises(ValueError, match="非法的露头名"):
            validate_outcrop_name(name)
