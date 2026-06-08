"""流水线执行服务 — 线程安全队列 + 轮询架构。"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

from backend.utils.path_utils import validate_outcrop_name
from trace_pipeline.config import resolve_io_paths
from trace_pipeline.logging import LogContext
from trace_pipeline.models import PipelineStatus, RunConfig
from trace_pipeline.pipeline import run_pipeline

logger = logging.getLogger(__name__)

# 保护 matplotlib 全局状态，防止并发绘制时竞争。
# 注意：Agg 后端本身线程安全，但 configure_style 使用线程局部上下文管理器，
# 且 PyInstaller 打包环境下 matplotlib 字体缓存非线程安全，因此保留全局锁。
# 若需并行处理多个目标，可改为 per-target 锁 + 预初始化字体缓存。
_EXECUTION_LOCK = threading.Lock()


class PipelineService:
    """后台线程执行流水线，前端通过轮询获取进度。"""

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque()
        self._lock = threading.Lock()
        self._running = False
        self._shutdown_event = threading.Event()
        self._worker_thread: threading.Thread | None = None

    def run(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        """启动后台线程，非阻塞返回。"""
        try:
            validated_targets = [validate_outcrop_name(str(target)) for target in targets]
        except ValueError as exc:
            return {"status": "error", "message": str(exc)}
        if not validated_targets:
            return {"status": "error", "message": "请至少选择一个处理目标"}

        with self._lock:
            if self._running:
                return {"status": "busy", "message": "已有任务正在运行"}
            self._running = True
            self._queue.clear()
            self._shutdown_event.clear()
        self._worker_thread = threading.Thread(
            target=self._run_background,
            args=(validated_targets, config),
            daemon=True,  # daemon=True 确保主进程关闭时线程不会阻止退出
        )
        self._worker_thread.start()
        return {"status": "started", "total": len(validated_targets)}

    def poll_progress(self) -> dict[str, Any] | None:
        """前端轮询接口，线程安全、非阻塞。"""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def is_running(self) -> bool:
        return self._running

    def shutdown(self, timeout: float = 30.0) -> None:
        """优雅关闭：发送取消信号并等待后台线程完成。

        设置 shutdown_event 让工作线程在两个目标之间提前退出，
        然后 join(timeout) 等待线程结束。daemon=True 确保即使
        超时后主进程仍能退出而不会被后台线程阻塞。
        """
        if not self._running:
            return
        logger.info("正在等待后台流水线完成 (timeout=%.1fs)...", timeout)
        self._shutdown_event.set()
        if self._worker_thread is not None and self._worker_thread.is_alive():
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
                    # 检查关闭信号，在两个目标之间提前退出
                    if self._shutdown_event.is_set():
                        logger.info("收到关闭信号，停止处理剩余目标（已完成 %d/%d）", idx - 1, total)
                        self._emit({
                            "type": "complete",
                            "current": idx - 1,
                            "total": total,
                            "message": "处理已被取消",
                            "results": completed_results,
                        })
                        break
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
                    })

                    with _EXECUTION_LOCK:
                        result = run_pipeline(cfg)
                    item_duration = (time.perf_counter() - item_start) * 1000
                    result_dict = {
                        "outcrop": outcrop,
                        "status": result.status.value,
                        "trace_count": result.trace_count,
                        "mean_length": result.mean_length,
                        "scanline_azimuth": result.scanline_azimuth,
                        "excel_path": result.excel_path,
                        "raw_plot": result.raw_plot_path,
                        "rotated_plot": result.rotated_plot_path,
                        "rose_plot": result.rose_plot_path,
                        "window_strategy": result.window_strategy,
                        "area_source": result.area_source,
                        "error": result.error,
                        "error_type": result.error_type,
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
                            "%s 处理失败 [%s]: %s (%.3f ms)", outcrop, result.error_type, result.error, item_duration,
                            extra={"stage": "item_end", "outcrop": outcrop, "error": result.error, "error_type": result.error_type, "duration_ms": round(item_duration, 3)},
                        )
                    fail_hint = ""
                    if result.error_type == "PermissionError":
                        fail_hint = "（文件被占用，请关闭 Excel/WPS 后重试）"
                    elif result.error_type == "FileNotFoundError":
                        fail_hint = "（输入文件不存在）"
                    self._emit({
                        "type": "file_complete",
                        "current": idx,
                        "total": total,
                        "filename": table_stem,
                        "message": f"{outcrop} 处理完成" if result.status is PipelineStatus.SUCCESS else f"{outcrop} 处理失败{fail_hint}",
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
