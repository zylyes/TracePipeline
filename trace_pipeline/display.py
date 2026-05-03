"""结果展示 — 格式化输出与汇总报告。

提供处理结果的终端友好展示：
  - 单结果详情
  - 批量结果汇总表
  - 统计摘要
"""
from __future__ import annotations

from typing import List

from .models import RunResult


# ===========================================================================
# 表格常量
# ===========================================================================

_SEP = "-"
_HEADER_SEP = "="
_COL_WIDTHS = [10, 8, 10, 10, 8, 6]
_COL_HEADERS = ["露头", "迹线数", "平均迹长", "测线走向", "玫瑰图", "状态"]


def _format_row(values: List[str], widths: List[int]) -> str:
    """按列宽格式化一行。"""
    cells = [v.center(w) if i > 0 else v.ljust(w) for i, (v, w) in enumerate(zip(values, widths))]
    return "| " + " | ".join(cells) + " |"


def _format_separator(widths: List[int], char: str = _SEP) -> str:
    """绘制分隔线。"""
    parts = [char * w for w in widths]
    return "+-" + "-+-".join(parts) + "-+"


def _format_header(widths: List[int]) -> str:
    """绘制表头分隔线（双线）。"""
    parts = [_HEADER_SEP * w for w in widths]
    return "+=" + "=+=".join(parts) + "=+"


def _format_footer(widths: List[int]) -> str:
    """绘制表尾分隔线。"""
    parts = [_HEADER_SEP * w for w in widths]
    return "+=" + "=+=".join(parts) + "=+"


# ===========================================================================
# 公开 API
# ===========================================================================


def format_result_detail(result: RunResult) -> str:
    """格式化单个处理结果的详细信息。

    Returns:
        多行字符串，包含状态、迹线数、输出路径等。
    """
    lines = [
        f"露头: {result.table_stem}",
        f"状态: {result.status}",
    ]
    if result.status == "success":
        lines += [
            f"迹线数量: {result.trace_count}",
            f"Excel 输出: {result.excel_path}",
            f"原始迹线图: {result.raw_plot_path}",
            f"旋转迹线图: {result.rotated_plot_path}",
        ]
        if result.rose_plot_path:
            lines.append(f"玫瑰图: {result.rose_plot_path}")
    else:
        lines.append(f"错误: {result.error}")
    return "\n".join(lines)


def format_results_table(results: List[RunResult]) -> str:
    """将批量处理结果格式化为终端表格。

    Returns:
        Unicode 表格字符串，可直接 print。
    """
    if not results:
        return "（无结果）"

    widths = list(_COL_WIDTHS)
    lines = []

    # 顶线
    lines.append(_format_header(widths))

    # 表头
    lines.append(_format_row(_COL_HEADERS, widths))
    lines.append(_format_separator(widths, _HEADER_SEP))

    # 数据行
    total_traces = 0
    total_length = 0.0
    has_rose = 0
    for r in results:
        stem = r.table_stem
        count = str(r.trace_count)
        avg_len = f"{r.mean_length:.2f}" if r.status == "success" else ""
        azimuth = f"{r.scanline_azimuth:.0f}°" if r.status == "success" else ""
        rose = "否"
        status = "OK" if r.status == "success" else "FAIL"

        if r.status == "success":
            total_traces += r.trace_count
            total_length += r.mean_length * r.trace_count
            if r.rose_plot_path:
                has_rose += 1
                rose = "是"

        row = [stem, count, avg_len, azimuth, rose, status]
        lines.append(_format_row(row, widths))

    # 底线
    lines.append(_format_footer(widths))

    # 汇总行
    success = sum(1 for r in results if r.status == "success")
    lines.append(f"\n总计: {len(results)} 个露头 | 成功 {success} 个 | 迹线总数 {total_traces} | 玫瑰图 {has_rose} 张")

    return "\n".join(lines)


def format_summary(results: List[RunResult]) -> str:
    """生成批量处理的统计摘要。

    Returns:
        多行摘要字符串。
    """
    if not results:
        return "没有可用的处理结果。"

    success = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status != "success"]

    lines = [
        "=" * 56,
        "  处 理 结 果 摘 要",
        "=" * 56,
        f"  总目标数:    {len(results)}",
        f"  成功:        {len(success)}",
        f"  失败:        {len(failed)}",
    ]

    if success:
        total_traces = sum(r.trace_count for r in success)
        total_len = sum(r.mean_length * r.trace_count for r in success)
        avg_len = total_len / total_traces if total_traces else 0.0
        lines.append(f"  总迹线条数:  {total_traces}")
        lines.append(f"  平均迹线数:  {total_traces / len(success):.1f} 条/露头")
        lines.append(f"  加权平均迹长: {avg_len:.2f}")

    if failed:
        lines.append("")
        lines.append("  失败列表:")
        for r in failed:
            lines.append(f"    - {r.table_stem}: {r.error[:80]}")

    lines.append("=" * 56)
    return "\n".join(lines)


def print_pipeline_results(results: List[RunResult]) -> None:
    """一站式打印：先输出汇总表，再输出摘要。

    这是 CLI 调用的推荐入口。
    """
    print()
    print(format_results_table(results))
    print()
    print(format_summary(results))
    print()


__all__ = [
    "format_result_detail",
    "format_results_table",
    "format_summary",
    "print_pipeline_results",
]
