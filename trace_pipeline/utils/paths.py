"""项目路径解析工具。"""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

__all__ = ["get_project_root", "get_resource_root"]


@cache
def get_project_root() -> Path:
    """推断项目根目录，兼容开发模式与 PyInstaller 打包模式。

    打包模式下使用 ``sys.executable`` 所在目录（EXE 旁），用于创建
    input / output / logs / config.json 等用户可写文件。

    Returns:
        项目根目录的绝对 Path。
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).resolve().parent.parent.parent.resolve()


@cache
def get_resource_root() -> Path:
    """推断只读资源根目录，兼容开发模式与 PyInstaller 打包模式。

    打包模式下使用 ``sys._MEIPASS``（PyInstaller 临时解压目录），
    用于读取 backend/static 等打包内只读资源。

    Returns:
        资源根目录的绝对 Path。
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).parent.resolve()
    return Path(__file__).resolve().parent.parent.parent.resolve()
