"""流水线执行服务 — 线程安全队列 + 轮询架构。"""

from __future__ import annotations

import logging
import multiprocessing as mp
import threading
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

from backend.utils.path_utils import validate_outcrop_name
from trace_pipeline.config import resolve_io_paths
from trace_pipeline.logging import LogContext
from trace_pipeline.models import PipelineStatus, RunConfig, RunResult
from trace_pipeline.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def _available_cpu_count() -> int:
    """返回可用 CPU 核心数；平台无法识别时保守退回 1。"""
    try:
        count = int(mp.cpu_count())
    except (NotImplementedError, TypeError, ValueError):
        logger.warning("无法识别 CPU 核心数，parallel_workers 将退回 1")
        return 1
    return max(count, 1)


class PipelineService:
    """后台线程执行流水线，前端通过轮询获取进度。"""

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque(maxlen=2000)
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
        # 非守护线程 + 显式 shutdown()：避免主进程退出时强制中断正在写入文件/Excel 的操作
        self._worker_thread = threading.Thread(
            target=self._run_background,
            args=(validated_targets, config),
            daemon=False,
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
        然后 join(timeout) 等待线程结束。线程为非守护线程，确保
        当前文件/Excel 写入完成后主进程才退出；若超时仍未完成则
        记录警告并继续关闭流程。
        """
        with self._lock:
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
        completed_count = 0
        batch_start = time.perf_counter()
        batch_req_id = f"batch-{int(batch_start * 1000)}"
        with LogContext(request_id=batch_req_id):
            try:
                input_dir = config.get("input_dir", "input")
                output_dir = config.get("output_dir", "output")
                in_path, out_path = resolve_io_paths(input_dir, output_dir)

                total = len(targets)
                logger.info(
                    "流水线启动: %d 个目标",
                    total,
                    extra={"stage": "batch_start", "target_count": total, "targets": targets},
                )
                self._emit(
                    {
                        "type": "start",
                        "total": total,
                        "current": 0,
                        "filename": "",
                        "message": "开始处理",
                    }
                )

                # 检查关闭信号，在提交任务之前提前退出
                if self._shutdown_event.is_set():
                    logger.info("收到关闭信号，取消本次处理")
                    self._emit(
                        {
                            "type": "complete",
                            "current": 0,
                            "total": total,
                            "message": "处理已被取消",
                            "completed_count": 0,
                        }
                    )
                    return

                # 构建任务配置（不在此处发进度，避免一次性刷到 100%）
                task_configs: list[tuple[str, str, int]] = []
                for idx, outcrop in enumerate(targets, 1):
                    table_stem = f"{outcrop}_process"
                    task_configs.append((outcrop, table_stem, idx))

                # 使用 multiprocessing 并行执行
                # parallel_workers: 0=自动(cpu_count), 1=单进程串行, >1=指定进程数
                requested = int(config.get("parallel_workers", 0) or 0)
                cpu_count = _available_cpu_count()
                if requested <= 0:
                    workers = min(len(task_configs), cpu_count)
                elif requested == 1:
                    workers = 1  # 1 个进程 = 串行（但仍在独立进程中）
                else:
                    workers = min(len(task_configs), requested, cpu_count)
                    if workers < requested:
                        logger.debug(
                            "parallel_workers 请求 %d 被 CPU 核心数 %d 裁剪为 %d",
                            requested, cpu_count, workers,
                        )
                ctx = mp.get_context("spawn")
                logger.info(
                    "并行执行: %d 个工作进程，%d 个目标 (请求=%d, CPU=%d)",
                    workers,
                    total,
                    requested,
                    cpu_count,
                    extra={
                        "stage": "parallel_start",
                        "workers": workers,
                        "total": total,
                        "requested": requested,
                        "cpu_count": cpu_count,
                    },
                )
                self._emit(
                    {
                        "type": "progress",
                        "current": 0,
                        "total": total,
                        "filename": "",
                        "message": f"并行处理中（{workers} 进程）...",
                    }
                )
                with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as executor:
                    future_to_info: dict[Any, tuple[str, str, int, float]] = {}
                    for outcrop, table_stem, idx in task_configs:
                        cfg = RunConfig.from_mapping(
                            {
                                **config,
                                "input_dir": in_path,
                                "output_dir": out_path,
                                "table_stem": table_stem,
                                "outcrop": outcrop,
                                "output_prefix": outcrop,
                            }
                        )
                        item_start = time.perf_counter()
                        future = executor.submit(run_pipeline, cfg)
                        future_to_info[future] = (outcrop, table_stem, idx, item_start)

                    for future in as_completed(future_to_info):
                        # 检查关闭信号
                        if self._shutdown_event.is_set():
                            logger.info(
                                "收到关闭信号，停止处理剩余目标（已完成 %d/%d）",
                                completed_count,
                                total,
                            )
                            executor.shutdown(wait=False, cancel_futures=True)
                            self._emit(
                                {
                                    "type": "complete",
                                    "current": completed_count,
                                    "total": total,
                                    "message": "处理已被取消",
                                    "completed_count": completed_count,
                                }
                            )
                            return

                        outcrop, table_stem, idx, item_start = future_to_info[future]
                        try:
                            result = future.result()
                        except (MemoryError, SystemExit, KeyboardInterrupt):
                            raise  # 关键异常不吞没，向上传播
                        except Exception as exc:
                            result = RunResult.failure(
                                table_stem=table_stem,
                                error=str(exc),
                                error_type=type(exc).__name__,
                            )
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
                        completed_count += 1
                        self._emit(
                            {
                                "type": "progress",
                                "current": completed_count,
                                "total": total,
                                "filename": table_stem,
                                "message": f"{outcrop} 处理完成 ({completed_count}/{total})",
                            }
                        )
                        if result.status is PipelineStatus.SUCCESS:
                            logger.info(
                                "%s 处理完成 (%.3f ms)",
                                outcrop,
                                item_duration,
                                extra={
                                    "stage": "item_end",
                                    "outcrop": outcrop,
                                    "duration_ms": round(item_duration, 3),
                                },
                            )
                        else:
                            logger.error(
                                "%s 处理失败 [%s]: %s (%.3f ms)",
                                outcrop,
                                result.error_type,
                                result.error,
                                item_duration,
                                extra={
                                    "stage": "item_end",
                                    "outcrop": outcrop,
                                    "error": result.error,
                                    "error_type": result.error_type,
                                    "duration_ms": round(item_duration, 3),
                                },
                            )
                        fail_hint = ""
                        if result.error_type == "PermissionError":
                            fail_hint = "（文件被占用，请关闭 Excel/WPS 后重试）"
                        elif result.error_type == "FileNotFoundError":
                            fail_hint = "（输入文件不存在）"
                        self._emit(
                            {
                                "type": "file_complete",
                                "current": completed_count,
                                "total": total,
                                "filename": table_stem,
                                "message": f"{outcrop} 处理完成"
                                if result.status is PipelineStatus.SUCCESS
                                else f"{outcrop} 处理失败{fail_hint}",
                                "result": result_dict,
                            }
                        )

                batch_duration = (time.perf_counter() - batch_start) * 1000
                logger.info(
                    "流水线全部完成 (%.3f ms)",
                    batch_duration,
                    extra={
                        "stage": "batch_end",
                        "duration_ms": round(batch_duration, 3),
                        "completed": completed_count,
                    },
                )
                self._emit(
                    {
                        "type": "complete",
                        "current": total,
                        "total": total,
                        "message": "全部处理完成",
                        "completed_count": completed_count,
                    }
                )
            except (MemoryError, SystemExit, KeyboardInterrupt):
                raise  # 关键异常不吞没，向上传播
            except Exception as exc:
                batch_duration = (time.perf_counter() - batch_start) * 1000
                logger.exception(
                    "后台流水线异常 (%.3f ms)",
                    batch_duration,
                    extra={"stage": "batch_error", "duration_ms": round(batch_duration, 3)},
                )
                self._emit(
                    {
                        "type": "error",
                        "message": f"{type(exc).__name__}: {exc}",
                        "completed_count": completed_count,
                        "total": len(targets),
                    }
                )
            finally:
                with self._lock:
                    self._running = False
