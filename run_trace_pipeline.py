"""迹线处理脚本：读取 Excel、计算几何、导出表格与图片。

本脚本作为命令行入口：
- 解析命令行参数（输入/输出目录、配置、单文件模式）
- 加载配置并初始化绘图样式
- 查找或指定要处理的 Excel 表格
- 逐个调用流水线处理并记录日志

注：此文件只负责流程控制与日志，具体实现由 trace_pipeline 包内模块完成。
"""
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
    """配置日志系统，同时输出到控制台和文件。

    返回的 logger 使用模块名作为 logger 名称，文件和控制台分别打印不同级别的信息：
    - 控制台（stdout）：INFO 级别及以上，方便终端交互观察
    - 日志文件：DEBUG 级别及以上，保存完整运行细节以便排查
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 清除已有的 handler，防止多次运行时重复输出
    if logger.handlers:
        logger.handlers.clear()

    # 控制台 Handler：INFO 及以上输出到 stdout，方便交互式查看
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件 Handler：DEBUG 及以上输出到文件，保存完整日志便于排查
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """解析命令行参数。

    支持的参数：
    - --input/-i: 指定输入目录（覆盖 config 中的 input_dir）
    - --output/-o: 指定输出目录（覆盖 config 中的 output_dir）
    - --config/-c: 指定配置文件路径（JSON）
    - --single/-s: 仅处理配置文件中指定的单个文件，忽略目录扫描
    """
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
        # 配置加载失败为致命错误，记录并退出
        logger.critical(f"无法加载配置: {e}")
        return

    # 命令行参数优先覆盖配置文件中的对应项，方便临时指定目录或切换模式
    if args.input:
        cfg["input_dir"] = args.input
    if args.output:
        cfg["output_dir"] = args.output
    if args.single:
        cfg["process_all"] = False

    # 配置 matplotlib，确保中文与符号正常显示
    configure_plotting_style()

    # 校验输入/输出路径并确定待处理的 Excel 列表
    # 若传入的路径无效，ensure_io_paths 会回退到当前工作目录，避免直接抛出异常
    input_dir, output_dir = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    
    logger.info(f"输入目录：{input_dir}")
    logger.info(f"输出目录：{output_dir}")

    # 在输入目录扫描符合命名规则的迹线表（例如以 "_process" 结尾的文件）
    discovered = find_trace_tables(input_dir)
    
    # 决定处理目标
    # 决定处理目标：优先批量处理扫描到的文件，若未扫描到或配置为单文件则使用配置中的单个表
    if cfg.get("process_all") and discovered:
        targets = discovered
        logger.info(f"模式：批量处理 (找到 {len(targets)} 个文件)")
    else:
        targets = [(cfg["excel_base"], cfg["outcrop_name"])]
        logger.info(f"模式：单文件处理 ({cfg['excel_base']})")

    # 存放每次处理的摘要结果（用于最后统计）
    run_summaries: List[dict] = []

    # 逐个处理目标并收集每次运行的摘要信息
    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        # 合并运行时配置为一个字典，便于传递给 pipeline 的函数
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        # 调用核心流水线处理单个目标，返回摘要信息（成功/失败、输出路径等）
        summary = process_target(run_cfg)
        run_summaries.append(summary)

        # 根据返回摘要信息记录日志（成功或警告）
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
