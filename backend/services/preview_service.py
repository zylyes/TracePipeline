"""样式预览图生成服务（150 DPI + 缓存）。"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from trace_pipeline.models import RunConfig
from trace_pipeline.pipeline import load_trace_data
from trace_pipeline.plotting.rose_plot import render_rose_plot
from trace_pipeline.plotting.trace_plot import CircleWindowOverlay, ConvexHullOverlay, render_trace_plot
from trace_pipeline.geology.statistics import TraceStatisticsConfig, compute_trace_statistics
from trace_pipeline.geology.transforms import normalize_coordinates
from trace_pipeline.geology.angles import azimuth_to_cartesian_deg, fold_strike_angle
from trace_pipeline.plotting.style import configure_style

logger = logging.getLogger(__name__)

PREVIEW_DIR = Path("output/preview")
PREVIEW_DPI = 150
CACHE_TTL = 300  # 5分钟

# 样式常量映射（与 trace_plot.py / rose_plot.py 对应）
_STYLE_CONSTANTS = {
    "trace_line_color": "trace_plot._TRACE_LINE_COLOR",
    "trace_line_width": "trace_plot._TRACE_LINE_WIDTH",
    "hull_line_color": "trace_plot._HULL_LINE_COLOR",
    "hull_fill_color": "trace_plot._HULL_FILL_COLOR",
    "hull_fill_alpha": "trace_plot._HULL_FILL_ALPHA",
    "circle_window_line_color": "trace_plot._CIRCLE_WINDOW_LINE_COLOR",
    "circle_window_fill_color": "trace_plot._CIRCLE_WINDOW_FILL_COLOR",
    "circle_window_fill_alpha": "trace_plot._CIRCLE_WINDOW_FILL_ALPHA",
    "rose_bar_color": "rose_plot._ROSE_BAR_COLOR",
    "rose_bar_edge": "rose_plot._ROSE_BAR_EDGE",
    "rose_grid_color": "rose_plot._ROSE_GRID_COLOR",
}

# 线程安全锁，保护 matplotlib 全局状态修改
_PREVIEW_LOCK = threading.Lock()


def _hash_style(style: dict[str, Any]) -> str:
    """计算样式配置的哈希值，用于缓存键。"""
    normalized = json.dumps(style, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


class PreviewService:
    """使用样本数据（O76）生成 150 DPI 预览图，支持缓存。"""

    def __init__(self, sample_outcrop: str = "O76") -> None:
        self._sample = sample_outcrop
        self._cache: dict[str, tuple[float, dict[str, str]]] = {}
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, style_config: dict[str, Any]) -> dict[str, Any]:
        style_hash = _hash_style(style_config)
        with _PREVIEW_LOCK:
            if style_hash in self._cache:
                ts, paths = self._cache[style_hash]
                if time.time() - ts < CACHE_TTL:
                    return {"status": "ready", "paths": paths}

        try:
            paths = self._generate_images(style_config, style_hash)
            with _PREVIEW_LOCK:
                self._cache[style_hash] = (time.time(), paths)
            return {"status": "ready", "paths": paths}
        except Exception as exc:
            logger.exception("预览生成失败")
            return {"status": "error", "message": str(exc)}

    def _generate_images(self, style: dict[str, Any], style_hash: str) -> dict[str, str]:
        """临时修改 matplotlib 常量，生成预览图（线程安全）。"""
        import trace_pipeline.plotting.trace_plot as tp
        import trace_pipeline.plotting.rose_plot as rp

        with _PREVIEW_LOCK:
            # 保存原始值
            orig: dict[str, Any] = {}
            for key, path in _STYLE_CONSTANTS.items():
                module_path, attr = path.split(".")
                mod = tp if module_path == "trace_plot" else rp
                orig[key] = getattr(mod, attr)

            try:
                # 应用样式
                for key, val in style.items():
                    if key in _STYLE_CONSTANTS:
                        module_path, attr = _STYLE_CONSTANTS[key].split(".")
                        mod = tp if module_path == "trace_plot" else rp
                        setattr(mod, attr, val)

                # 全局字号
                if "global_font_size" in style:
                    matplotlib.rcParams["font.size"] = float(style["global_font_size"])

                # 加载样本数据
                trace = load_trace_data("input", f"{self._sample}_process", self._sample)
                rotated = normalize_coordinates(trace.endpoints, trace.scanline_azimuth)
                stats_config = TraceStatisticsConfig(
                    window_strategy=style.get("window_strategy", "auto"),
                )
                statistics = compute_trace_statistics(trace, stats_config)

                from trace_pipeline.pipeline import _raw_circle_overlays, _rotated_circle_overlays, _selected_hull_overlays
                raw_circles = _raw_circle_overlays(trace, statistics)
                rot_circles = _rotated_circle_overlays(trace, raw_circles)
                raw_hull, rot_hull = _selected_hull_overlays(trace, statistics)

                from trace_pipeline.geology.statistics import format_statistics_box_lines
                stats_lines = format_statistics_box_lines(statistics)

                raw_path = PREVIEW_DIR / f"preview_{style_hash}_raw.png"
                rose_path = PREVIEW_DIR / f"preview_{style_hash}_rose.png"

                configure_style()

                render_trace_plot(
                    trace.endpoints,
                    "迹线长度图（预览）",
                    str(PREVIEW_DIR),
                    raw_path.name,
                    dpi=PREVIEW_DPI,
                    statistics_lines=stats_lines,
                    circle_windows=raw_circles,
                    hull_overlay=raw_hull,
                    area_source=statistics.outcrop_area_source,
                )

                if trace.joint_strikes.size:
                    render_rose_plot(
                        trace.joint_strikes,
                        "产状玫瑰花瓣图（预览）",
                        str(PREVIEW_DIR),
                        rose_path.name,
                        bin_width=style.get("rose_bin_width", 10.0),
                        dpi=PREVIEW_DPI,
                    )

                return {
                    "raw": str(raw_path.resolve()),
                    "rose": str(rose_path.resolve()) if trace.joint_strikes.size else "",
                }
            finally:
                # 恢复原始值
                for key, val in orig.items():
                    module_path, attr = _STYLE_CONSTANTS[key].split(".")
                    mod = tp if module_path == "trace_plot" else rp
                    setattr(mod, attr, val)
