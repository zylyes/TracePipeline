"""日志初始化 — 双通道（控制台 INFO+ / 文件 DEBUG+）。"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

_CONSOLE_FMT = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_FILE_FMT = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

__all__ = ["setup_logging"]


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """配置双通道日志：控制台 INFO+，文件 DEBUG+（幂等）。"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"pipeline_{timestamp}.log"

    root = logging.getLogger()
    if root.level == logging.WARNING and not root.handlers:
        root.setLevel(logging.DEBUG)

    pkg_logger = logging.getLogger("trace_pipeline")
    pkg_logger.setLevel(logging.DEBUG)

    has_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(log_file)
        for h in pkg_logger.handlers
    )
    if has_file:
        return logging.getLogger(__name__)

    if not any(
        isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout
        for h in pkg_logger.handlers
    ):
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(_CONSOLE_FMT)
        pkg_logger.addHandler(console)

    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FILE_FMT)
    pkg_logger.addHandler(file_handler)

    return logging.getLogger(__name__)
