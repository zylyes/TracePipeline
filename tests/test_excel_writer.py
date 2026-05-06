"""单元测试：Excel 四区输出。"""
import numpy as np
from openpyxl import load_workbook

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


def test_write_excel_sections_uses_expected_layout(tmp_path):
    trace = _trace()
    rotated = trace.endpoints + 1.0
    sections = build_excel_sections(trace, rotated)
    path = tmp_path / "O76_traces.xlsx"

    write_excel_sections(str(path), "O76", sections)

    workbook = load_workbook(path)
    ws = workbook["O76"]

    assert ws["A1"].value == "测线走向(°)"
    assert ws["A2"].value == 90.0
    assert ws["B1"].value == "迹线数量"
    assert ws["B2"].value == 2
    assert ws["A4"].value == "起点X"
    assert ws["G4"].value == "旋转后起点X"
    assert ws["M4"].value == "节理走向(°)"
    assert ws["A5"].value == 0.0
    assert ws["G5"].value == 1.0
    assert ws["N5"].value == 5.0
    assert ws.column_dimensions["A"].width == 14
