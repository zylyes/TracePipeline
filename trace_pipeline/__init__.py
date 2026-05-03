"""trace_pipeline — 岩体节理测线坐标计算与绘图工具包。

模块分工:
  config.py       — 配置加载、校验、路径解析与文件发现
  data_loader.py  — Excel 读取与 ParsedTraceData 封装
  geometry.py     — 迹线端点向量化计算 (复数)
  transforms.py   — 坐标平移与走向旋转
  excel_export.py — Excel 四区输出
  plotting.py     — 迹线图与玫瑰花瓣图
  pipeline.py     — 单目标全流程编排
"""
from __future__ import annotations

from .config import (
    CONFIG_PATH,
    DEFAULT_CONFIG,
    PROJECT_ROOT,
    find_trace_tables,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
    validate_config,
    validate_rose_bin_width,
    validate_rose_dpi,
)
from .data_loader import ParsedTraceData, load_trace_data, load_trace_table
from .geometry import (
    COL_DIP,
    COL_LEFT_LEN1,
    COL_LEFT_LEN2,
    COL_RIGHT_LEN1,
    COL_RIGHT_LEN2,
    COL_SHIFT_ALONG,
    COL_SHIFT_ACROSS,
    dip_to_strike_vec,
    parse_trace_table,
)
from .plotting import configure_plotting_style, lines_to_plot_xy
from .transforms import (
    norm_rotate_lines,
    rotate_shift_lines,
    shift_to_positive,
    strike_to_rad,
)

__all__ = [
    # config
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "PROJECT_ROOT",
    "find_trace_tables",
    "load_config",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "validate_config",
    "validate_rose_bin_width",
    "validate_rose_dpi",
    # data_loader
    "ParsedTraceData",
    "load_trace_data",
    "load_trace_table",
    # geometry
    "COL_DIP",
    "COL_LEFT_LEN1",
    "COL_LEFT_LEN2",
    "COL_RIGHT_LEN1",
    "COL_RIGHT_LEN2",
    "COL_SHIFT_ALONG",
    "COL_SHIFT_ACROSS",
    "dip_to_strike_vec",
    "parse_trace_table",
    # transforms
    "norm_rotate_lines",
    "rotate_shift_lines",
    "shift_to_positive",
    "strike_to_rad",
    # plotting
    "configure_plotting_style",
    "lines_to_plot_xy",
]
