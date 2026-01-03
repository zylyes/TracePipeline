"""包导出接口：汇总常用函数以便上层脚本导入。

在包的顶层导入这些符号可以简化主脚本的导入逻辑，例如
from trace_pipeline import load_config, process_target 等。
"""

from .config import ensure_io_paths, find_trace_tables, load_config
from .data_loader import ParsedTraceData, load_trace_data
from .excel_export import build_excel_sections, write_excel_sections
from .geometry import parse_trace_table
from .plotting import build_nan_lines, render_trace_plot, configure_plotting_style
from .transforms import norm_rotate_lines

__all__ = [
    "ensure_io_paths",
    "find_trace_tables",
    "load_config",
    "ParsedTraceData",
    "load_trace_data",
    "build_excel_sections",
    "write_excel_sections",
    "parse_trace_table",
    "build_nan_lines",
    "render_trace_plot",
    "configure_plotting_style",
    "norm_rotate_lines",
]
