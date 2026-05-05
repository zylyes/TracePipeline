"""trace_pipeline — 岩体节理测线坐标计算与绘图工具包。

目录结构:
  models.py     — 数据模型（TraceData, RunConfig, RunResult）
  config.py     — 配置加载、路径解析、CLI 覆盖
  pipeline.py   — 单目标全流程编排（run_pipeline, load_trace_data）
  reporting.py  — 结果格式化展示
  geology/      — 地质/几何算法（纯函数）
  io/           — Excel 读写 + 文件发现
  plotting/     — 迹线图 + 玫瑰图
  cli/          — 命令行入口
"""
from __future__ import annotations

from .config import (
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    apply_cli_overrides,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
)
from .geology.statistics import (
    CircleWindowDiagnostic,
    TraceStatistics,
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from .io.discovery import find_trace_tables
from .models import RunConfig, RunResult, TraceData
from .pipeline import load_trace_data, run_pipeline
from .plotting.style import configure_style
from .reporting import print_pipeline_results

__all__ = [
    "DEFAULT_CONFIG",
    "DEFAULT_CONFIG_PATH",
    "PROJECT_ROOT",
    "CircleWindowDiagnostic",
    "RunConfig",
    "RunResult",
    "TraceStatistics",
    "TraceStatisticsConfig",
    "TraceData",
    "apply_cli_overrides",
    "configure_style",
    "compute_trace_statistics",
    "find_trace_tables",
    "format_statistics_box_lines",
    "load_config",
    "load_trace_data",
    "print_pipeline_results",
    "resolve_config_base_dir",
    "resolve_io_paths",
    "run_pipeline",
]
