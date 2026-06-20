"""目标决策与执行（串/并统一）。"""

from __future__ import annotations

import logging
import multiprocessing as mp
import time
from collections.abc import Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from typing import Any

logger = logging.getLogger(__name__)

from tqdm import tqdm

from ..config import DEFAULT_CONFIG
from ..io.discovery import TraceFile
from ..models import PipelineStatus, RunConfig, RunResult
from ..pipeline import run_pipeline

__all__ = ["decide_targets", "execute_targets"]


def decide_targets(
    cfg: dict[str, Any],
    discovered: Sequence[TraceFile],
    logger: logging.Logger,
) -> list[TraceFile]:
    """根据配置模式与扫描结果，决定处理目标列表。"""
    if cfg.get("process_all", True):
        if discovered:
            logger.info("模式：批量处理（发现 %d 个文件）", len(discovered))
            return list(discovered)
        logger.warning("批量模式下未发现匹配文件，回退为单文件处理")

    table_stem = cfg.get("table_stem", "")
    outcrop = cfg.get("outcrop", "")
    logger.info("模式：单文件处理（%s）", table_stem)
    return [TraceFile(stem=table_stem, outcrop=outcrop)]


def _build_run_config(
    cfg: dict[str, Any],
    input_dir: str,
    output_dir: str,
    target: TraceFile,
) -> RunConfig:
    output_prefix = _resolve_output_prefix(cfg, target)
    return RunConfig.from_mapping(
        {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "output_prefix": output_prefix,
            "table_stem": target.stem,
            "outcrop": target.outcrop,
        }
    )


def _resolve_output_prefix(cfg: dict[str, Any], target: TraceFile) -> str:
    """解析输出前缀：批量保持按露头命名，单目标允许显式配置覆盖。"""
    configured_prefix = str(cfg.get("output_prefix", "")).strip()
    custom_prefix = configured_prefix and configured_prefix != DEFAULT_CONFIG["output_prefix"]
    if not cfg.get("process_all", True) and custom_prefix:
        return configured_prefix
    return target.outcrop


def _terminate_worker_processes(
    executor: ProcessPoolExecutor,
    timed_out_futures: set[Any],
) -> None:
    """终止超时任务对应的 worker 进程，防止孤儿进程继续消耗资源。

    ProcessPoolExecutor 的 future.cancel() 只能取消尚未开始的排队任务，
    对正在运行的进程无效。此函数使用 multiprocessing.active_children()
    公开 API 获取活跃子进程并发送终止信号，确保超时进程被真正终止。
    """
    children = mp.active_children()
    if not children:
        logger.debug("无活跃 worker 进程，跳过终止")
        return

    for proc in children:
        try:
            if proc.is_alive():
                logger.warning("终止超时 worker 进程 pid=%d", proc.pid)
                proc.terminate()
        except Exception as exc:
            logger.debug("终止 worker 进程 pid=%s 失败: %s", getattr(proc, "pid", "?"), exc)


def _should_use_serial(targets: Sequence[TraceFile], workers: int) -> bool:
    """判断串行是否可能比并行更快。

    Windows spawn 创建进程的 overhead 约 1-3 秒/进程，
    当目标数很少时，串行总耗时通常更短。
    """
    return len(targets) <= 2


def execute_targets(
    targets: Sequence[TraceFile],
    cfg: dict[str, Any],
    input_dir: str,
    output_dir: str,
    workers: int,
    logger: logging.Logger,
    force_parallel: bool = False,
) -> list[RunResult]:
    """执行目标列表，支持串/并行模式，返回结果列表。"""
    total = len(targets)
    parallel = workers > 1

    if parallel and not force_parallel and _should_use_serial(targets, workers):
        logger.info("目标数较少（%d个），自动切换为串行模式以避免进程创建开销", total)
        logger.info("提示：使用 --force-parallel 可强制并行")
        parallel = False

    if parallel:
        logger.info("启用并行处理：%d 进程", workers)
        parallel_results: list[RunResult | None] = [None] * total
        pbar = tqdm(total=total, desc="处理迹线表", unit="个", ncols=100)
        mp_ctx = mp.get_context("spawn")
        executor = ProcessPoolExecutor(max_workers=workers, mp_context=mp_ctx)
        timed_out = False
        # 跟踪已超时的 future，用于后续终止对应 worker 进程
        _timed_out_futures: set[Any] = set()
        try:
            future_map: dict[Any, tuple[int, str, float]] = {}
            for idx, target in enumerate(targets):
                try:
                    run_cfg = _build_run_config(cfg, input_dir, output_dir, target)
                except Exception as exc:
                    parallel_results[idx] = RunResult.failure(
                        target.stem, str(exc), error_type=type(exc).__name__
                    )
                    pbar.update(1)
                    continue
                future = executor.submit(run_pipeline, run_cfg)
                future_map[future] = (idx, target.stem, time.monotonic() + 300.0)

            pending = set(future_map)
            while pending:
                now = time.monotonic()
                next_deadline = min(deadline for _, _, deadline in (future_map[f] for f in pending))
                timeout = max(0.0, next_deadline - now)
                done, _ = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
                if not done:
                    now = time.monotonic()
                    done = {f for f in pending if future_map[f][2] <= now}
                    timed_out = timed_out or bool(done)

                for future in done:
                    pending.remove(future)
                    idx, stem, deadline = future_map[future]
                    if future.done():
                        try:
                            result = future.result()
                        except Exception as exc:
                            result = RunResult.failure(
                                stem, str(exc), error_type=type(exc).__name__
                            )
                    elif time.monotonic() >= deadline:
                        # 超时：future.cancel() 无法终止已运行的进程，
                        # 但会取消尚未开始的排队任务。
                        future.cancel()
                        _timed_out_futures.add(future)
                        result = RunResult.failure(
                            stem, "处理超时(300s)", error_type="TimeoutError"
                        )
                    else:
                        continue
                    parallel_results[idx] = result
                    pbar.set_postfix_str(f"完成: {stem}")
                    pbar.update(1)

            # 对超时任务对应的 worker 进程发送终止信号，
            # 防止孤儿进程继续消耗 CPU/内存。
            if _timed_out_futures:
                _terminate_worker_processes(executor, _timed_out_futures)
        finally:
            executor.shutdown(wait=not timed_out, cancel_futures=timed_out)
            pbar.close()
        valid = [r for r in parallel_results if r is not None]
        if len(valid) < total:
            logger.warning("并行执行结果不完整: 预期 %d，实际 %d", total, len(valid))
        return valid

    serial_results: list[RunResult] = []
    pbar = tqdm(targets, desc="处理迹线表", unit="个", ncols=100)
    try:
        for target in pbar:
            pbar.set_postfix_str(f"当前: {target.stem}")
            try:
                run_cfg = _build_run_config(cfg, input_dir, output_dir, target)
            except Exception as exc:
                serial_results.append(
                    RunResult.failure(target.stem, str(exc), error_type=type(exc).__name__)
                )
                continue

            try:
                result = run_pipeline(run_cfg)
            except Exception as exc:
                # 单文件崩溃不应中断整批,降级为失败结果并继续
                logger.warning("处理 %s 时发生未捕获异常: %s", target.stem, exc)
                serial_results.append(
                    RunResult.failure(target.stem, str(exc), error_type=type(exc).__name__)
                )
                continue
            serial_results.append(result)

            if result.status is PipelineStatus.SUCCESS:
                logger.info(
                    "完成 %s → %s（迹线数=%d）",
                    target.stem,
                    result.excel_path,
                    result.trace_count,
                )
            else:
                logger.warning("失败 %s: %s", target.stem, result.error)
    finally:
        pbar.close()

    return serial_results
