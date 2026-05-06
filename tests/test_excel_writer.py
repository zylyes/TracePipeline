"""单元测试：Excel 分区输出。"""
import numpy as np
from openpyxl import load_workbook

from trace_pipeline.geology.statistics import TraceStatistics
from trace_pipeline.io.excel_writer import build_excel_sections, write_excel_sections
from trace_pipeline.models import TraceData


def _trace():
    return TraceData(
        scanline_azimuth=90.0,
        count=2,
        endpoints=np.array([[0.0, 0.0, 3.0, 4.0], [1.0, 2.0, 4.0, 6.0]]),
        joint_strikes=np.array([10.0, 20.0]),
        segment_lengths=np.array([5.0, 6.0]),
        scanline_positions=np.array([0.0, 10.0]),
    )


def _statistics():
    return TraceStatistics(
        scanline_azimuth=90.0,
        total_count=2,
        type_i_count=1,
        type_ii_count=1,
        type_iii_count=0,
        scanline_length=10.0,
        outcrop_area=20.0,
        mean_trace_length=5.5,
        trace_length_total=11.0,
        p10=0.2,
        p20=0.1,
        p21=0.55,
        scanline_length_source="measured",
        outcrop_area_source="measured",
        trace_length_source="endpoint",
        trace_types=("I", "II"),
        diagnostics=(),
    )


def _write_workbook(tmp_path, statistics=None):
    trace = _trace()
    rotated = trace.endpoints + 1.0
    sections = build_excel_sections(trace, rotated, statistics=statistics)
    path = tmp_path / "O76_traces.xlsx"

    write_excel_sections(str(path), "O76", sections)

    return load_workbook(path)["O76"]


def _summary_values(ws):
    values = {}
    for col in range(1, ws.max_column + 1):
        label = ws.cell(row=2, column=col).value
        if label:
            values[label] = ws.cell(row=3, column=col).value
    return values


def test_write_excel_sections_transposes_summary_and_merges_units(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())

    assert ws["A1"].value == "基本信息与统计指标"
    assert ws["A2"].value == "测线走向"
    assert ws["A3"].value == "90°"
    assert ws["B2"].value == "迹线数量"
    assert ws["B3"].value == "2"
    assert ws["C2"].value == "平均迹线长度"
    assert ws["C3"].value == "5.5 m"
    assert "单位" not in _summary_values(ws)


def test_write_excel_sections_uses_unicode_subscripts_and_superscripts(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())
    summary = _summary_values(ws)

    assert summary["测线长度"] == "10 m"
    assert summary["露头面积"] == "20 m²"
    assert summary["线密度(P₁₀)"] == "0.2 m⁻¹"
    assert summary["面密度(P₂₀)"] == "0.1 m⁻²"
    assert summary["面累计长度密度(P₂₁)"] == "0.55 m⁻¹"
    for removed in (
        "总裂隙数",
        "全部实测平均迹长",
        "I型实测平均迹长",
        "估算平均迹长",
        "I型线密度(P₁₀,I)",
        "全部线密度(P₁₀,all)",
        "估算体密度(P₂₁,est)",
        "实测体密度(P₂₁,obs)",
        "有效取样窗数量",
    ):
        assert removed not in summary


def test_write_excel_sections_uses_compact_gap_columns_and_section_widths(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())

    assert ws.column_dimensions["A"].width == 12
    assert ws.column_dimensions["D"].width == 12
    assert ws.column_dimensions["E"].width == 3
    assert ws.column_dimensions["F"].width == 12
    assert ws.column_dimensions["G"].width == 14
    assert ws.column_dimensions["J"].width == 14
    assert ws.column_dimensions["K"].width == 3
    assert ws.column_dimensions["L"].width == 3
    assert ws.column_dimensions["M"].width == 12
    assert ws.column_dimensions["N"].width == 12
    assert ws.column_dimensions["O"].width == 16
    assert ws.column_dimensions["P"].width == 10
    assert ws.column_dimensions["Q"].width <= 16


def test_write_excel_sections_wraps_headers_and_sets_summary_row_heights(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())

    assert ws["A2"].alignment.wrap_text
    assert ws["G2"].alignment.wrap_text
    assert ws["A6"].alignment.wrap_text
    assert ws["G6"].alignment.wrap_text
    assert ws.row_dimensions[2].height == 36
    assert ws.row_dimensions[3].height == 22
    assert ws.row_dimensions[6].height == 28


def test_write_excel_sections_uses_dynamic_data_start_without_statistics(tmp_path):
    ws = _write_workbook(tmp_path)

    assert _summary_values(ws) == {
        "测线走向": "90°",
        "迹线数量": "2",
        "平均迹线长度": "5 m",
    }
    assert ws["A5"].value == "原始端点坐标"
    assert ws["A6"].value == "起点X"
    assert ws["G5"].value == "旋转后端点坐标"
    assert ws["G6"].value == "旋转后起点X"
    assert ws["M5"].value == "走向与长度"
    assert ws["M6"].value == "节理走向(°)"
    assert ws["A7"].value == 0
    assert ws["G7"].value == 1
    assert ws["N7"].value == 5
    assert ws.freeze_panes == "A7"


def test_write_excel_sections_keeps_trace_types_after_transposed_summary(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())

    assert ws["A5"].value == "原始端点坐标"
    assert ws["A6"].value == "起点X"
    assert ws["G5"].value == "旋转后端点坐标"
    assert ws["M5"].value == "走向与长度"
    assert ws["P6"].value == "迹线类型"
    assert ws["P7"].value == "I"
    assert ws["P8"].value == "II"
    assert ws.freeze_panes == "A7"


def test_write_excel_sections_applies_basic_layout_styles(tmp_path):
    ws = _write_workbook(tmp_path, statistics=_statistics())

    assert ws["A1"].font.bold
    assert ws["A2"].font.bold
    assert ws["A5"].font.bold
    assert ws["A7"].border.left.style == "thin"
    assert ws.column_dimensions["A"].width == 12
    assert ws.column_dimensions["M"].width == 12
