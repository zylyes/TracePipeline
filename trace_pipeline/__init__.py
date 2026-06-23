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

from importlib import import_module
from typing import Any

__version__ = "4.5.5"

from .config import (
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    PROJECT_ROOT,
    apply_cli_overrides,
    load_config,
    resolve_config_base_dir,
    resolve_io_paths,
)

_LAZY_EXPORTS = {
    "CircleWindowDiagnostic": ("trace_pipeline.geology.statistics", "CircleWindowDiagnostic"),
    "TraceStatistics": ("trace_pipeline.geology.statistics", "TraceStatistics"),
    "TraceStatisticsConfig": ("trace_pipeline.geology.statistics", "TraceStatisticsConfig"),
    "RunConfig": ("trace_pipeline.models", "RunConfig"),
    "RunResult": ("trace_pipeline.models", "RunResult"),
    "TraceData": ("trace_pipeline.models", "TraceData"),
    "compute_trace_statistics": ("trace_pipeline.geology.statistics", "compute_trace_statistics"),
    "configure_style": ("trace_pipeline.plotting.style", "configure_style"),
    "find_trace_tables": ("trace_pipeline.io.discovery", "find_trace_tables"),
    "format_statistics_box_lines": (
        "trace_pipeline.geology.statistics",
        "format_statistics_box_lines",
    ),
    "load_trace_data": ("trace_pipeline.pipeline", "load_trace_data"),
    "print_pipeline_results": ("trace_pipeline.reporting", "print_pipeline_results"),
    "run_pipeline": ("trace_pipeline.pipeline", "run_pipeline"),
}


def __getattr__(name: str) -> Any:
    """按需加载会触发绘图依赖的公开入口。"""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


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
