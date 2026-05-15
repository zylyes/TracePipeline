"""流水线执行服务 — 线程安全队列 + 轮询架构。"""
from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any

from trace_pipeline.config import resolve_io_paths
from trace_pipeline.models import RunConfig
from trace_pipeline.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class PipelineService:
    """后台线程执行流水线，前端通过轮询获取进度。"""

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque()
        self._lock = threading.Lock()
        self._running = False

    def run(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        """启动后台线程，非阻塞返回。"""
        if self._running:
            return {"status": "busy", "message": "已有任务正在运行"}
        self._running = True
        self._queue.clear()
        threading.Thread(
            target=self._run_background,
            args=(targets, config),
            daemon=True,
        ).start()
        return {"status": "started", "total": len(targets)}

    def poll_progress(self) -> dict[str, Any] | None:
        """前端轮询接口，线程安全、非阻塞。"""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def is_running(self) -> bool:
        return self._running

    def _emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._queue.append(event)

    def _run_background(self, targets: list[str], config: dict[str, Any]) -> None:
        completed_results: list[dict[str, Any]] = []
        try:
            input_dir = config.get("input_dir", "input")
            output_dir = config.get("output_dir", "output")
            in_path, out_path = resolve_io_paths(input_dir, output_dir)

            total = len(targets)
            logger.info("流水线启动: %d 个目标", total)
            self._emit({
                "type": "start",
                "total": total,
                "current": 0,
                "filename": "",
                "message": "开始处理",
            })

            for idx, outcrop in enumerate(targets, 1):
                table_stem = f"{outcrop}_process"
                logger.info("正在处理: %s (%d/%d)", outcrop, idx, total)
                self._emit({
                    "type": "progress",
                    "current": idx,
                    "total": total,
                    "filename": table_stem,
                    "message": f"正在处理 {outcrop}...",
                })

                cfg = RunConfig.from_mapping({
                    **config,
                    "input_dir": in_path,
                    "output_dir": out_path,
                    "table_stem": table_stem,
                    "outcrop": outcrop,
                    "output_prefix": outcrop,
                    "export_rose_plot": config.get("export_rose_plot", True),
                    "rose_bin_width": config.get("rose_bin_width", 10.0),
                    "rose_dpi": config.get("rose_dpi", 400),
                    "trace_dpi": config.get("trace_dpi", 300),
                    "rotated_trace_dpi": config.get("rotated_trace_dpi", 600),
                    "window_strategy": config.get("window_strategy", "auto"),
                    "auto_density_threshold": config.get("auto_density_threshold", 5.0),
                    "tangent_window_count": config.get("tangent_window_count", 3),
                })

                result = run_pipeline(cfg)
                result_dict = {
                    "outcrop": outcrop,
                    "status": result.status,
                    "trace_count": result.trace_count,
                    "mean_length": result.mean_length,
                    "scanline_azimuth": result.scanline_azimuth,
                    "excel_path": result.excel_path,
                    "raw_plot_path": result.raw_plot_path,
                    "rotated_plot_path": result.rotated_plot_path,
                    "rose_plot_path": result.rose_plot_path,
                    "window_strategy": result.window_strategy,
                    "area_source": result.area_source,
                    "error": result.error,
                    "node_count": result.node_count,
                    "node_x_count": result.node_x_count,
                    "node_y_count": result.node_y_count,
                    "node_i_count": result.node_i_count,
                }
                completed_results.append(result_dict)
                if result.status == "success":
                    logger.info("%s 处理完成", outcrop)
                else:
                    logger.error("%s 处理失败: %s", outcrop, result.error)
                self._emit({
                    "type": "file_complete",
                    "current": idx,
                    "total": total,
                    "filename": table_stem,
                    "message": f"{outcrop} 处理完成" if result.status == "success" else f"{outcrop} 处理失败",
                    "result": result_dict,
                })

            logger.info("流水线全部完成")
            self._emit({
                "type": "complete",
                "current": total,
                "total": total,
                "message": "全部处理完成",
                "results": completed_results,
            })
        except Exception as exc:
            logger.exception("后台流水线异常")
            # 即使异常，也发送已完成的摘要
            self._emit({
                "type": "error",
                "message": f"{type(exc).__name__}: {exc}",
                "completed_count": len(completed_results),
                "total": len(targets),
                "results": completed_results,
            })
        finally:
            self._running = False
