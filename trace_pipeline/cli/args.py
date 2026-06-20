"""CLI 参数定义与 → 配置覆盖映射。"""

from __future__ import annotations

import argparse
from typing import Any

__all__ = ["build_overrides", "parse_args"]


def parse_args() -> argparse.Namespace:
    """解析命令行参数并返回命名空间对象。"""
    parser = argparse.ArgumentParser(description="岩体节理测线坐标计算与绘图工具")
    parser.add_argument("--input", "-i", help="输入目录（覆盖配置文件）")
    parser.add_argument("--output", "-o", help="输出目录（覆盖配置文件）")
    parser.add_argument("--config", "-c", help="JSON 配置文件路径")
    parser.add_argument(
        "--single", "-s", action="store_true", help="单文件模式：仅处理配置中 table_stem 指定的文件"
    )

    def _positive_float(val: str) -> float:
        v = float(val)
        if v <= 0 or v > 180:
            raise argparse.ArgumentTypeError(f"玫瑰图分箱宽度必须在 (0, 180] 范围内，收到: {v}")
        return v

    def _positive_int(val: str) -> int:
        v = int(val)
        if v <= 0 or v > 2400:
            raise argparse.ArgumentTypeError(f"DPI 必须是正整数且不超过 2400，收到: {v}")
        return v

    def _nonnegative_int(val: str) -> int:
        v = int(val)
        if v < 0:
            raise argparse.ArgumentTypeError(f"并行线程数必须为非负整数，收到: {v}")
        return v

    parser.add_argument(
        "--rose-bin", type=_positive_float, default=None, help="玫瑰图分箱宽度（度），覆盖配置文件"
    )
    parser.add_argument(
        "--rose-dpi", type=_positive_int, default=None, help="玫瑰图 DPI，覆盖配置文件"
    )
    parser.add_argument("--no-rose", action="store_true", help="跳过玫瑰图导出")
    parser.add_argument(
        "--window-strategy",
        choices=("auto", "tangent", "hybrid", "concentric"),
        default=None,
        help="圆形取样窗策略，覆盖配置文件",
    )
    parser.add_argument(
        "--parallel",
        "-p",
        type=_nonnegative_int,
        default=0,
        metavar="N",
        help="并行处理线程数（默认 0=串行，设为 0 或 1 为串行）",
    )
    parser.add_argument(
        "--force-parallel",
        action="store_true",
        help="强制并行模式：当目标数较少时默认自动降级为串行，设置此参数可强制使用并行",
    )
    parser.add_argument(
        "--interactive", "-I", action="store_true", help="交互模式：列出文件后由用户选择处理目标"
    )
    parser.add_argument("--list", "-l", action="store_true", help="列出发现的迹线表文件后退出")
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="试运行：列出待处理目标但不实际执行"
    )
    return parser.parse_args()


def build_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """将 CLI 参数转换为配置覆盖字典（仅包含显式指定的项）。"""
    overrides: dict[str, Any] = {}
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
    if args.window_strategy:
        overrides["window_strategy"] = args.window_strategy
    return overrides
