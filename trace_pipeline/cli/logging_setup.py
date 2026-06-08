"""日志初始化兼容层 — 委托给统一日志系统。

保留原有导入路径 ``from trace_pipeline.cli.logging_setup import setup_logging`` 向后兼容。
"""

from __future__ import annotations

from trace_pipeline.logging import setup_logging

__all__ = ["setup_logging"]
