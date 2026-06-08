"""操作审计日志服务 — 合并到统一结构化日志流。

保留对外接口 ``log()`` / ``get()``，内部通过统一 logger 输出，
日志随主日志文件一起按天归档。
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

from trace_pipeline.utils.paths import get_project_root

logger = logging.getLogger("backend.audit")
_PROJECT_ROOT = get_project_root()


class AuditService:
    """记录用户操作到统一日志流，通过 event_type="audit" 区分。"""

    def __init__(self) -> None:
        self._buffer: deque[dict[str, Any]] = deque(maxlen=200)

    def log(self, action: str, params: dict[str, Any] | None = None, result: str = "") -> None:
        """写入一条审计记录到统一 JSON 日志。"""
        logger.info(
            "audit: %s",
            action,
            extra={
                "event_type": "audit",
                "action": action,
                "params": params or {},
                "result": result,
            },
        )
        self._buffer.appendleft(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "params": params or {},
                "result": result,
            }
        )

    def get(self, limit: int = 50) -> list[dict[str, Any]]:
        """从内存缓冲区读取最近 N 条审计记录，回退到文件扫描。"""
        if self._buffer:
            return list(self._buffer)[:limit]

        log_dir = _PROJECT_ROOT / "logs"
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = log_dir / today
        if not day_dir.is_dir():
            return []

        records: list[dict[str, Any]] = []
        for f in sorted(day_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
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
                        if rec.get("event_type") == "audit" or (
                            rec.get("extra", {}).get("event_type") == "audit"
                        ):
                            audit_rec: dict[str, Any] = {
                                "timestamp": rec.get("timestamp", ""),
                                "action": rec.get("extra", {}).get("action", ""),
                                "params": rec.get("extra", {}).get("params", {}),
                                "result": rec.get("extra", {}).get("result", ""),
                            }
                            records.append(audit_rec)
            except OSError:
                continue
            if len(records) >= limit:
                break

        return records[:limit]
