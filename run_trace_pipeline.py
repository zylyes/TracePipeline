"""迹线处理脚本：读取 Excel、计算几何、导出表格与图片。"""
from __future__ import annotations

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from trace_pipeline import ensure_io_paths, find_trace_tables, load_config, configure_plotting_style
from trace_pipeline.pipeline import process_target

def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """配置日志系统，同时输出到控制台和文件。"""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除旧的 handlers
    if logger.handlers:
        logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="岩体节理测线坐标计算与绘图工具")
    parser.add_argument("--input", "-i", help="输入目录路径")
    parser.add_argument("--output", "-o", help="输出目录路径")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--single", "-s", action="store_true", help="仅处理配置文件中指定的单个文件，忽略目录扫描")
    return parser.parse_args()

def main():
    args = parse_args()
    logger = setup_logging()

    try:
        cfg = load_config(args.config)
    except Exception as e:
        logger.critical(f"无法加载配置: {e}")
        return

    # 命令行参数覆盖配置文件
    if args.input:
        cfg["input_dir"] = args.input
    if args.output:
        cfg["output_dir"] = args.output
    if args.single:
        cfg["process_all"] = False

    configure_plotting_style()

    # 校验输入/输出路径并确定待处理的 Excel 列表
    input_dir, output_dir = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    
    logger.info(f"输入目录：{input_dir}")
    logger.info(f"输出目录：{output_dir}")

    discovered = find_trace_tables(input_dir)
    
    # 决定处理目标
    if cfg.get("process_all") and discovered:
        targets = discovered
        logger.info(f"模式：批量处理 (找到 {len(targets)} 个文件)")
    else:
        targets = [(cfg["excel_base"], cfg["outcrop_name"])]
        logger.info(f"模式：单文件处理 ({cfg['excel_base']})")

    run_summaries: List[dict] = []

    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        # 合并运行时配置，方便传递给后续函数
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        summary = process_target(run_cfg)
        run_summaries.append(summary)

        if summary["status"] == "success":
            logger.info(
                f"[{idx}/{len(targets)}] 完成 {excel_base} -> {summary['excel_out']} (迹线数={summary['trace_count']})"
            )
        else:
            logger.warning(f"[{idx}/{len(targets)}] 失败 {excel_base}: {summary.get('error')}")

    if not run_summaries:
        logger.warning(f"未找到可处理的文件，请检查输入目录：{input_dir}")
        return

    success_count = sum(1 for s in run_summaries if s["status"] == "success")
    logger.info(f"处理完成，成功: {success_count}/{len(run_summaries)}")


if __name__ == "__main__":
    main()
