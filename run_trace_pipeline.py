"""迹线处理入口脚本 — CLI 参数解析与批量调度。

命令行参数:
  --input, -i       输入目录（覆盖配置文件）
  --output, -o      输出目录（覆盖配置文件）
  --config, -c      配置文件路径（JSON）
  --single, -s      单文件模式（忽略目录扫描）
  --rose-bin        玫瑰图分箱宽度（度，覆盖配置文件）
  --rose-dpi        玫瑰图 DPI（覆盖配置文件）
  --no-rose         跳过玫瑰图导出
  --parallel, -p    并行处理线程数（默认 0=串行）
  --list, -l        列出发现的迹线表文件后退出
  --interactive, -I 交互模式：列出文件后由用户选择处理目标
  --dry-run, -n     试运行：打印待处理目标但不实际执行

典型用法:
  python run_trace_pipeline.py
  python run_trace_pipeline.py -i ./data -o ./results
  python run_trace_pipeline.py -s -c my_config.json
  python run_trace_pipeline.py -l
  python run_trace_pipeline.py -I
  python run_trace_pipeline.py -n
  python run_trace_pipeline.py -p 4   # 4 线程并行处理
"""
from __future__ import annotations

import matplotlib as _mpl
_mpl.use("Agg")

import argparse
import logging
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from tqdm import tqdm

from trace_pipeline import (
    apply_cli_overrides,
    configure_style,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
)
from trace_pipeline.types import RunConfig, RunResult
from trace_pipeline.pipeline import run_pipeline


# ---------------------------------------------------------------------------
# 日志初始化
# ---------------------------------------------------------------------------

_CONSOLE_FMT = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
_FILE_FMT = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """配置双通道日志：控制台 INFO+，文件 DEBUG+（幂等）。"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"pipeline_{timestamp}.log"

    root = logging.getLogger()
    if root.level == logging.WARNING and not root.handlers:
        root.setLevel(logging.DEBUG)

    pkg_logger = logging.getLogger("trace_pipeline")
    pkg_logger.setLevel(logging.DEBUG)

    has_file = any(
        isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(log_file)
        for h in pkg_logger.handlers
    )
    if has_file:
        return logging.getLogger(__name__)

    if not any(isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
               for h in pkg_logger.handlers):
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(_CONSOLE_FMT)
        pkg_logger.addHandler(console)

    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FILE_FMT)
    pkg_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI 参数
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """解析命令行参数并返回命名空间对象。"""
    parser = argparse.ArgumentParser(description="岩体节理测线坐标计算与绘图工具")
    parser.add_argument("--input", "-i", help="输入目录（覆盖配置文件）")
    parser.add_argument("--output", "-o", help="输出目录（覆盖配置文件）")
    parser.add_argument("--config", "-c", help="JSON 配置文件路径")
    parser.add_argument("--single", "-s", action="store_true",
                        help="单文件模式：仅处理配置中 table_stem 指定的文件")
    parser.add_argument("--rose-bin", type=float, default=None,
                        help="玫瑰图分箱宽度（度），覆盖配置文件")
    parser.add_argument("--rose-dpi", type=int, default=None,
                        help="玫瑰图 DPI，覆盖配置文件")
    parser.add_argument("--no-rose", action="store_true",
                        help="跳过玫瑰图导出")
    parser.add_argument("--parallel", "-p", type=int, default=0, metavar="N",
                        help="并行处理线程数（默认 0=串行，设为 0 或 1 为串行）")
    parser.add_argument("--interactive", "-I", action="store_true",
                        help="交互模式：列出文件后由用户选择处理目标")
    parser.add_argument("--list", "-l", action="store_true",
                        help="列出发现的迹线表文件后退出")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="试运行：列出待处理目标但不实际执行")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 目标决策
# ---------------------------------------------------------------------------

def decide_targets(
    cfg: Dict[str, Any],
    discovered: List[Tuple[str, str]],
    logger: logging.Logger,
) -> List[Tuple[str, str]]:
    """根据配置模式与扫描结果，决定处理目标列表。"""
    if cfg.get("process_all", True):
        if discovered:
            logger.info("模式：批量处理（发现 %d 个文件）", len(discovered))
            return discovered
        logger.warning("批量模式下未发现匹配文件，回退为单文件处理")

    table_stem = cfg.get("table_stem", "")
    outcrop = cfg.get("outcrop", "")
    logger.info("模式：单文件处理（%s）", table_stem)
    return [(table_stem, outcrop)]


# ---------------------------------------------------------------------------
# 交互式选择
# ---------------------------------------------------------------------------

def _parse_selection(raw: str, max_n: int) -> List[int]:
    """解析用户输入的索引字符串，返回 0-based 索引列表。"""
    cleaned = raw.strip().lower()
    if cleaned in ("", "all", "a"):
        return list(range(max_n))

    selected: List[int] = []
    for token in re.split(r"\s*,\s*", cleaned):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = token.split("-", 1)
            try:
                lo, hi = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError(f"无效区间: {token}")
            if lo < 1 or hi > max_n or lo > hi:
                raise ValueError(f"区间 {lo}-{hi} 超出范围 1-{max_n}")
            selected.extend(range(lo - 1, hi))
        else:
            try:
                idx = int(token)
            except ValueError:
                raise ValueError(f"无效索引: {token}")
            if idx < 1 or idx > max_n:
                raise ValueError(f"索引 {idx} 超出范围 1-{max_n}")
            selected.append(idx - 1)

    if not selected:
        raise ValueError("未选择任何目标")
    return sorted(set(selected))


def select_targets_interactive(
    discovered: Sequence[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    """交互式选择处理目标。"""
    if not discovered:
        print("没有可用的迹线表文件。")
        return []

    print(f"\n发现 {len(discovered)} 个迹线表文件:\n")
    for i, (table_stem, outcrop) in enumerate(discovered, start=1):
        print(f"  [{i:>3}]  {table_stem}  (露头: {outcrop})")

    print("\n输入要处理的编号（支持: all / 1,3,5 / 1-5 / 1,3-5,7）")
    while True:
        try:
            raw = input(">>> ").strip()
            indices = _parse_selection(raw, len(discovered))
            chosen = [discovered[i] for i in indices]
            print(f"已选择 {len(chosen)} 个目标: {', '.join(b for b, _ in chosen)}")
            return chosen
        except ValueError as exc:
            print(f"输入无效: {exc}，请重新输入")
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return []


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI 入口：配置加载 → 文件发现 → 逐目标处理 → 汇总报告。"""
    args = parse_args()
    logger = setup_logging()

    # ---- 1. 加载与校验配置 ----
    try:
        cfg = load_config(args.config)
        cli_overrides: Dict[str, Any] = {}
        if args.input:
            cli_overrides["input_dir"] = args.input
        if args.output:
            cli_overrides["output_dir"] = args.output
        if args.single:
            cli_overrides["process_all"] = False
        if args.rose_bin is not None:
            cli_overrides["rose_bin_width"] = args.rose_bin
        if args.rose_dpi is not None:
            cli_overrides["rose_dpi"] = args.rose_dpi
        if args.no_rose:
            cli_overrides["export_rose_plot"] = False
        if cli_overrides:
            cfg = apply_cli_overrides(cfg, **cli_overrides)
    except Exception as exc:
        logger.critical("配置加载失败: %s", exc)
        sys.exit(1)

    configure_style()

    # ---- 2. 路径解析与文件发现 ----
    base_dir = resolve_config_base_dir(args.config)
    input_dir, output_dir = resolve_io_paths(cfg["input_dir"], cfg["output_dir"], base_dir=base_dir)

    logger.info("输入目录：%s", input_dir)
    logger.info("输出目录：%s", output_dir)

    discovered = find_trace_tables(input_dir)

    # ---- 3. --list 模式 ----
    if args.list:
        if discovered:
            print(f"\n在 {input_dir} 中发现 {len(discovered)} 个迹线表文件:\n")
            for i, (table_stem, outcrop) in enumerate(discovered, start=1):
                print(f"  [{i:>3}]  {table_stem}  (露头: {outcrop})")
        else:
            print(f"\n在 {input_dir} 中未发现匹配的迹线表文件。")
        return

    # ---- 4. 目标决策 ----
    if args.interactive and sys.stdin.isatty():
        targets = select_targets_interactive(discovered)
        if not targets:
            return
    else:
        targets = decide_targets(cfg, discovered, logger)

    if not targets:
        logger.warning("没有可处理的目标，退出。")
        return

    # ---- 5. --dry-run 模式 ----
    if args.dry_run:
        print(f"\n[试运行] 将处理 {len(targets)} 个目标:\n")
        for i, (table_stem, outcrop) in enumerate(targets, start=1):
            print(f"  [{i:>3}]  {table_stem}  →  输出: {outcrop}_traces.xlsx")
        print(f"\n输入目录:  {input_dir}")
        print(f"输出目录:  {output_dir}")
        print(f"玫瑰图:    {'是' if cfg.get('export_rose_plot', True) else '否'}")
        print("（试运行模式，未执行任何操作）")
        return

    # ---- 6. 逐目标处理（支持并行） ----
    total = len(targets)
    results: List[RunResult] = []
    workers = args.parallel if args.parallel > 1 else 0

    def _build_run_config(table_stem: str, outcrop: str) -> RunConfig:
        return RunConfig.from_mapping({
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "output_prefix": outcrop,
            "table_stem": table_stem,
            "outcrop": outcrop,
        })

    if workers:
        logger.info("启用并行处理：%d 线程", workers)
        pbar = tqdm(total=total, desc="处理迹线表", unit="个", ncols=100)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {}
            for table_stem, outcrop in targets:
                try:
                    run_cfg = _build_run_config(table_stem, outcrop)
                except Exception as exc:
                    results.append(RunResult.failure(table_stem, str(exc)))
                    pbar.update(1)
                    continue
                future_map[executor.submit(run_pipeline, run_cfg)] = table_stem

            for future in as_completed(future_map):
                table_stem = future_map[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = RunResult.failure(table_stem, str(exc))
                results.append(result)
                pbar.set_postfix_str(f"完成: {table_stem}")
                pbar.update(1)
        pbar.close()
    else:
        pbar = tqdm(targets, desc="处理迹线表", unit="个", ncols=100)
        for table_stem, outcrop in pbar:
            pbar.set_postfix_str(f"当前: {table_stem}")

            try:
                run_cfg = _build_run_config(table_stem, outcrop)
            except Exception as exc:
                results.append(RunResult.failure(table_stem, str(exc)))
                continue

            result = run_pipeline(run_cfg)
            results.append(result)

            if result.status == "success":
                logger.info(
                    "完成 %s → %s（迹线数=%d）",
                    table_stem, result.excel_path, result.trace_count,
                )
            else:
                logger.warning("失败 %s: %s", table_stem, result.error)
        pbar.close()

    # ---- 7. 汇总 ----
    from trace_pipeline.report import print_pipeline_results
    print_pipeline_results(results)

    success_count = sum(1 for r in results if r.status == "success")
    logger.info("处理完成：成功 %d/%d", success_count, total)


if __name__ == "__main__":
    main()