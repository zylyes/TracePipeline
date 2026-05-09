"""Excel 写入 — 四区布局单工作表输出。"""
from __future__ import annotations

import logging
import math
import numbers
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Color, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..geology.statistics import TraceStatistics
from ..models import TraceData

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_LAYOUT",
    "ExcelLayout",
    "ExcelSection",
    "build_excel_sections",
    "write_excel_sections",
]

_SUMMARY_TITLES = {"基本信息", "裂隙情况", "计算数据"}


@dataclass(frozen=True)
class ExcelSection:
    """单个 Excel 输出区段。"""

    df: pd.DataFrame
    startrow: int
    startcol: int
    header: bool
    title: str = ""


@dataclass(frozen=True)
class ExcelLayout:
    """生成 Excel 工作表的布局规格。"""

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


def _is_summary_section(section: ExcelSection) -> bool:
    return section.title in _SUMMARY_TITLES


_CJK_FONT = "SimSun"
_WESTERN_FONT = "Times New Roman"


def _is_cjk(char: str) -> bool:
    """判断单个字符是否属于 CJK（中文）Unicode 区块。"""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)      # CJK 统一汉字
        or (0x3400 <= cp <= 0x4DBF)   # 扩展 A
        or (0x20000 <= cp <= 0x2A6DF) # 扩展 B
        or (0xF900 <= cp <= 0xFAFF)   # 兼容汉字
        or (0x2F800 <= cp <= 0x2FA1F) # 兼容补充
        or (0x3000 <= cp <= 0x303F)   # CJK 符号与标点
        or (0xFF00 <= cp <= 0xFFEF)   # 全角字符
        or (0x2E80 <= cp <= 0x2FFF)   # 偏旁部首 / 康熙部首 / 表意描述符
        or (0x31C0 <= cp <= 0x31EF)   # CJK 笔画
    )


def _classify_text(text: str) -> str:
    """返回 'cjk' / 'latin' / 'mixed'。"""
    has_cjk = False
    has_other = False
    for ch in text:
        if _is_cjk(ch):
            has_cjk = True
        else:
            has_other = True
        if has_cjk and has_other:
            return "mixed"
    return "cjk" if has_cjk else "latin"


def _build_mixed_font_text(
    value: str,
    bold: bool = False,
    color: str | None = None,
) -> CellRichText:
    """将混合中英文文本拆为 CellRichText，中文=宋体，英文/数字=Times New Roman。"""
    blocks: list[TextBlock] = []
    current_text = ""
    current_cjk: bool | None = None
    for ch in value:
        is_cjk = _is_cjk(ch)
        if current_cjk is None:
            current_cjk = is_cjk
            current_text = ch
        elif is_cjk == current_cjk:
            current_text += ch
        else:
            blocks.append(_make_text_block(current_text, current_cjk, bold, color))
            current_text = ch
            current_cjk = is_cjk
    if current_text:
        assert current_cjk is not None
        blocks.append(_make_text_block(current_text, current_cjk, bold, color))
    return CellRichText(*blocks)


def _make_text_block(
    text: str,
    is_cjk: bool,
    bold: bool,
    color_str: str | None,
) -> TextBlock:
    font_kwargs: dict[str, object] = {"rFont": _CJK_FONT if is_cjk else _WESTERN_FONT}
    if bold:
        font_kwargs["b"] = True
    if color_str:
        font_kwargs["color"] = Color(rgb="00" + color_str)
    return TextBlock(InlineFont(**font_kwargs), text)


def _apply_cell_font(cell, *, bold: bool = False, color: str | None = None) -> None:
    """按单元格内容类型设置字体：中文→宋体，数字/英文→Times New Roman。"""
    value = cell.value
    if value is None:
        return
    if isinstance(value, str):
        classification = _classify_text(value)
        if classification == "mixed":
            cell.value = _build_mixed_font_text(value, bold=bold, color=color)
        else:
            font_name = _CJK_FONT if classification == "cjk" else _WESTERN_FONT
            font_kwargs: dict = {"name": font_name, "bold": bold}
            if color:
                font_kwargs["color"] = color
            cell.font = Font(**font_kwargs)
    elif isinstance(value, (numbers.Integral, numbers.Real)):
        cell.font = Font(name=_WESTERN_FONT, bold=bold)


def _round_float(value: float, digits: int = 4) -> float | None:
    value = float(value)
    if not math.isfinite(value):
        return None
    return round(value, digits)


def _format_excel_cell_value(value, unit: str = "") -> str:
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


def _one_row_df(items: Sequence[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [[value for _label, value in items]],
        columns=[label for label, _value in items],
    )


def _source_tag(source: str) -> str:
    """来源标注短标签，用于 Excel/表格。"""
    mapping = {
        "measured": "M",
        "window": "W",
        "window_equivalent": "W",
        "hull": "E",
        "endpoint": "E",
        "segment": "E",
        "estimated": "est",
    }
    tag = mapping.get(source)
    return f" ({tag})" if tag else ""


def _build_summary_sections(
    trace: TraceData,
    statistics: TraceStatistics | None,
    layout: ExcelLayout,
) -> list[ExcelSection]:
    mean_length = statistics.mean_trace_length if statistics is not None else trace.mean_length
    basic_items = [
        ("测线走向", _format_excel_cell_value(round(trace.scanline_azimuth, 2), "°")),
        (
            "测线长度",
            _format_excel_cell_value(_round_float(statistics.scanline_length), "m")
            if statistics is not None
            else "N/A",
        ),
        ("平均迹长", _format_excel_cell_value(_round_float(mean_length), "m")),
        (
            "露头面积",
            (
                _format_excel_cell_value(_round_float(statistics.outcrop_area), "m²")
                + _source_tag(statistics.outcrop_area_source)
            )
            if statistics is not None
            else "N/A",
        ),
    ]
    sections: list[ExcelSection] = [
        ExcelSection(
            df=_one_row_df(basic_items),
            startrow=layout.base_info_row,
            startcol=layout.raw_col_start,
            header=True,
            title="基本信息",
        ),
    ]

    if statistics is None:
        return sections

    fracture_items = [
        ("迹线数量", _format_excel_cell_value(statistics.total_count)),
        ("I型裂隙数", _format_excel_cell_value(statistics.type_i_count)),
        ("II型裂隙数", _format_excel_cell_value(statistics.type_ii_count)),
        ("III型裂隙数", _format_excel_cell_value(statistics.type_iii_count)),
    ]
    calculation_items = [
        ("线密度(P₁₀)", _format_excel_cell_value(_round_float(statistics.p10), "m⁻¹")),
        (
            "面密度(P₂₀)",
            _format_excel_cell_value(_round_float(statistics.p20), "m⁻²")
            + _source_tag(statistics.p20_source),
        ),
        (
            "面累计长度密度(P₂₁)",
            _format_excel_cell_value(_round_float(statistics.p21), "m⁻¹")
            + _source_tag(statistics.p21_source),
        ),
        ("有效取样窗数量", _format_excel_cell_value(statistics.valid_window_count)),
    ]
    if statistics.window_validation_warning:
        calculation_items.append(
            ("校验告警", statistics.window_validation_warning),
        )
    sections.extend([
        ExcelSection(
            df=_one_row_df(fracture_items),
            startrow=layout.base_info_row,
            startcol=layout.rot_col_start,
            header=True,
            title="裂隙情况",
        ),
        ExcelSection(
            df=_one_row_df(calculation_items),
            startrow=layout.base_info_row,
            startcol=layout.orient_col_start,
            header=True,
            title="计算数据",
        ),
    ])
    return sections


def _section_row_count(section: ExcelSection) -> int:
    return (1 if section.title else 0) + (1 if section.header else 0) + len(section.df)


def build_excel_sections(
    trace: TraceData,
    rotated_xy: np.ndarray,
    statistics: TraceStatistics | None = None,
    layout: ExcelLayout = DEFAULT_LAYOUT,
) -> list[ExcelSection]:
    """构建单工作表导出的 DataFrame 区段。"""
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
        _section_row_count(section)
        for section in summary_sections
    )
    data_row = layout.base_info_row + summary_rows + layout.data_gap
    return [
        *summary_sections,
        ExcelSection(raw_df, data_row, layout.raw_col_start, True, "原始端点坐标"),
        ExcelSection(rot_df, data_row, layout.rot_col_start, True, "旋转后端点坐标"),
        ExcelSection(orient_df, data_row, layout.orient_col_start, True, "走向与长度"),
    ]


def _write_section_title(ws, title: str, startrow: int, startcol: int, column_count: int) -> None:
    if not title:
        return
    row = startrow + 1
    col = startcol + 1
    cell = ws.cell(row=row, column=col, value=title)
    _apply_cell_font(cell, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="4F81BD")
    cell.alignment = Alignment(horizontal="center", vertical="center")
    if column_count > 1:
        ws.merge_cells(
            start_row=row,
            start_column=col,
            end_row=row,
            end_column=startcol + column_count,
        )


def _style_section(ws, section: ExcelSection) -> None:
    title_offset = 1 if section.title else 0
    header_row = section.startrow + title_offset + 1 if section.header else None
    first_data_row = section.startrow + title_offset + (2 if section.header else 1)
    last_row = section.startrow + title_offset + (1 if section.header else 0) + len(section.df)
    first_col = section.startcol + 1
    last_col = section.startcol + section.df.shape[1]
    thin = Side(style="thin", color="D9E2F3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    if section.header and header_row is not None:
        for row in ws.iter_rows(min_row=header_row, max_row=header_row, min_col=first_col, max_col=last_col):
            for cell in row:
                _apply_cell_font(cell, bold=True)
                cell.fill = PatternFill("solid", fgColor="D9EAF7")
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border
        ws.row_dimensions[header_row].height = 36 if _is_summary_section(section) else 28

    for row in ws.iter_rows(min_row=first_data_row, max_row=last_row, min_col=first_col, max_col=last_col):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            _apply_cell_font(cell, bold=False)
            if isinstance(cell.value, numbers.Integral):
                cell.number_format = "0"
            elif isinstance(cell.value, numbers.Real):
                cell.number_format = "0.0000"
    if _is_summary_section(section) and first_data_row <= last_row:
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
    for section in sections:
        first_col = section.startcol + 1
        last_col = section.startcol + section.df.shape[1]
        if section.header and _is_summary_section(section) and first_col <= col_idx <= last_col:
            header_row = section.startrow + (1 if section.title else 0) + 1
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

        if zero_based in {
            layout.raw_col_start + 4,
            layout.raw_col_start + 5,
            layout.rot_col_start + 4,
            layout.rot_col_start + 5,
        }:
            structural_width: float = layout.gap_column_width
        elif layout.raw_col_start <= zero_based < layout.raw_col_start + 4:
            structural_width = layout.raw_column_width
        elif layout.rot_col_start <= zero_based < layout.rot_col_start + 4:
            structural_width = layout.rotated_column_width
        elif zero_based == layout.orient_col_start or zero_based == layout.orient_col_start + 1:
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
        section.startrow
        for section in sections
        if section.header and not _is_summary_section(section)
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
    """将多个 DataFrame 区段写入同一工作表。"""
    output_dir = Path(excel_path).parent
    if str(output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)

    max_col = 0
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for section in sections:
            title_offset = 1 if section.title else 0
            section.df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=section.header,
                startrow=section.startrow + title_offset,
                startcol=section.startcol,
            )
            ws = writer.sheets[sheet_name]
            _write_section_title(ws, section.title, section.startrow, section.startcol, section.df.shape[1])
            _style_section(ws, section)
            max_col = max(max_col, section.startcol + section.df.shape[1])

        ws = writer.sheets[sheet_name]
        ws.freeze_panes = _freeze_pane_for_sections(sections)
        _apply_column_widths(ws, sections, max_col, layout)

    logger.debug("Excel 写入完成: %s", excel_path)
