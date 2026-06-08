"""输出目录结果文件查找工具。"""
from __future__ import annotations

from pathlib import Path

__all__ = ["find_output_images"]


def find_output_images(out_dir: Path, outcrop: str) -> dict[str, Path | None]:
    """查找指定露头在输出目录中的结果图片。

    Args:
        out_dir: 输出目录路径。
        outcrop: 露头标识。

    Returns:
        包含 "raw" / "rotated" / "rose" 键的字典，值为 Path 或 None。
    """
    raw = next((p for p in out_dir.glob(f"{outcrop}_raw*.png")), None)
    rotated = next((p for p in out_dir.glob(f"{outcrop}_rotated(strike=*).png")), None)
    rose = next((p for p in out_dir.glob(f"{outcrop}_rose(bin=*).png")), None)
    return {"raw": raw, "rotated": rotated, "rose": rose}
