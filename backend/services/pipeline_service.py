"""流水线执行服务 — 线程安全队列 + 轮询架构。"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

from trace_pipeline.config import resolve_io_paths
from trace_pipeline.logging import LogContext
from trace_pipeline.models import PipelineStatus, RunConfig
from trace_pipeline.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# 保护 matplotlib 全局状态，防止并发绘制时竞争
_EXECUTION_LOCK = threading.Lock()


class PipelineService:
    """后台线程执行流水线，前端通过轮询获取进度。"""

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._running = False

    def run(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        """启动后台线程，非阻塞返回。"""
        with self._lock:
            if self._running:
                return {"status": "busy", "message": "已有任务正在运行"}
            self._running = True
            self._queue.clear()
        self._worker_thread = threading.Thread(
            target=self._run_background,
            args=(targets, config),
            daemon=False,
        )
        self._worker_thread.start()
        return {"status": "started", "total": len(targets)}

    def poll_progress(self) -> dict[str, Any] | None:
        """前端轮询接口，线程安全、非阻塞。"""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def is_running(self) -> bool:
        return self._running

    def shutdown(self, timeout: float = 30.0) -> None:
        """优雅关闭：等待后台线程完成，防止文件写入被强制中断。

        若超时仍未完成，记录警告并强制继续关闭流程（依赖 daemon=False
        时主进程等待；若主进程退出，则线程被强制终止）。
        """
        if not self._running:
            return
        logger.info("正在等待后台流水线完成 (timeout=%.1fs)...", timeout)
        if hasattr(self, "_worker_thread") and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning(
                    "后台流水线未在 %.1fs 内完成，将强制关闭。"
                    "当前可能正在执行长时间绘图或 Excel 写入操作。",
                    timeout,
                )

    def _emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self._queue.append(event)

    def _run_background(self, targets: list[str], config: dict[str, Any]) -> None:
        completed_results: list[dict[str, Any]] = []
        batch_start = time.perf_counter()
        batch_req_id = f"batch-{int(batch_start * 1000)}"
        with LogContext(request_id=batch_req_id):
            try:
                input_dir = config.get("input_dir", "input")
                output_dir = config.get("output_dir", "output")
                in_path, out_path = resolve_io_paths(input_dir, output_dir)

                total = len(targets)
                logger.info(
                    "流水线启动: %d 个目标", total,
                    extra={"stage": "batch_start", "target_count": total, "targets": targets},
                )
                self._emit({
                    "type": "start",
                    "total": total,
                    "current": 0,
                    "filename": "",
                    "message": "开始处理",
                })

                for idx, outcrop in enumerate(targets, 1):
                    table_stem = f"{outcrop}_process"
                    item_start = time.perf_counter()
                    logger.info(
                        "正在处理: %s (%d/%d)", outcrop, idx, total,
                        extra={"stage": "item_start", "outcrop": outcrop, "idx": idx, "total": total},
                    )
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
                        "min_intersections": config.get("min_intersections", 5),
                    })

                    with _EXECUTION_LOCK:
                        result = run_pipeline(cfg)
                    item_duration = (time.perf_counter() - item_start) * 1000
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
                    if result.status is PipelineStatus.SUCCESS:
                        logger.info(
                            "%s 处理完成 (%.3f ms)", outcrop, item_duration,
                            extra={"stage": "item_end", "outcrop": outcrop, "duration_ms": round(item_duration, 3)},
                        )
                    else:
                        logger.error(
                            "%s 处理失败: %s (%.3f ms)", outcrop, result.error, item_duration,
                            extra={"stage": "item_end", "outcrop": outcrop, "error": result.error, "duration_ms": round(item_duration, 3)},
                        )
                    self._emit({
                        "type": "file_complete",
                        "current": idx,
                        "total": total,
                        "filename": table_stem,
                        "message": f"{outcrop} 处理完成" if result.status is PipelineStatus.SUCCESS else f"{outcrop} 处理失败",
                        "result": result_dict,
                    })

                batch_duration = (time.perf_counter() - batch_start) * 1000
                logger.info(
                    "流水线全部完成 (%.3f ms)", batch_duration,
                    extra={"stage": "batch_end", "duration_ms": round(batch_duration, 3), "completed": len(completed_results)},
                )
                self._emit({
                    "type": "complete",
                    "current": total,
                    "total": total,
                    "message": "全部处理完成",
                    "results": completed_results,
                })
            except Exception as exc:
                batch_duration = (time.perf_counter() - batch_start) * 1000
                logger.exception(
                    "后台流水线异常 (%.3f ms)", batch_duration,
                    extra={"stage": "batch_error", "duration_ms": round(batch_duration, 3)},
                )
                self._emit({
                    "type": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                    "completed_count": len(completed_results),
                    "total": len(targets),
                    "results": completed_results,
                })
            finally:
                with self._lock:
                    self._running = False
