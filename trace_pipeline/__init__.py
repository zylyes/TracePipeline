"""trace_pipeline — 岩体节理测线坐标计算与绘图工具包。

模块分工:
  types.py      — TraceData, RunConfig, RunResult 数据模型与校验
  config.py     — 配置加载、路径解析、CLI 覆盖合并
  angles.py     — 地质角度转换（倾向⇄走向、折叠、半平面、半圆）
  geometry.py   — 迹线端点坐标的向量化计算
  transforms.py — 坐标平移、旋转与线段→绘图序列转换
  io.py         — Excel 读取、结果写入与文件发现
  plotting.py   — 迹线图与玫瑰花瓣图绘制
  report.py     — 结果格式化展示与汇总报告
  pipeline.py   — 单目标全流程编排
"""
from __future__ import annotations

# ---- 数据模型 ----
from .types import RunConfig, RunResult, TraceData

# ---- 配置 ----
from .config import (
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    apply_cli_overrides,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
)

# ---- 角度工具 ----
from .angles import (
    dip_to_strike,
    fold_strike_angle,
    fold_strikes_to_semicircle,
    fold_to_halfplane,
)

# ---- 端点计算 ----
from .geometry import compute_endpoints

# ---- 坐标变换 ----
from .transforms import (
    normalize_coordinates,
    rotate_and_shift,
    segments_to_xy,
    shift_to_positive,
)

# ---- Excel I/O 与文件发现 ----
from .io import (
    build_excel_sections,
    find_trace_tables,
    parse_trace_file,
    read_trace_excel,
    write_excel_sections,
)

# ---- 绘图 ----
from .plotting import (
    configure_style,
    render_rose_plot,
    render_trace_plot,
)

# ---- 结果展示 ----
from .report import (
    format_result_detail,
    format_results_table,
    format_summary,
    print_pipeline_results,
)

# ---- 流水线 ----
from .pipeline import run_pipeline


__all__ = [
    # 数据模型
    "TraceData", "RunConfig", "RunResult",
    # 配置
    "DEFAULT_CONFIG", "DEFAULT_CONFIG_PATH", "PROJECT_ROOT",
    "apply_cli_overrides", "load_config",
    "resolve_config_base_dir", "resolve_io_paths",
    # 角度
    "dip_to_strike", "fold_strike_angle",
    "fold_strikes_to_semicircle", "fold_to_halfplane",
    # 几何计算
    "compute_endpoints",
    # 坐标变换
    "normalize_coordinates", "rotate_and_shift",
    "segments_to_xy", "shift_to_positive",
    # Excel I/O 与文件发现
    "build_excel_sections", "find_trace_tables",
    "parse_trace_file", "read_trace_excel", "write_excel_sections",
    # 绘图
    "configure_style", "render_rose_plot", "render_trace_plot",
    # 结果展示
    "format_result_detail", "format_results_table",
    "format_summary", "print_pipeline_results",
    # 流水线
    "run_pipeline",
]