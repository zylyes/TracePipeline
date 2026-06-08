"""日志上下文 — request_id 传播与计时工具。"""

from __future__ import annotations

import contextvars
import functools
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

P = ParamSpec("P")
R = TypeVar("R")


def get_request_id() -> str | None:
    """获取当前上下文的请求ID。"""
    return _request_id.get()


def set_request_id(req_id: str | None) -> contextvars.Token[str | None]:
    """设置当前上下文的请求ID，返回 Token 用于恢复。"""
    return _request_id.set(req_id)


class LogContext:
    """上下文管理器：在作用域内绑定 request_id。

    用法:
        with LogContext(request_id="abc-123"):
            logger.info("处理中")  # 自动携带 request_id
    """

    def __init__(self, request_id: str | None = None) -> None:
        self._req_id = request_id or _generate_request_id()
        self._token: contextvars.Token[str | None] | None = None

    def __enter__(self) -> LogContext:
        self._token = set_request_id(self._req_id)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _request_id.reset(self._token)

    @property
    def request_id(self) -> str:
        return self._req_id


def _generate_request_id() -> str:
    """生成一个独特的请求ID（时间戳+UUID短前缀）。"""
    import uuid

    return f"{time.time_ns():x}-{uuid.uuid4().hex[:8]}"


class _TimedContext:
    """计时上下文管理器内部实现。"""

    def __init__(self, logger: Any, level: int, name: str, extra: dict[str, Any] | None) -> None:
        self.logger = logger
        self.level = level
        self.name = name
        self.extra = extra or {}
        self.start: float = 0.0

    def __enter__(self) -> _TimedContext:
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start) * 1000
        extra = {**self.extra, "duration_ms": round(duration_ms, 3)}
        if exc_type is not None:
            extra["error"] = f"{exc_type.__name__}: {exc_val}"
            self.logger.error("[%s] 失败 (%.3f ms)", self.name, duration_ms, extra=extra)
        else:
            self.logger.log(self.level, "[%s] 完成 (%.3f ms)", self.name, duration_ms, extra=extra)


def timed(
    level: int = 20,  # logging.DEBUG=10, INFO=20
    name: str = "",
    extra: dict[str, Any] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]] | _TimedContext:
    """计时装饰器或上下文管理器。

    作为装饰器:
        @timed(logging.INFO, name="数据处理")
        def process_data(...): ...

    作为上下文管理器:
        with timed(logger, logging.INFO, name="文件读取"):
            ...
    """
    import logging

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _name = name or func.__qualname__
            _extra = extra or {}
            _extra.setdefault("func", func.__qualname__)
            _extra.setdefault("module", func.__module__)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                logging.getLogger(func.__module__).log(
                    level,
                    "[%s] 完成 (%.3f ms)",
                    _name,
                    duration_ms,
                    extra={**_extra, "duration_ms": round(duration_ms, 3)},
                )
                return result
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                logging.getLogger(func.__module__).error(
                    "[%s] 失败 (%.3f ms): %s",
                    _name,
                    duration_ms,
                    exc,
                    extra={**_extra, "duration_ms": round(duration_ms, 3), "error": str(exc)},
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


def timed_ctx(
    logger: Any,
    level: int = 20,
    name: str = "",
    extra: dict[str, Any] | None = None,
) -> _TimedContext:
    """返回计时上下文管理器（显式传入 logger）。"""
    return _TimedContext(logger, level, name, extra)
