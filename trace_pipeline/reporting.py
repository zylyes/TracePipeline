"""结果展示 — 格式化输出与汇总报告。

提供处理结果的终端友好展示：
  - 批量结果汇总表
  - 统计摘要
"""
from __future__ import annotations

import unicodedata

from .models import PipelineStatus, RunResult

# ===========================================================================
# 表格常量
# ===========================================================================

_SEP = "-"
_HEADER_SEP = "="
_MIN_COL_WIDTHS = [6, 6, 8, 8, 8, 6, 4]
_COL_HEADERS = ["露头", "迹线数", "平均迹长", "测线走向", "策略", "玫瑰图", "状态"]

_AREA_SOURCE_LABELS = {
    "measured": "实测",
    "hull": "凸包",
    "hull_buffered": "缓冲凸包",
}

_WINDOW_STRATEGY_LABELS = {
    "auto": "自动",
    "tangent": "切线圆窗",
    "hybrid": "混合圆窗",
    "concentric": "同心圆窗",
}


def _format_strategy(r: RunResult) -> str:
    """将面积来源与圆窗策略映射为终端显示中文名。"""
    if r.area_source in _AREA_SOURCE_LABELS:
        return _AREA_SOURCE_LABELS[r.area_source]
    # window / window_equivalent / 其他回退到圆窗策略
    return _WINDOW_STRATEGY_LABELS.get(r.window_strategy, r.window_strategy)


def _display_width(s: str) -> int:
    """计算字符串在等宽终端中的显示宽度（CJK 字符按双宽度计算）。"""
    width = 0
    for ch in s:
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width


def _pad_to_width(s: str, target: int, align: str = "center") -> str:
    """按显示宽度填充字符串。"""
    current = _display_width(s)
    padding = max(0, target - current)
    if align == "left":
        return s + " " * padding
    left = padding // 2
    right = padding - left
    return " " * left + s + " " * right


def _compute_col_widths(rows: list[list[str]]) -> list[int]:
    """根据表头和数据内容动态计算各列宽度。"""
    ncols = len(_COL_HEADERS)
    widths = [max(_MIN_COL_WIDTHS[i], _display_width(_COL_HEADERS[i])) for i in range(ncols)]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], _display_width(cell))
    return widths


def _format_row(values: list[str], widths: list[int]) -> str:
    """按列宽格式化一行（支持 CJK 字符宽度）。"""
    if len(values) != len(widths):
        raise ValueError(f"values 长度 {len(values)} 与 widths 长度 {len(widths)} 不一致")
    cells = [
        _pad_to_width(v, w, "left") if i == 0 else _pad_to_width(v, w)
        for i, (v, w) in enumerate(zip(values, widths))
    ]
    return "| " + " | ".join(cells) + " |"


def _format_separator(widths: list[int], char: str = _SEP) -> str:
    """绘制分隔线；char 为 '=' 时绘制双线分隔（表头/表尾）。"""
    parts = [char * w for w in widths]
    left = "+=" if char == _HEADER_SEP else "+-"
    mid = "=+=" if char == _HEADER_SEP else "-+-"
    right = "=+" if char == _HEADER_SEP else "-+"
    return left + mid.join(parts) + right


def format_results_table(results: list[RunResult]) -> str:
    """将批量处理结果格式化为终端表格。"""
    if not results:
        return "（无结果）"

    data_rows: list[list[str]] = []
    total_traces = 0
    total_length = 0.0
    has_rose = 0
    for r in results:
        stem = r.table_stem
        count = str(r.trace_count)
        avg_len = f"{r.mean_length:.2f}" if r.status is PipelineStatus.SUCCESS else ""
        azimuth = f"{r.scanline_azimuth:.0f}°" if r.status is PipelineStatus.SUCCESS else ""
        strategy = _format_strategy(r) if r.status is PipelineStatus.SUCCESS else ""
        rose = "否"
        status = "OK" if r.status is PipelineStatus.SUCCESS else "FAIL"

        if r.status is PipelineStatus.SUCCESS:
            total_traces += r.trace_count
            total_length += r.mean_length * r.trace_count
            if r.rose_plot_path:
                has_rose += 1
                rose = "是"

        data_rows.append([stem, count, avg_len, azimuth, strategy, rose, status])

    widths = _compute_col_widths(data_rows)
    lines = []
    lines.append(_format_separator(widths, _HEADER_SEP))
    lines.append(_format_row(_COL_HEADERS, widths))
    lines.append(_format_separator(widths, _HEADER_SEP))

    for row in data_rows:
        lines.append(_format_row(row, widths))

    lines.append(_format_separator(widths, _HEADER_SEP))

    success = sum(1 for r in results if r.status is PipelineStatus.SUCCESS)
    lines.append(f"\n总计: {len(results)} 个露头 | 成功 {success} 个 | 迹线总数 {total_traces} | 玫瑰图 {has_rose} 张")

    return "\n".join(lines)


def format_summary(results: list[RunResult]) -> str:
    """生成批量处理的统计摘要。"""
    if not results:
        return "没有可用的处理结果。"

    success = [r for r in results if r.status is PipelineStatus.SUCCESS]
    failed = [r for r in results if r.status is not PipelineStatus.SUCCESS]

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


def print_pipeline_results(results: list[RunResult]) -> None:
    """一站式打印：先输出汇总表，再输出摘要。"""
    print()
    print(format_results_table(results))
    print()
    print(format_summary(results))
    print()


__all__ = [
    "format_results_table",
    "format_summary",
    "print_pipeline_results",
]
