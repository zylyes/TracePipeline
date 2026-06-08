"""绘图子包：样式配置、迹线图、玫瑰花瓣图。"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_LAZY_EXPORTS = {
    "CircleWindowOverlay": ("trace_pipeline.plotting.trace_plot", "CircleWindowOverlay"),
    "ConvexHullOverlay": ("trace_pipeline.plotting.trace_plot", "ConvexHullOverlay"),
    "configure_style": ("trace_pipeline.plotting.style", "configure_style"),
    "render_rose_plot": ("trace_pipeline.plotting.rose_plot", "render_rose_plot"),
    "render_trace_plot": ("trace_pipeline.plotting.trace_plot", "render_trace_plot"),
    "segments_to_xy": ("trace_pipeline.plotting.trace_plot", "segments_to_xy"),
}


def __getattr__(name: str) -> Any:
    """按需加载绘图入口，避免导入包时提前加载 pyplot。"""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _LAZY_EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "CircleWindowOverlay",
    "ConvexHullOverlay",
    "configure_style",
    "render_rose_plot",
    "render_trace_plot",
    "segments_to_xy",
]
