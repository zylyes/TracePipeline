"""文件扫描服务。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from trace_pipeline.io.discovery import find_trace_tables

logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FileService:
    """扫描输入目录，返回迹线表文件列表。"""

    def __init__(self, input_dir: str = "input") -> None:
        self.input_dir = self._resolve(input_dir)
        self._output_dir = self._resolve("output")

    def _resolve(self, p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / p
        return path.resolve()

    def scan(self) -> list[dict[str, Any]]:
        """扫描 input_dir，返回文件列表。"""
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
        return results

    def set_output_dir(self, output_dir: str) -> None:
        self._output_dir = self._resolve(output_dir)

    def set_dirs(self, input_dir: str, output_dir: str) -> None:
        self.input_dir = self._resolve(input_dir)
        self._output_dir = self._resolve(output_dir)
