"""文件扫描服务。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.utils.cache import TTLCache
from backend.utils.path_utils import resolve_path
from trace_pipeline.io.discovery import find_trace_tables

logger = logging.getLogger(__name__)

_SCAN_CACHE_KEY = "scan"


class FileService:
    """扫描输入目录，返回迹线表文件列表。"""

    def __init__(self, input_dir: str = "input") -> None:
        self.input_dir = resolve_path(input_dir)
        self._output_dir = resolve_path("output")
        self._cache = TTLCache(ttl=3.0)
        logger.info("FileService 已初始化（带扫描缓存）", extra={"stage": "file_service_init", "scan_ttl": self._cache._ttl})

    def scan(self) -> list[dict[str, Any]]:
        """扫描 input_dir，返回文件列表（带缓存）。"""
        cached = self._cache.get(_SCAN_CACHE_KEY)
        if cached is not None:
            logger.debug("scan 命中缓存: %d 个文件", len(cached), extra={"stage": "file_scan_cache_hit", "count": len(cached)})
            return cached
        logger.info(
            "扫描输入目录: %s", self.input_dir,
            extra={"stage": "file_scan", "input_dir": str(self.input_dir), "output_dir": str(self._output_dir)},
        )
        tables = find_trace_tables(str(self.input_dir))
        results: list[dict[str, Any]] = []
        for tf in tables:
            outcrop = tf.outcrop
            has_raw = next(self._output_dir.glob(f"{outcrop}_raw*.png"), None) is not None
            has_rotated = next(self._output_dir.glob(f"{outcrop}_rotated*.png"), None) is not None
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
        self._cache.set(_SCAN_CACHE_KEY, results)
        return results

    def invalidate_cache(self) -> None:
        """使扫描缓存失效。"""
        self._cache.invalidate()
        logger.debug("scan 缓存已失效", extra={"stage": "file_scan_cache_invalidate"})

    def set_output_dir(self, output_dir: str) -> None:
        self._output_dir = resolve_path(output_dir)

    def set_dirs(self, input_dir: str, output_dir: str) -> None:
        self.input_dir = resolve_path(input_dir)
        self._output_dir = resolve_path(output_dir)
        self.invalidate_cache()
