"""输出目录结果文件查找工具。"""

from __future__ import annotations

import glob
from pathlib import Path

__all__ = ["find_output_images"]


def _safe_glob_pattern(literal_part: str, wildcard: str = "*") -> str:
    """构建安全的 glob 模式：转义字面特殊字符但保留通配符。

    glob.escape() 会把 ``*`` 转义为 ``[*]``，这里将其恢复为 ``*``，
    确保括号等字面字符在所有平台上都不被解释为通配符。
    """
    escaped = glob.escape(literal_part)
    return escaped.replace("[*]", wildcard)


def find_output_images(out_dir: Path, outcrop: str) -> dict[str, Path | None]:
    """查找指定露头在输出目录中的结果图片。

    Args:
        out_dir: 输出目录路径。
        outcrop: 露头标识。

    Returns:
        包含 "raw" / "rotated" / "rose" 键的字典，值为 Path 或 None。
    """
    raw = next((p for p in out_dir.glob(_safe_glob_pattern(f"{outcrop}_raw") + "*.png")), None)
    rotated = next(
        (p for p in out_dir.glob(_safe_glob_pattern(f"{outcrop}_rotated(strike=") + "*" + _safe_glob_pattern(").png"))),
        None,
    )
    rose = next(
        (p for p in out_dir.glob(_safe_glob_pattern(f"{outcrop}_rose(bin=") + "*" + _safe_glob_pattern(").png"))),
        None,
    )
    return {"raw": raw, "rotated": rotated, "rose": rose}
