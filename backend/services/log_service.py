"""日志读取服务 — 解析结构化 JSON Lines 日志。"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

if getattr(sys, "frozen", False):
    _PROJECT_ROOT = Path(sys.executable).parent
else:
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LogService:
    """读取 logs/ 目录下的 JSON Lines 日志文件。"""

    def __init__(self, log_dir: str = "") -> None:
        path = Path(log_dir) if log_dir else _PROJECT_ROOT / "logs"
        self._log_dir = path.resolve()

    def _today_dir(self) -> Path | None:
        """返回当天的日志目录。"""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        d = self._log_dir / today
        return d if d.is_dir() else None

    def _latest_jsonl_files(self) -> list[Path]:
        """获取当天目录下所有 jsonl 文件，按修改时间降序。"""
        d = self._today_dir()
        if d is None:
            return []
        files = [p for p in d.glob("*.jsonl") if p.is_file()]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def get_logs(self, tail: int = 100, level: str = "INFO") -> list[str]:
        """读取最新日志文件的最后 N 行，返回格式化字符串列表。

        Args:
            tail: 返回最近多少条。
            level: 过滤级别（DEBUG/INFO/WARNING/ERROR/ALL）。
        """
        files = self._latest_jsonl_files()
        if not files:
            return []

        # 读取所有 jsonl 文件内容，合并后按时间排序
        records: list[dict[str, Any]] = []
        for f in files:
            try:
                with f.open("r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if not isinstance(rec, dict):
                            continue
                        records.append(rec)
            except OSError as exc:
                logger.warning("读取日志文件失败 %s: %s", f, exc)

        # 按时间戳排序
        records.sort(key=lambda r: r.get("timestamp", ""))

        # 级别过滤
        if level != "ALL":
            level_order = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "WARN": 30, "ERROR": 40, "CRITICAL": 50}
            threshold = level_order.get(level, 20)
            records = [
                r for r in records
                if level_order.get(r.get("level", "INFO"), 20) >= threshold
            ]

        # 取尾部
        if len(records) > tail:
            records = records[-tail:]

        # 格式化为人类可读字符串
        lines: list[str] = []
        for r in records:
            ts = r.get("timestamp", "")
            lvl = r.get("level", "INFO")
            mod = r.get("logger", "")
            msg = r.get("message", "")
            req_id = r.get("request_id")
            duration = r.get("extra", {}).get("duration_ms")
            parts = [ts, f"[{lvl}]", mod, ":", msg]
            if req_id:
                parts.insert(2, f"req={req_id}")
            if duration is not None:
                parts.append(f"({duration} ms)")
            lines.append(" ".join(parts))

        return lines
