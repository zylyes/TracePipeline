"""目标决策与执行（串/并统一）。"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Sequence

from tqdm import tqdm

from ..io.discovery import TraceFile
from ..models import RunConfig, RunResult
from ..pipeline import run_pipeline

__all__ = ["decide_targets", "execute_targets"]


def decide_targets(
    cfg: Dict[str, Any],
    discovered: Sequence[TraceFile],
    logger: logging.Logger,
) -> List[TraceFile]:
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
    cfg: Dict[str, Any],
    input_dir: str,
    output_dir: str,
    target: TraceFile,
) -> RunConfig:
    return RunConfig.from_mapping({
        **cfg,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "output_prefix": target.outcrop,
        "table_stem": target.stem,
        "outcrop": target.outcrop,
    })


def execute_targets(
    targets: Sequence[TraceFile],
    cfg: Dict[str, Any],
    input_dir: str,
    output_dir: str,
    workers: int,
    logger: logging.Logger,
) -> List[RunResult]:
    """执行目标列表，支持串/并行模式，返回结果列表。"""
    results: List[RunResult] = []
    total = len(targets)
    parallel = workers > 1

    if parallel:
        logger.info("启用并行处理：%d 线程", workers)
        pbar = tqdm(total=total, desc="处理迹线表", unit="个", ncols=100)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {}
            for target in targets:
                try:
                    run_cfg = _build_run_config(cfg, input_dir, output_dir, target)
                except Exception as exc:
                    results.append(RunResult.failure(target.stem, str(exc)))
                    pbar.update(1)
                    continue
                future_map[executor.submit(run_pipeline, run_cfg)] = target.stem

            for future in as_completed(future_map):
                stem = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = RunResult.failure(stem, str(exc))
                results.append(result)
                pbar.set_postfix_str(f"完成: {stem}")
                pbar.update(1)
        pbar.close()
    else:
        pbar = tqdm(targets, desc="处理迹线表", unit="个", ncols=100)
        for target in pbar:
            pbar.set_postfix_str(f"当前: {target.stem}")
            try:
                run_cfg = _build_run_config(cfg, input_dir, output_dir, target)
            except Exception as exc:
                results.append(RunResult.failure(target.stem, str(exc)))
                continue

            result = run_pipeline(run_cfg)
            results.append(result)

            if result.status == "success":
                logger.info(
                    "完成 %s → %s（迹线数=%d）",
                    target.stem, result.excel_path, result.trace_count,
                )
            else:
                logger.warning("失败 %s: %s", target.stem, result.error)
        pbar.close()

    return results
