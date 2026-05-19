"""项目路径解析工具。"""
from __future__ import annotations

import sys
from pathlib import Path

__all__ = ["get_project_root"]


# 缓存项目根目录，避免重复计算
_project_root: Path | None = None


def get_project_root() -> Path:
    """推断项目根目录，兼容开发模式与 PyInstaller 打包模式。

    打包模式下优先使用 ``sys._MEIPASS``（PyInstaller 解压目录），
    回退到 ``sys.executable`` 所在目录。

    Returns:
        项目根目录的绝对 Path。
    """
    global _project_root  # noqa: PLW0603
    if _project_root is not None:
        return _project_root

    if getattr(sys, "frozen", False):
        # PyInstaller: _MEIPASS 是解压后的资源目录；若不存在则回退到 exe 所在目录
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            _project_root = Path(meipass).resolve()
        else:
            _project_root = Path(sys.executable).parent.resolve()
    else:
        # 本文件位于 trace_pipeline/utils/paths.py，项目根目录为其祖父目录
        _project_root = Path(__file__).resolve().parent.parent.parent.resolve()

    return _project_root
