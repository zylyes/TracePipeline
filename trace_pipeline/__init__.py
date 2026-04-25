"""trace_pipeline — 岩体节理测线坐标计算与绘图工具包。

模块分工:
  config.py      — 配置加载、校验与路径解析
  data_loader.py — Excel 读取与 ParsedTraceData 封装
  geometry.py    — 迹线端点向量化计算
  transforms.py  — 坐标平移与旋转
  excel_export.py— Excel 输出构建与写入
  plotting.py    — 迹线图与玫瑰花瓣图
  pipeline.py    — 单目标全流程编排
"""
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
from .data_loader import ParsedTraceData, load_trace_data, load_trace_table
from .geometry import COL_DIP, COL_R1, COL_R2, COL_R4, COL_R5, COL_R6, COL_R7, parse_trace_table
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
    "load_trace_table",
    # geometry
    "COL_DIP",
    "COL_R1",
    "COL_R2",
    "COL_R4",
    "COL_R5",
    "COL_R6",
    "COL_R7",
    "parse_trace_table",
    # transforms
    "norm_rotate_lines",
    "rotate_shift_lines",
    "shift_lines_pos",
    "strike_to_rad",
    # plotting
    "configure_plotting_style",
]
