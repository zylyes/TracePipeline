"""I/O 子包：Excel 读取、写入与文件发现。"""

from .discovery import TRACE_SUFFIX, TraceFile, find_trace_tables
from .excel_reader import read_trace_excel
from .excel_writer import (
    DEFAULT_LAYOUT,
    ExcelLayout,
    build_result_workbook_sections,
    write_excel_multi_sheets,
)

__all__ = [
    "DEFAULT_LAYOUT",
    "ExcelLayout",
    "TRACE_SUFFIX",
    "TraceFile",
    "build_result_workbook_sections",
    "find_trace_tables",
    "read_trace_excel",
    "write_excel_multi_sheets",
]
