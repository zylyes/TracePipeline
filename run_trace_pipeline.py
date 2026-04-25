"""迹线处理入口脚本。

命令行参数:
  --input, -i     输入目录（覆盖配置）
  --output, -o    输出目录（覆盖配置）
  --config, -c    配置文件路径（JSON）
  --single, -s    单文件模式（忽略目录扫描）
  --rose-bin      玫瑰图分箱宽度（覆盖配置，度）
  --rose-dpi      玫瑰图 DPI（覆盖配置）
  --no-rose       跳过玫瑰图导出

典型用法:
  python run_trace_pipeline.py
  python run_trace_pipeline.py -i ./data -o ./results
  python run_trace_pipeline.py -s -c my_config.json
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime #
from typing import Any, Dict, List, Tuple

from trace_pipeline import (
    configure_plotting_style,
    ensure_io_paths,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    validate_config,
)
from trace_pipeline.pipeline import process_target


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """双通道日志：控制台 INFO+，文件 DEBUG+。"""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # 控制台
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root.addHandler(ch)

    # 文件
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root.addHandler(fh)

    return logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="岩体节理测线坐标计算与绘图工具",
    )
    parser.add_argument("--input", "-i", help="输入目录（覆盖配置文件）")
    parser.add_argument("--output", "-o", help="输出目录（覆盖配置文件）")
    parser.add_argument("--config", "-c", help="JSON 配置文件路径")
    parser.add_argument("--single", "-s", action="store_true",
                        help="单文件模式：仅处理配置中指定的文件")
    parser.add_argument("--rose-bin", type=float, default=None,
                        help="玫瑰图分箱宽度（度），覆盖配置文件")
    parser.add_argument("--rose-dpi", type=int, default=None,
                        help="玫瑰图 DPI，覆盖配置文件")
    parser.add_argument("--no-rose", action="store_true",
                        help="跳过玫瑰图导出")
    return parser.parse_args()


def apply_cli_overrides(
    cfg: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    """将 CLI 参数合并到配置中。"""
    overrides: Dict[str, Any] = {}
    if args.input:
        overrides["input_dir"] = args.input
    if args.output:
        overrides["output_dir"] = args.output
    if args.single:
        overrides["process_all"] = False
    if args.rose_bin is not None:
        overrides["rose_bin_width"] = args.rose_bin
    if args.rose_dpi is not None:
        overrides["rose_dpi"] = args.rose_dpi
    if args.no_rose:
        overrides["export_rose_plot"] = False

    if overrides:
        cfg = {**cfg, **overrides}
        cfg = validate_config(cfg)
    return cfg


# ---------------------------------------------------------------------------
# 目标决策
# ---------------------------------------------------------------------------

def decide_targets(
    cfg: Dict[str, Any],
    discovered: List[Tuple[str, str]],
    logger: logging.Logger,
) -> List[Tuple[str, str]]:
    """批量/单文件模式决策。"""
    if cfg.get("process_all", True):
        if discovered:
            logger.info("模式：批量处理（发现 %d 个文件）", len(discovered))
            return discovered
        logger.warning("批量模式下未发现匹配文件，回退为单文件处理")
    logger.info("模式：单文件处理（%s）", cfg["excel_base"])
    return [(cfg["excel_base"], cfg["outcrop_name"])]


def build_run_config(
    cfg: Dict[str, Any],
    input_dir: str,
    output_dir: str,
    excel_base: str,
    outcrop_name: str,
) -> Dict[str, Any]:
    """构造单个目标的运行时配置字典。"""
    return {
        **cfg,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "file_name": outcrop_name,
        "excel_base": excel_base,
        "outcrop_name": outcrop_name,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI 入口。"""
    args = parse_args()
    logger = setup_logging()

    # ---- 配置 ----
    try:
        cfg = load_config(args.config)
        cfg = apply_cli_overrides(cfg, args)
    except Exception as exc:
        logger.critical("配置加载失败: %s", exc)
        sys.exit(1)

    configure_plotting_style()

    base_dir = resolve_config_base_dir(args.config)
    input_dir, output_dir = ensure_io_paths(
        cfg["input_dir"], cfg["output_dir"], base_dir=base_dir,
    )

    logger.info("输入目录：%s", input_dir)
    logger.info("输出目录：%s", output_dir)

    discovered = find_trace_tables(input_dir)
    targets = decide_targets(cfg, discovered, logger)

    if not targets:
        logger.warning("没有可处理的目标，退出。")
        return

    # ---- 逐目标处理 ----
    summaries: List[Dict[str, Any]] = []
    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        run_cfg = build_run_config(cfg, input_dir, output_dir, excel_base, outcrop_name)
        summary = process_target(run_cfg)
        summaries.append(summary)

        if summary["status"] == "success":
            logger.info(
                "[%d/%d] 完成 %s → %s（迹线数=%d）",
                idx, len(targets), excel_base,
                summary.get("excel_out", "?"),
                summary.get("trace_count", 0),
            )
        else:
            logger.warning(
                "[%d/%d] 失败 %s: %s",
                idx, len(targets), excel_base, summary.get("error", "未知错误"),
            )

    success_count = sum(1 for s in summaries if s["status"] == "success")
    logger.info("处理完成：成功 %d/%d", success_count, len(summaries))


if __name__ == "__main__":
    main()
