"""CLI 顶层编排：串联参数解析、配置加载、文件发现与执行。"""
from __future__ import annotations

import sys

from ..config import apply_cli_overrides, load_config, resolve_config_base_dir, resolve_io_paths
from ..io.discovery import find_trace_tables
from ..reporting import print_pipeline_results
from .args import build_overrides, parse_args
from .dispatcher import decide_targets, execute_targets
from .interactive import select_targets_interactive
from .logging_setup import setup_logging

__all__ = ["main"]


def _init_plotting() -> None:
    """延迟初始化 matplotlib 后端（仅在需要绘图时调用）。"""
    import matplotlib
    matplotlib.use("Agg")


def main() -> None:
    """CLI 入口：配置加载 → 文件发现 → 目标决策 → 执行 → 汇总。"""
    args = parse_args()
    logger = setup_logging()

    # ---- 1. 加载与校验配置 ----
    try:
        cfg = load_config(args.config)
        overrides = build_overrides(args)
        if overrides:
            cfg = apply_cli_overrides(cfg, **overrides)
    except Exception as exc:
        logger.critical("配置加载失败: %s", exc)
        sys.exit(1)

    # ---- 2. 路径解析与文件发现 ----
    base_dir = resolve_config_base_dir(args.config)
    input_dir, output_dir = resolve_io_paths(
        cfg["input_dir"],
        cfg["output_dir"],
        base_dir=base_dir,
        create_dirs=not (args.list or args.dry_run),
    )
    logger.info("输入目录：%s", input_dir)
    logger.info("输出目录：%s", output_dir)

    discovered = find_trace_tables(input_dir)

    # ---- 3. --list 模式 ----
    if args.list:
        if discovered:
            print(f"\n在 {input_dir} 中发现 {len(discovered)} 个迹线表文件:\n")
            for i, tf in enumerate(discovered, start=1):
                print(f"  [{i:>3}]  {tf.stem}  (露头: {tf.outcrop})")
        else:
            print(f"\n在 {input_dir} 中未发现匹配的迹线表文件。")
        return

    # ---- 4. 目标决策 ----
    if args.interactive:
        if not sys.stdin.isatty():
            logger.error("--interactive 需要交互式终端，当前 stdin 不是 TTY")
            sys.exit(2)
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
        for i, tf in enumerate(targets, start=1):
            print(f"  [{i:>3}]  {tf.stem}  →  输出: {tf.outcrop}_traces.xlsx")
        print(f"\n输入目录:  {input_dir}")
        print(f"输出目录:  {output_dir}")
        print(f"玫瑰图:    {'是' if cfg.get('export_rose_plot', True) else '否'}")
        print("（试运行模式，未执行任何操作）")
        return

    # ---- 6. 执行 ----
    _init_plotting()
    results = execute_targets(
        targets, cfg, input_dir, output_dir,
        workers=args.parallel, logger=logger,
    )

    # ---- 7. 汇总 ----
    print_pipeline_results(results)
    success_count = sum(1 for r in results if r.status == "success")
    logger.info("处理完成：成功 %d/%d", success_count, len(targets))
