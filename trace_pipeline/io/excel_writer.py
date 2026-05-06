"""Excel result writer with a summary-first single-sheet layout."""
from __future__ import annotations

import logging
import math
import numbers
import os
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..geology.statistics import TraceStatistics
from ..models import TraceData

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_LAYOUT",
    "ExcelLayout",
    "build_excel_sections",
    "write_excel_sections",
]

ExcelSection = Tuple[pd.DataFrame, int, int, bool]
_SECTION_TITLE_KEY = "section_title"
_SUMMARY_TITLES = {"基本信息", "裂隙情况", "计算数据"}


@dataclass(frozen=True)
class ExcelLayout:
    """Layout specification for the generated Excel worksheet."""

    base_info_row: int = 0
    data_gap: int = 1
    raw_col_start: int = 0
    rot_col_start: int = 6
    orient_col_start: int = 12
    column_width: int = 14
    min_column_width: int = 10
    max_column_width: int = 28
    summary_min_width: int = 12
    summary_max_width: int = 16
    gap_column_width: int = 3
    raw_column_width: int = 12
    rotated_column_width: int = 14
    orientation_column_width: int = 12
    segment_length_column_width: int = 16
    trace_type_column_width: int = 10


DEFAULT_LAYOUT = ExcelLayout()


def _with_title(df: pd.DataFrame, title: str) -> pd.DataFrame:
    df.attrs[_SECTION_TITLE_KEY] = title
    return df


def _section_title(df: pd.DataFrame) -> str:
    return str(df.attrs.get(_SECTION_TITLE_KEY, ""))


def _round_float(value: float, digits: int = 4) -> float | None:
    value = float(value)
    if not math.isfinite(value):
        return None
    return round(value, digits)


def _format_value(value, unit: str = "") -> str:
    if value is None:
        text = "N/A"
    elif isinstance(value, numbers.Integral):
        text = str(int(value))
    elif isinstance(value, numbers.Real):
        text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    if unit == "°":
        return f"{text}{unit}"
    return f"{text} {unit}".strip()


def _is_summary_section(df: pd.DataFrame) -> bool:
    return _section_title(df) in _SUMMARY_TITLES


def _one_row_df(items: Sequence[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [[value for _label, value in items]],
        columns=[label for label, _value in items],
    )


def _build_summary_sections(
    trace: TraceData,
    statistics: TraceStatistics | None,
    layout: ExcelLayout,
) -> List[ExcelSection]:
    mean_length = statistics.mean_trace_length if statistics is not None else trace.mean_length
    basic_items = [
        ("测线走向", _format_value(round(trace.scanline_azimuth, 2), "°")),
        (
            "测线长度",
            _format_value(_round_float(statistics.scanline_length), "m")
            if statistics is not None
            else "N/A",
        ),
        ("平均迹长", _format_value(_round_float(mean_length), "m")),
        (
            "露头面积",
            _format_value(_round_float(statistics.outcrop_area), "m²")
            if statistics is not None
            else "N/A",
        ),
    ]
    sections: List[ExcelSection] = [
        (
            _with_title(_one_row_df(basic_items), "基本信息"),
            layout.base_info_row,
            layout.raw_col_start,
            True,
        ),
    ]

    if statistics is None:
        return sections

    fracture_items = [
        ("迹线数量", _format_value(statistics.total_count)),
        ("I型裂隙数", _format_value(statistics.type_i_count)),
        ("II型裂隙数", _format_value(statistics.type_ii_count)),
        ("III型裂隙数", _format_value(statistics.type_iii_count)),
    ]
    calculation_items = [
        ("线密度(P₁₀)", _format_value(_round_float(statistics.p10), "m⁻¹")),
        ("面密度(P₂₀)", _format_value(_round_float(statistics.p20), "m⁻²")),
        ("面累计长度密度(P₂₁)", _format_value(_round_float(statistics.p21), "m⁻¹")),
        ("有效取样窗数量", _format_value(statistics.valid_window_count)),
    ]
    sections.extend([
        (
            _with_title(_one_row_df(fracture_items), "裂隙情况"),
            layout.base_info_row,
            layout.rot_col_start,
            True,
        ),
        (
            _with_title(_one_row_df(calculation_items), "计算数据"),
            layout.base_info_row,
            layout.orient_col_start,
            True,
        ),
    ])
    return sections


def _section_row_count(df: pd.DataFrame, header: bool) -> int:
    return (1 if _section_title(df) else 0) + (1 if header else 0) + len(df)


def build_excel_sections(
    trace: TraceData,
    rotated_xy: np.ndarray,
    statistics: TraceStatistics | None = None,
    layout: ExcelLayout = DEFAULT_LAYOUT,
) -> List[ExcelSection]:
    """Build DataFrame sections for a single worksheet export."""
    if rotated_xy.shape != trace.endpoints.shape:
        raise ValueError(
            f"旋转坐标形状 {rotated_xy.shape} 与原始坐标 {trace.endpoints.shape} 不一致"
        )
    if not np.isfinite(rotated_xy).all():
        raise ValueError("旋转坐标包含 NaN 或 inf")

    summary_sections = _build_summary_sections(trace, statistics, layout)

    raw_df = pd.DataFrame(
        trace.endpoints,
        columns=["起点X", "起点Y", "终点X", "终点Y"],
    )

    rot_df = pd.DataFrame(
        rotated_xy,
        columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"],
    )

    orient_df = pd.DataFrame({
        "节理走向(°)": np.round(trace.joint_strikes, 2),
        "端点距离": np.round(trace.lengths, 4),
        "测段长度(r5+r7)": np.round(trace.segment_lengths, 4),
    })
    if statistics is not None:
        if len(statistics.trace_types) != trace.count:
            raise ValueError(
                f"迹线类型数量 {len(statistics.trace_types)} 与迹线数量 {trace.count} 不一致"
            )
        orient_df["迹线类型"] = list(statistics.trace_types)

    summary_rows = max(
        _section_row_count(df, header)
        for df, _startrow, _startcol, header in summary_sections
    )
    data_row = layout.base_info_row + summary_rows + layout.data_gap
    return [
        *summary_sections,
        (_with_title(raw_df, "原始端点坐标"), data_row, layout.raw_col_start, True),
        (_with_title(rot_df, "旋转后端点坐标"), data_row, layout.rot_col_start, True),
        (_with_title(orient_df, "走向与长度"), data_row, layout.orient_col_start, True),
    ]


def _write_section_title(ws, title: str, startrow: int, startcol: int, column_count: int) -> None:
    if not title:
        return
    row = startrow + 1
    col = startcol + 1
    cell = ws.cell(row=row, column=col, value=title)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="4F81BD")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    if column_count > 1:
        ws.merge_cells(
            start_row=row,
            start_column=col,
            end_row=row,
            end_column=startcol + column_count,
        )


def _style_section(ws, df: pd.DataFrame, startrow: int, startcol: int, header: bool) -> None:
    title_offset = 1 if _section_title(df) else 0
    header_row = startrow + title_offset + 1 if header else None
    first_data_row = startrow + title_offset + (2 if header else 1)
    last_row = startrow + title_offset + (1 if header else 0) + len(df)
    first_col = startcol + 1
    last_col = startcol + df.shape[1]
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    if header and header_row is not None:
        for row in ws.iter_rows(min_row=header_row, max_row=header_row, min_col=first_col, max_col=last_col):
            for cell in row:
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="D9EAF7")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
        ws.row_dimensions[header_row].height = 36 if _is_summary_section(df) else 28

    for row in ws.iter_rows(min_row=first_data_row, max_row=last_row, min_col=first_col, max_col=last_col):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if isinstance(cell.value, numbers.Integral):
                cell.number_format = "0"
            elif isinstance(cell.value, numbers.Real):
                cell.number_format = "0.0000"
    if _is_summary_section(df) and first_data_row <= last_row:
        ws.row_dimensions[first_data_row].height = 22


def _content_width(value) -> int:
    if value is None:
        return 0
    return len(str(value))


def _bounded_content_width(ws, col_idx: int, min_width: int, max_width: int) -> float:
    max_width_seen = 0
    for column in ws.iter_cols(min_col=col_idx, max_col=col_idx, values_only=False):
        for cell in column:
            max_width_seen = max(max_width_seen, _content_width(cell.value))
    return min(max_width, max(min_width, max_width_seen * 1.1 + 2))


def _summary_column_has_label(ws, col_idx: int, sections: Sequence[ExcelSection]) -> bool:
    for df, startrow, startcol, header in sections:
        first_col = startcol + 1
        last_col = startcol + df.shape[1]
        if header and _is_summary_section(df) and first_col <= col_idx <= last_col:
            header_row = startrow + (1 if _section_title(df) else 0) + 1
            value = ws.cell(row=header_row, column=col_idx).value
            return bool(value)
    return False


def _apply_column_widths(ws, sections: Sequence[ExcelSection], max_col: int, layout: ExcelLayout) -> None:
    for col_idx in range(1, max_col + 1):
        zero_based = col_idx - 1
        summary_width = None
        if _summary_column_has_label(ws, col_idx, sections):
            summary_width = _bounded_content_width(
                ws,
                col_idx,
                layout.summary_min_width,
                layout.summary_max_width,
            )

        if zero_based in {4, 5, 10, 11}:
            structural_width = layout.gap_column_width
        elif layout.raw_col_start <= zero_based < layout.raw_col_start + 4:
            structural_width = layout.raw_column_width
        elif layout.rot_col_start <= zero_based < layout.rot_col_start + 4:
            structural_width = layout.rotated_column_width
        elif zero_based == layout.orient_col_start:
            structural_width = layout.orientation_column_width
        elif zero_based == layout.orient_col_start + 1:
            structural_width = layout.orientation_column_width
        elif zero_based == layout.orient_col_start + 2:
            structural_width = layout.segment_length_column_width
        elif zero_based == layout.orient_col_start + 3:
            structural_width = layout.trace_type_column_width
        else:
            structural_width = _bounded_content_width(
                ws,
                col_idx,
                layout.min_column_width,
                layout.max_column_width,
            )
        width = max(summary_width, structural_width) if summary_width is not None else structural_width
        ws.column_dimensions[get_column_letter(col_idx)].width = width


def _freeze_pane_for_sections(sections: Sequence[ExcelSection]) -> str:
    data_starts = [
        startrow
        for df, startrow, _startcol, header in sections
        if header and not _is_summary_section(df)
    ]
    if not data_starts:
        return "A1"
    first_data_start = min(data_starts)
    return f"A{first_data_start + 3}"


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[ExcelSection],
    layout: ExcelLayout = DEFAULT_LAYOUT,
) -> None:
    """Write multiple DataFrame sections into one worksheet."""
    output_dir = os.path.dirname(excel_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    max_col = 0
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for df, startrow, startcol, header in sections:
            title = _section_title(df)
            title_offset = 1 if title else 0
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=header,
                startrow=startrow + title_offset,
                startcol=startcol,
            )
            ws = writer.sheets[sheet_name]
            _write_section_title(ws, title, startrow, startcol, df.shape[1])
            _style_section(ws, df, startrow, startcol, header)
            max_col = max(max_col, startcol + df.shape[1])

        ws = writer.sheets[sheet_name]
        ws.freeze_panes = _freeze_pane_for_sections(sections)
        _apply_column_widths(ws, sections, max_col, layout)

    logger.debug("Excel 写入完成: %s", excel_path)
