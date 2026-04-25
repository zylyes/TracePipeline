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
from __future__ import annotations # Python 3.7+，允许前向引用类型提示

import argparse # 命令行参数解析
import logging # 日志记录
import os # 文件系统操作
import sys # 系统相关功能
from datetime import datetime # 时间戳生成
from typing import Any, Dict, List, Tuple # 类型提示

from trace_pipeline import (
    configure_plotting_style,
    ensure_io_paths,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    validate_config,
) # 配置和工具函数
from trace_pipeline.pipeline import process_target # 迹线处理核心函数


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

# 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """双通道日志：控制台 INFO+，文件 DEBUG+。"""
    os.makedirs(log_dir, exist_ok=True) # 确保日志目录存在
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # 生成时间戳
    log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log") # 日志文件路径

    root = logging.getLogger() # 获取根日志记录器
    root.setLevel(logging.DEBUG) # 设置最低日志级别为 DEBUG
    root.handlers.clear() # 清除默认处理器，避免重复日志输出

    # 控制台
    ch = logging.StreamHandler(sys.stdout) # 输出到标准输出
    ch.setLevel(logging.INFO) # 设置控制台日志级别为 INFO
    ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")) # 设置日志格式
    root.addHandler(ch) # 添加控制台处理器

    # 文件
    fh = logging.FileHandler(log_file, encoding="utf-8") # 输出到文件
    fh.setLevel(logging.DEBUG) # 设置文件日志级别为 DEBUG
    fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")) # 设置日志格式
    root.addHandler(fh) # 添加文件处理器

    return logging.getLogger(__name__) # 返回当前模块的日志记录器


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# 配置加载与覆盖
def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="岩体节理测线坐标计算与绘图工具",
    ) # 创建参数解析器
    parser.add_argument("--input", "-i", help="输入目录（覆盖配置文件）") # 输入目录参数
    parser.add_argument("--output", "-o", help="输出目录（覆盖配置文件）") # 输出目录参数
    parser.add_argument("--config", "-c", help="JSON 配置文件路径") # 配置文件参数
    parser.add_argument("--single", "-s", action="store_true",
                        help="单文件模式：仅处理配置中指定的文件") # 单文件模式参数
    parser.add_argument("--rose-bin", type=float, default=None,
                        help="玫瑰图分箱宽度（度），覆盖配置文件") # 玫瑰图分箱宽度参数
    parser.add_argument("--rose-dpi", type=int, default=None,
                        help="玫瑰图 DPI，覆盖配置文件") # 玫瑰图 DPI 参数
    parser.add_argument("--no-rose", action="store_true",
                        help="跳过玫瑰图导出") # 跳过玫瑰图参数
    return parser.parse_args() # 返回解析结果


# 配置加载与验证
def apply_cli_overrides(
    cfg: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    """将 CLI 参数合并到配置中。"""
    overrides: Dict[str, Any] = {} # 临时存储覆盖项
    if args.input: # 如果指定了输入目录，覆盖配置中的输入目录
        overrides["input_dir"] = args.input # 覆盖输入目录
    if args.output: # 如果指定了输出目录，覆盖配置中的输出目录
        overrides["output_dir"] = args.output # 覆盖输出目录
    if args.single: # 如果指定了单文件模式，覆盖配置中的处理模式
        overrides["process_all"] = False # 设置为单文件模式
    if args.rose_bin is not None: # 如果指定了玫瑰图分箱宽度，覆盖配置中的分箱宽度
        overrides["rose_bin_width"] = args.rose_bin # 覆盖玫瑰图分箱宽度
    if args.rose_dpi is not None: # 如果指定了玫瑰图 DPI，覆盖配置中的 DPI
        overrides["rose_dpi"] = args.rose_dpi # 覆盖玫瑰图 DPI
    if args.no_rose: # 如果指定了跳过玫瑰图，覆盖配置中的导出选项
        overrides["export_rose_plot"] = False # 设置不导出玫瑰图

    if overrides: # 如果有任何覆盖项，合并到配置中并重新验证
        cfg = {**cfg, **overrides} # 合并覆盖项到配置
        cfg = validate_config(cfg) # 校验新的配置，确保覆盖项合法
    return cfg # 返回最终配置


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
