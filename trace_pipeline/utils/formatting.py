"""通用格式化工具。"""
from __future__ import annotations

__all__ = ["format_file_size"]


def format_file_size(num_bytes: int) -> str:
    """将字节数格式化为人类可读的字符串。

    Args:
        num_bytes: 字节数。

    Returns:
        格式化后的字符串，如 "1.5 MB"。
    """
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"
