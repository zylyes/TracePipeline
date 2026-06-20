"""日志读取服务 — 解析结构化 JSON Lines 日志。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trace_pipeline.utils.paths import get_project_root

logger = logging.getLogger(__name__)
_PROJECT_ROOT = get_project_root()
_MAX_LOG_FILES = 3
_MAX_FILE_SIZE = 10 * 1024 * 1024
_READ_CHUNK = 65536
_MAX_TAIL_BUFFER = 2 * 1024 * 1024  # 2MB


def _tail_lines(path: Path, max_lines: int) -> list[str]:
    """从文件末尾反向读取最多 max_lines 行（高效 tail）。"""
    lines: list[str] = []
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        pos = fh.tell()
        buf = bytearray()
        while pos > 0 and len(lines) < max_lines:
            read_size = min(_READ_CHUNK, pos)
            pos -= read_size
            fh.seek(pos)
            chunk = fh.read(read_size)
            buf[:0] = chunk
            if len(buf) > _MAX_TAIL_BUFFER:
                buf = buf[-_MAX_TAIL_BUFFER:]
                logger.warning("日志 tail 读取超过缓冲区上限 %d 字节，已截断", _MAX_TAIL_BUFFER)
                break
            while True:
                nl = buf.rfind(b"\n")
                if nl == -1:
                    break
                line = buf[nl + 1 :].decode("utf-8", errors="replace").strip()
                if line:
                    lines.append(line)
                    if len(lines) >= max_lines:
                        break
                del buf[nl:]
        if buf and len(lines) < max_lines:
            line = buf.decode("utf-8", errors="replace").strip()
            if line:
                lines.append(line)
    lines.reverse()
    return lines


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

        使用反向读取避免全量加载大文件。
        """
        files = self._latest_jsonl_files()
        if not files:
            return []

        files = files[:_MAX_LOG_FILES]
        overread = tail * 4
        records: list[dict[str, Any]] = []
        for f in files:
            if f.stat().st_size > _MAX_FILE_SIZE:
                logger.debug("日志文件过大，跳过: %s", f)
                continue
            try:
                raw_lines = _tail_lines(f, overread)
                for line in raw_lines:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(rec, dict):
                        continue
                    records.append(rec)
            except OSError as exc:
                logger.warning("读取日志文件失败 %s: %s", f, exc)

        records.sort(key=lambda r: r.get("timestamp", ""))

        if level != "ALL":
            level_order = {
                "DEBUG": 10,
                "INFO": 20,
                "WARNING": 30,
                "WARN": 30,
                "ERROR": 40,
                "CRITICAL": 50,
            }
            threshold = level_order.get(level, 20)
            records = [
                r for r in records if level_order.get(r.get("level", "INFO"), 20) >= threshold
            ]

        if len(records) > tail:
            records = records[-tail:]

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
