"""共享路径解析与错误响应工具。

消除 DataService / FileService / GuiApi 中重复的 _resolve 方法和不一致的错误格式。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from trace_pipeline.utils.paths import get_project_root

PROJECT_ROOT = get_project_root()

# 露头名白名单：字母、数字、下划线、连字符、中文。禁止路径分隔符与 ".." 等。
_OUTCROP_PATTERN = re.compile(r"^[\w\-一-龥]+$")


def validate_outcrop_name(outcrop: str) -> str:
    """校验露头名,防止路径遍历。

    露头名会被拼入文件名(如 ``{outcrop}_traces.xlsx``),必须禁止
    路径分隔符、``..`` 及其他可能逃逸目录的字符。

    Args:
        outcrop: 前端传入的露头标识符。

    Returns:
        校验通过的露头名(原样返回)。

    Raises:
        ValueError: 露头名为空或含非法字符。
    """
    if not outcrop or not _OUTCROP_PATTERN.match(outcrop):
        raise ValueError(f"非法的露头名: {outcrop!r}")
    return outcrop


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
