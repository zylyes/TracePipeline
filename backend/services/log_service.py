"""日志读取服务。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


if getattr(sys, 'frozen', False):
    _PROJECT_ROOT = Path(sys.executable).parent
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LogService:
    """读取 logs/ 目录下的日志文件。"""

    def __init__(self, log_dir: str = "") -> None:
        path = Path(log_dir) if log_dir else _PROJECT_ROOT / "logs"
        self._log_dir = path.resolve()

    def get_logs(self, tail: int = 100, level: str = "INFO") -> list[str]:
        """读取最新日志文件的最后 N 行。"""
        if not self._log_dir.is_dir():
            return []
        log_files = sorted(self._log_dir.glob("pipeline_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            return []
        latest = log_files[0]
        try:
            lines = latest.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        # 过滤级别（日志格式: "时间 - 模块 - LEVEL - 内容"）
        if level != "ALL":
            lines = [ln for ln in lines if f" - {level} - " in ln]
        return lines[-tail:] if len(lines) > tail else lines
