"""字体与 CJK 文本处理工具。"""
from __future__ import annotations

__all__ = ["is_cjk", "classify_text"]


def is_cjk(char: str) -> bool:
    """判断单个字符是否属于 CJK（中文）Unicode 区块。"""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)      # CJK 统一汉字
        or (0x3400 <= cp <= 0x4DBF)   # 扩展 A
        or (0x20000 <= cp <= 0x2A6DF) # 扩展 B
        or (0xF900 <= cp <= 0xFAFF)   # 兼容汉字
        or (0x2F800 <= cp <= 0x2FA1F) # 兼容补充
        or (0x3000 <= cp <= 0x303F)   # CJK 符号与标点
        or (0xFF00 <= cp <= 0xFFEF)   # 全角字符
        or (0x2E80 <= cp <= 0x2FFF)   # 偏旁部首 / 康熙部首 / 表意描述符
        or (0x31C0 <= cp <= 0x31EF)   # CJK 笔画
    )


def classify_text(text: str) -> str:
    """将文本按字符集分类。

    Returns:
        'cjk' — 纯 CJK 字符
        'latin' — 非 CJK 字符
        'mixed' — 混合
    """
    has_cjk = False
    has_other = False
    for ch in text:
        if is_cjk(ch):
            has_cjk = True
        else:
            has_other = True
        if has_cjk and has_other:
            return "mixed"
    return "cjk" if has_cjk else "latin"
