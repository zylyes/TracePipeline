"""CLI 参数定义与 → 配置覆盖映射。"""
from __future__ import annotations

import argparse
from typing import Any, Dict

__all__ = ["build_overrides", "parse_args"]


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


def build_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """将 CLI 参数转换为配置覆盖字典（仅包含显式指定的项）。"""
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
    return overrides
