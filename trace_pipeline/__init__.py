"""trace_pipeline — 岩体节理测线坐标计算与绘图工具包。"""
from __future__ import annotations

from .config import (
    CONFIG_PATH,
    DEFAULT_CONFIG,
    PROJECT_ROOT,
    ensure_io_paths,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    validate_config,
)
from .data_loader import ParsedTraceData, load_trace_data
from .geometry import parse_trace_table
from .plotting import configure_plotting_style
from .transforms import norm_rotate_lines, rotate_shift_lines, shift_lines_pos, strike_to_rad

__all__ = [
    # config
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "PROJECT_ROOT",
    "ensure_io_paths",
    "find_trace_tables",
    "load_config",
    "resolve_config_base_dir",
    "validate_config",
    # data
    "ParsedTraceData",
    "load_trace_data",
    # geometry
    "parse_trace_table",
    # transforms
    "norm_rotate_lines",
    "rotate_shift_lines",
    "shift_lines_pos",
    "strike_to_rad",
    # plotting
    "configure_plotting_style",
]
