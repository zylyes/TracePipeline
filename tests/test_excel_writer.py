"""单元测试 — io/excel_writer.py 混合中英文字体分段。"""

from __future__ import annotations

from openpyxl.cell.rich_text import CellRichText

from trace_pipeline.io.excel_writer import (
    _CJK_BODY_FONT,
    _WESTERN_FONT,
    _build_mixed_font_text,
)


class TestBuildMixedFontText:
    """_build_mixed_font_text 的分段与字体测试。

    回归重点(C2):首字符的 CJK 判定曾把函数对象误赋给状态变量,
    导致英文/数字开头的文本首段错用宋体。
    """

    @staticmethod
    def _fonts(rich: CellRichText) -> list[str]:
        return [block.font.rFont for block in rich]

    def test_english_first_uses_western_font(self) -> None:
        """英文开头:首段必须用 Times New Roman,而非宋体。"""
        rich = _build_mixed_font_text("ab中文", _CJK_BODY_FONT)
        fonts = self._fonts(rich)
        assert fonts[0] == _WESTERN_FONT
        assert fonts[-1] == _CJK_BODY_FONT

    def test_cjk_first_uses_cjk_font(self) -> None:
        """中文开头:首段用宋体。"""
        rich = _build_mixed_font_text("中文ab", _CJK_BODY_FONT)
        fonts = self._fonts(rich)
        assert fonts[0] == _CJK_BODY_FONT
        assert fonts[-1] == _WESTERN_FONT

    def test_pure_english_single_block(self) -> None:
        """纯英文:单段,西文字体。"""
        rich = _build_mixed_font_text("hello", _CJK_BODY_FONT)
        fonts = self._fonts(rich)
        assert fonts == [_WESTERN_FONT]

    def test_digits_first(self) -> None:
        """数字开头:首段西文字体。"""
        rich = _build_mixed_font_text("123米", _CJK_BODY_FONT)
        fonts = self._fonts(rich)
        assert fonts[0] == _WESTERN_FONT
