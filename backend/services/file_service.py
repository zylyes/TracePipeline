"""文件扫描服务。"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

from trace_pipeline.config import PROJECT_ROOT
from trace_pipeline.io.discovery import find_trace_tables

logger = logging.getLogger(__name__)


class FileService:
    """扫描输入目录，返回迹线表文件列表。"""

    def __init__(self, input_dir: str = "input") -> None:
        self.input_dir = self._resolve(input_dir)
        self._output_dir = self._resolve("output")
        self._scan_cache: tuple[list[dict[str, Any]], float] | None = None
        self._scan_ttl = 3.0  # 3秒缓存（避免短时间内重复扫描，但用户手动刷新能立即生效）
        logger.info("FileService 已初始化（带扫描缓存）", extra={"stage": "file_service_init", "scan_ttl": self._scan_ttl})

    def _resolve(self, p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / p
        return path.resolve()

    def scan(self) -> list[dict[str, Any]]:
        """扫描 input_dir，返回文件列表（带缓存）。"""
        if self._scan_cache:
            results, ts = self._scan_cache
            if time.monotonic() - ts < self._scan_ttl:
                logger.debug("scan 命中缓存: %d 个文件", len(results), extra={"stage": "file_scan_cache_hit", "count": len(results)})
                return results
        logger.info(
            "扫描输入目录: %s", self.input_dir,
            extra={"stage": "file_scan", "input_dir": str(self.input_dir), "output_dir": str(self._output_dir)},
        )
        tables = find_trace_tables(str(self.input_dir))
        results: list[dict[str, Any]] = []
        for tf in tables:
            outcrop = tf.outcrop
            # 检查 output 中是否已有结果（通配匹配）
            has_raw = bool(list(self._output_dir.glob(f"{outcrop}_raw*.png")))
            has_rotated = bool(list(self._output_dir.glob(f"{outcrop}_rotated*.png")))
            status = "completed" if has_raw and has_rotated else "pending"
            results.append({
                "stem": tf.stem,
                "outcrop": outcrop,
                "path": str(self.input_dir / tf.stem),
                "status": status,
            })
            logger.debug(
                "  发现迹线表: %s [%s]", outcrop, status,
                extra={"stage": "file_scan_item", "outcrop": outcrop, "stem": tf.stem, "status": status},
            )
        logger.info(
            "扫描完成: %d 个文件 (待处理 %d / 已完成 %d)",
            len(results),
            sum(1 for r in results if r["status"] == "pending"),
            sum(1 for r in results if r["status"] == "completed"),
            extra={
                "stage": "file_scan_done",
                "total": len(results),
                "pending": sum(1 for r in results if r["status"] == "pending"),
                "completed": sum(1 for r in results if r["status"] == "completed"),
            },
        )
        self._scan_cache = (results, time.monotonic())
        return results

    def invalidate_cache(self) -> None:
        """使扫描缓存失效。"""
        self._scan_cache = None
        logger.debug("scan 缓存已失效", extra={"stage": "file_scan_cache_invalidate"})

    def set_output_dir(self, output_dir: str) -> None:
        self._output_dir = self._resolve(output_dir)

    def set_dirs(self, input_dir: str, output_dir: str) -> None:
        self.input_dir = self._resolve(input_dir)
        self._output_dir = self._resolve(output_dir)
        self.invalidate_cache()
