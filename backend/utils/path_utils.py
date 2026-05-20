"""共享路径解析与错误响应工具。

消除 DataService / FileService / GuiApi 中重复的 _resolve 方法和不一致的错误格式。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trace_pipeline.utils.paths import get_project_root

PROJECT_ROOT = get_project_root()


def resolve_path(p: str, base: Path | None = None) -> Path:
    """将路径解析为绝对路径。

    若路径非绝对，则基于 base 或 PROJECT_ROOT 解析。

    Args:
        p: 输入路径字符串。
        base: 可选基准目录，默认为 PROJECT_ROOT。

    Returns:
        解析后的绝对 Path。
    """
    root = base if base is not None else PROJECT_ROOT
    path = Path(p)
    if not path.is_absolute():
        path = root / p
    return path.resolve()


def error_response(message: str, *, status: str = "error") -> dict[str, Any]:
    """构造统一的错误响应字典。

    所有服务层方法均应使用此函数返回错误，保证前端只需处理一种格式。
    """
    return {"status": status, "message": message}
