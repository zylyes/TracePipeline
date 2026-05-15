"""操作审计日志服务（毕设功能）。"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

AUDIT_PATH = Path("logs/audit.jsonl")
MAX_AUDIT_SIZE = 10 * 1024 * 1024  # 10 MB 上限


class AuditService:
    """记录用户操作到 jsonl 文件，支持查询。"""

    def __init__(self, path: str | Path = AUDIT_PATH) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, params: dict[str, Any] | None = None, result: str = "") -> None:
        """写入一条审计记录，超过 10MB 则轮换。"""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "params": params or {},
            "result": result,
        }
        try:
            if self._path.exists() and self._path.stat().st_size > MAX_AUDIT_SIZE:
                rotated = self._path.with_suffix(".jsonl.old")
                rotated.unlink(missing_ok=True)
                self._path.rename(rotated)
                logger.info("审计日志已轮换")
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("审计日志写入失败: %s", exc)

    def get(self, limit: int = 50) -> list[dict[str, Any]]:
        """读取最近 N 条审计记录。"""
        if not self._path.exists():
            return []
        lines = []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return []
        records: list[dict[str, Any]] = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(records) >= limit:
                break
        return list(reversed(records))
