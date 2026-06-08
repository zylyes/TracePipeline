"""TracePipeline 统一结构化日志系统。

基于 Python 标准库 logging 扩展，提供：
  - JSON Lines 文件输出（按天目录 + 自动打包）
  - 请求ID 跨线程/协程追踪
  - 计时装饰器与上下文管理器
  - 多进程安全写入
"""

from __future__ import annotations

from .context import LogContext, get_request_id, set_request_id, timed, timed_ctx
from .core import DailyRotatingJsonHandler, JsonFormatter, setup_logging, setup_worker_logging

__all__ = [
    "DailyRotatingJsonHandler",
    "JsonFormatter",
    "LogContext",
    "get_request_id",
    "set_request_id",
    "setup_logging",
    "setup_worker_logging",
    "timed",
    "timed_ctx",
]
