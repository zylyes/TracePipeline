"""迹线处理入口脚本 — CLI 参数解析与批量调度。

命令行参数:
  --input, -i     输入目录（覆盖配置文件）
  --output, -o    输出目录（覆盖配置文件）
  --config, -c    配置文件路径（JSON）
  --single, -s    单文件模式（忽略目录扫描）
  --rose-bin      玫瑰图分箱宽度（度，覆盖配置文件）
  --rose-dpi      玫瑰图 DPI（覆盖配置文件）
  --no-rose       跳过玫瑰图导出

典型用法:
  python run_trace_pipeline.py
  python run_trace_pipeline.py -i ./data -o ./results
  python run_trace_pipeline.py -s -c my_config.json
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from trace_pipeline import (
    configure_plotting_style,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
    validate_config,
)
from trace_pipeline.pipeline import process_target


# ---------------------------------------------------------------------------
# 日志初始化
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """配置双通道日志：控制台 INFO+，文件 DEBUG+。

    副作用：清空并重新配置根 logger 的所有 handler。
    """
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"pipeline_{timestamp}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root.addHandler(console)

    # 文件 handler
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root.addHandler(file_handler)

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
                        help="单文件模式：仅处理配置中 excel_base 指定的文件")
    parser.add_argument("--rose-bin", type=float, default=None,
                        help="玫瑰图分箱宽度（度），覆盖配置文件")
    parser.add_argument("--rose-dpi", type=int, default=None,
                        help="玫瑰图 DPI，覆盖配置文件")
    parser.add_argument("--no-rose", action="store_true",
                        help="跳过玫瑰图导出")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# 配置合并
# ---------------------------------------------------------------------------

def apply_cli_overrides(cfg: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """将 CLI 参数覆盖到配置字典中，覆盖后重新校验。

    返回新字典，不修改入参 cfg。
    """
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

    if not overrides:
        return cfg

    merged = {**cfg, **overrides}
    return validate_config(merged)


# ---------------------------------------------------------------------------
# 目标决策
# ---------------------------------------------------------------------------

def decide_targets(
    cfg: Dict[str, Any],
    discovered: List[Tuple[str, str]],
    logger: logging.Logger,
) -> List[Tuple[str, str]]:
    """根据配置模式与扫描结果，决定处理目标列表。

    - 批量模式且有匹配文件 → 返回全部 discovered
    - 批量模式但无匹配 → 回退单文件模式
    - 单文件模式 → 返回 [(excel_base, outcrop_name)]
    """
    if cfg.get("process_all", True):
        if discovered:
            logger.info("模式：批量处理（发现 %d 个文件）", len(discovered))
            return discovered
        logger.warning("批量模式下未发现匹配文件，回退为单文件处理")

    logger.info("模式：单文件处理（%s）", cfg["excel_base"])
    return [(cfg["excel_base"], cfg["outcrop_name"])]


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
        cfg = apply_cli_overrides(cfg, args)
    except Exception as exc:
        logger.critical("配置加载失败: %s", exc)
        sys.exit(1)

    configure_plotting_style()

    # ---- 2. 路径解析与文件发现 ----
    base_dir = resolve_config_base_dir(args.config)
    input_dir, output_dir = resolve_io_paths(cfg["input_dir"], cfg["output_dir"], base_dir=base_dir)

    logger.info("输入目录：%s", input_dir)
    logger.info("输出目录：%s", output_dir)

    discovered = find_trace_tables(input_dir)
    targets = decide_targets(cfg, discovered, logger)

    if not targets:
        logger.warning("没有可处理的目标，退出。")
        return

    # ---- 3. 逐目标处理 ----
    total = len(targets)
    summaries: List[Dict[str, Any]] = []

    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        summary = process_target(run_cfg)
        summaries.append(summary)

        if summary["status"] == "success":
            logger.info(
                "[%d/%d] 完成 %s → %s（迹线数=%d）",
                idx, total, excel_base,
                summary.get("excel_out", "?"),
                summary.get("trace_count", 0),
            )
        else:
            logger.warning(
                "[%d/%d] 失败 %s: %s",
                idx, total, excel_base,
                summary.get("error", "未知错误"),
            )

    # ---- 4. 汇总 ----
    success_count = sum(1 for s in summaries if s["status"] == "success")
    logger.info("处理完成：成功 %d/%d", success_count, total)


if __name__ == "__main__":
    main()
