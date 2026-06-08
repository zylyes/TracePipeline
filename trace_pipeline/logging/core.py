"""日志核心 — JsonFormatter、DailyRotatingJsonHandler 与初始化入口。"""

from __future__ import annotations

import json
import logging
import math
import os
import shutil
import sys
import threading
import zipfile
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trace_pipeline.utils.numpy_compat import to_native as _to_native

from .context import get_request_id

__all__ = [
    "JsonFormatter",
    "DailyRotatingJsonHandler",
    "setup_logging",
    "setup_worker_logging",
]

# 日志目录与文件命名常量
_LOG_SUBDIR_FMT = "%Y-%m-%d"
_LOG_FILE_PREFIX = "run"
_LOG_SEQ_FMT = "{prefix}_{seq:03d}.jsonl"
_WORKER_FILE_FMT = "worker_{pid}.jsonl"
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB 单文件上限
_KEEP_DAYS = 30  # 保留最近 30 天压缩包

# 用于标记由本系统管理的 Handler
_MANAGED_ATTR = "_tp_logging_managed"

_lock = threading.Lock()


class JsonFormatter(logging.Formatter):
    """将 LogRecord 格式化为单行 JSON。

    输出字段:
        timestamp  : ISO 8601 格式（带时区）
        level      : 日志级别名称
        logger     : logger 名称
        module     : 模块名
        funcName   : 函数名
        lineno     : 行号
        message    : 日志消息
        request_id : 当前请求ID（如有）
        exc_info   : 异常堆栈（如有）
        extra      : 通过 extra= 传入的扩展字段
    """

    def format(self, record: logging.LogRecord) -> str:
        # 使用带时区的 ISO 格式
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        payload: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }

        # request_id
        req_id = get_request_id()
        if req_id is not None:
            payload["request_id"] = req_id

        # 异常信息
        if record.exc_info and record.exc_info != (None, None, None):
            payload["exc_info"] = self.formatException(record.exc_info)

        # 扩展字段（排除 logging 内置属性）
        built_in = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "request_id",
        }
        extras: dict[str, Any] = {}
        for key, val in record.__dict__.items():
            if key not in built_in and not key.startswith("_"):
                extras[key] = val
        if extras:
            payload["extra"] = extras

        # 确保无 NaN/inf（JSON 标准不支持）
        return json.dumps(
            _json_sanitize(payload),
            ensure_ascii=False,
            default=_json_default,
            allow_nan=False,
        )


def _json_default(obj: Any) -> Any:
    """处理 numpy 等不可 JSON 序列化的类型，支持嵌套结构。"""
    result = _to_native(obj, max_depth=10)
    if result is not obj:
        return _json_sanitize(result)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_sanitize(obj: Any, max_depth: int = 20, _depth: int = 0) -> Any:
    """递归转换日志载荷，保证输出为标准 JSON。"""
    if _depth > max_depth:
        return str(obj)

    obj = _to_native(obj, max_depth=max_depth - _depth)
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_sanitize(v, max_depth, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_sanitize(v, max_depth, _depth + 1) for v in obj]
    return obj


class DailyRotatingJsonHandler(logging.FileHandler):
    """按天目录存储 JSON Lines，自动打包前一天日志。

    目录结构:
        logs/
          2026-05-15.zip
          2026-05-16/
            run_001.jsonl
            worker_12345.jsonl
    """

    # 类级锁，防止多线程/多进程同时归档导致竞态
    _ARCHIVE_LOCK = threading.Lock()

    def __init__(
        self,
        log_dir: str | Path = "logs",
        filename: str | None = None,
        max_bytes: int = _MAX_BYTES,
    ) -> None:
        self._log_dir = Path(log_dir).resolve()
        self._day_dir = self._log_dir / datetime.now(timezone.utc).strftime(_LOG_SUBDIR_FMT)
        self._day_dir.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_bytes

        # 自动打包旧日志（加锁保护竞态）
        with self._ARCHIVE_LOCK:
            self._archive_old_days()
            self._cleanup_old_archives()

        # 确定文件名
        if filename is None:
            filename = self._next_seq_filename()
        self._log_path = self._day_dir / filename

        super().__init__(str(self._log_path), mode="a", encoding="utf-8")
        setattr(self, _MANAGED_ATTR, True)

        # 设置 JSON 格式
        self.setFormatter(JsonFormatter())
        self.setLevel(logging.DEBUG)

    def _next_seq_filename(self) -> str:
        """在同天目录中查找最大序号并递增。"""
        seq = 0
        if self._day_dir.is_dir():
            for f in self._day_dir.glob(f"{_LOG_FILE_PREFIX}_*.jsonl"):
                try:
                    num = int(f.stem.split("_")[-1])
                    seq = max(seq, num)
                except ValueError:
                    pass
        return _LOG_SEQ_FMT.format(prefix=_LOG_FILE_PREFIX, seq=seq + 1)

    def _archive_old_days(self) -> None:
        """将非当天的日期目录打包为 zip 后删除。

        多进程安全：通过检查目标 zip 是否已存在 + 异常静默处理，
        避免 ProcessPoolExecutor 下多个 worker 同时归档导致竞态。
        """
        today_name = self._day_dir.name
        if not self._log_dir.is_dir():
            return

        def on_rm_error(func, path, exc_info):
            """处理无法删除的文件（如被锁定或只读）。"""
            import stat

            # 尝试移除只读属性后重试
            os.chmod(path, stat.S_IWRITE)
            func(path)

        for entry in self._log_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.name == today_name:
                continue
            # 验证目录名是否为日期格式 YYYY-MM-DD
            if not _is_date_dir_name(entry.name):
                continue

            zip_path = self._log_dir / f"{entry.name}.zip"
            # 竞态防护：若 zip 已存在，说明其他进程已归档，直接尝试删除原目录
            if zip_path.exists():
                with suppress(OSError):
                    shutil.rmtree(entry, onerror=on_rm_error)
                continue

            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_path in entry.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(entry)
                            zf.write(file_path, arcname)
                # 打包成功后递归删除原目录及其所有内容
                shutil.rmtree(entry, onerror=on_rm_error)
            except FileExistsError:
                # 其他进程刚好在同一时刻创建了 zip，尝试清理原目录即可
                with suppress(OSError):
                    shutil.rmtree(entry, onerror=on_rm_error)
            except OSError as exc:
                # 打包失败不打断启动，只发警告
                logging.getLogger(__name__).warning("日志归档失败 %s: %s", entry, exc)

    def _cleanup_old_archives(self) -> None:
        """清理超过保留期限的 zip 归档。"""
        if not self._log_dir.is_dir():
            return
        now = datetime.now(timezone.utc)
        for entry in self._log_dir.glob("*.zip"):
            try:
                # 从文件名解析日期
                dir_date = datetime.strptime(entry.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (now - dir_date).days
                if age_days > _KEEP_DAYS:
                    entry.unlink()
            except ValueError:
                continue
            except OSError:
                continue

    def emit(self, record: logging.LogRecord) -> None:
        """重写 emit 以支持按大小自动分片（线程安全）。"""
        with self._ARCHIVE_LOCK:
            if self._log_path.exists() and self._log_path.stat().st_size > self._max_bytes:
                self._rotate()
        super().emit(record)

    def _rotate(self) -> None:
        """同目录内分片：run_001.jsonl -> run_001_part_1.jsonl。

        调用方须持有 _ARCHIVE_LOCK，确保 close→rename→open 原子性。
        """
        self.close()
        base = self._log_path.stem
        part = 1
        while True:
            candidate = self._log_path.with_name(f"{base}_part_{part}.jsonl")
            if not candidate.exists():
                break
            part += 1
        self._log_path.rename(candidate)
        self._log_path = self._day_dir / f"{base}.jsonl"
        self.baseFilename = str(self._log_path)
        self.stream = self._open()


def _is_date_dir_name(name: str) -> bool:
    """检查目录名是否为 YYYY-MM-DD 格式。"""
    if len(name) != 10:
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _project_root() -> Path:
    """推断项目根目录。"""
    # 复用 trace_pipeline.config 中的 PROJECT_ROOT 定义，保持一致性
    from trace_pipeline.config import PROJECT_ROOT

    return PROJECT_ROOT


def setup_logging(
    log_dir: str | Path | None = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> logging.Logger:
    """初始化统一日志系统（幂等）。

    为主进程配置：
      - ConsoleHandler: 人类可读格式，级别 console_level
      - DailyRotatingJsonHandler: JSON Lines，级别 file_level
    """
    log_dir = _project_root() / "logs" if log_dir is None else Path(log_dir).resolve()

    pkg_logger = logging.getLogger("trace_pipeline")
    pkg_logger.setLevel(min(console_level, file_level))
    pkg_logger.propagate = False

    with _lock:
        # 幂等：复用已存在的托管 handler，避免二次调用时引用未初始化局部变量。
        console = next(
            (
                h
                for h in pkg_logger.handlers
                if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.FileHandler)
                and getattr(h, _MANAGED_ATTR, False)
            ),
            None,
        )
        file_handler = next(
            (
                h
                for h in pkg_logger.handlers
                if isinstance(h, DailyRotatingJsonHandler) and getattr(h, _MANAGED_ATTR, False)
            ),
            None,
        )

        if console is None:
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            setattr(console, _MANAGED_ATTR, True)
            pkg_logger.addHandler(console)
        console.setLevel(console_level)

        if file_handler is None:
            file_handler = DailyRotatingJsonHandler(log_dir=log_dir)
            pkg_logger.addHandler(file_handler)
        file_handler.setLevel(file_level)

        # 合并 backend 到 trace_pipeline：让 backend 的日志也写入同一个 run_XXX.jsonl
        backend_logger = logging.getLogger("backend")
        backend_logger.setLevel(min(console_level, file_level))
        backend_logger.propagate = False  # 关闭 propagate，直接添加 handler
        backend_logger.handlers.clear()  # 清除旧 handler，避免重复

        # 给 backend logger 添加与 trace_pipeline 相同的 handler
        if not any(
            isinstance(h, DailyRotatingJsonHandler) and getattr(h, _MANAGED_ATTR, False)
            for h in backend_logger.handlers
        ):
            backend_logger.addHandler(file_handler)
        if not any(
            isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
            and getattr(h, _MANAGED_ATTR, False)
            for h in backend_logger.handlers
        ):
            backend_logger.addHandler(console)

    return pkg_logger


def setup_worker_logging(log_dir: str | Path | None = None) -> logging.Logger:
    """子进程专用日志初始化（ProcessPoolExecutor worker）。

    子进程不继承父进程的文件描述符，因此需要独立创建 Handler。
    写入同一天目录，文件名带 worker PID。
    """
    log_dir = _project_root() / "logs" if log_dir is None else Path(log_dir).resolve()

    pkg_logger = logging.getLogger("trace_pipeline")
    pkg_logger.setLevel(logging.DEBUG)
    pkg_logger.propagate = False

    # 清除可能从父进程继承的 StreamHandler（避免重复输出到已关闭的 stdout）
    for h in list(pkg_logger.handlers):
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            pkg_logger.removeHandler(h)

    # 清除非托管的 FileHandler
    for h in list(pkg_logger.handlers):
        if isinstance(h, logging.FileHandler) and not getattr(h, _MANAGED_ATTR, False):
            h.close()
            pkg_logger.removeHandler(h)

    # 如果已有托管的 DailyRotatingJsonHandler，不重复创建
    if any(
        isinstance(h, DailyRotatingJsonHandler) and getattr(h, _MANAGED_ATTR, False)
        for h in pkg_logger.handlers
    ):
        return pkg_logger

    pid = os.getpid()
    filename = _WORKER_FILE_FMT.format(pid=pid)
    handler = DailyRotatingJsonHandler(log_dir=log_dir, filename=filename)
    handler.setLevel(logging.DEBUG)
    pkg_logger.addHandler(handler)

    # 子进程也保留一个精简的 stderr 输出，方便调试
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter(f"[worker-{pid}] %(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    setattr(console, _MANAGED_ATTR, True)
    pkg_logger.addHandler(console)

    return pkg_logger
