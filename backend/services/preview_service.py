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

from trace_pipeline.analysis.models import NodeRecognitionConfig
from trace_pipeline.analysis.nodes import recognize_trace_nodes
from trace_pipeline.geology.angles import fold_strike_angle
from trace_pipeline.geology.statistics import TraceStatisticsConfig, compute_trace_statistics
from trace_pipeline.geology.transforms import normalize_coordinates
from trace_pipeline.pipeline import load_trace_data
from trace_pipeline.plotting.overlays import (
    build_node_overlays,
    build_raw_circle_overlays,
    build_rotated_circle_overlays,
    build_rotated_node_overlays,
    build_selected_hull_overlays,
)
from trace_pipeline.plotting.rose_plot import render_rose_plot
from trace_pipeline.plotting.style import configure_style
from trace_pipeline.plotting.trace_plot import render_trace_plot

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


def _hash_config(config: dict[str, Any]) -> str:
    """计算样式配置的哈希值，用于缓存键。"""
    style = config.get("style", {})
    normalized = json.dumps(style, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


class PreviewService:
    """使用样本数据（O76）生成 150 DPI 预览图，支持缓存。"""

    def __init__(self, sample_outcrop: str = "O76") -> None:
        self._sample = sample_outcrop
        self._cache: dict[str, tuple[float, dict[str, str]]] = {}
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, config: dict[str, Any]) -> dict[str, Any]:
        style_hash = _hash_config(config)
        with _PREVIEW_LOCK:
            if style_hash in self._cache:
                ts, paths = self._cache[style_hash]
                if time.time() - ts < CACHE_TTL:
                    return {"status": "ready", "paths": paths, "images": self._to_images(paths)}

        try:
            paths = self._generate_images(config, style_hash)
            with _PREVIEW_LOCK:
                self._cache[style_hash] = (time.time(), paths)
            return {"status": "ready", "paths": paths, "images": self._to_images(paths)}
        except Exception as exc:
            logger.exception("预览生成失败")
            return {"status": "error", "message": str(exc)}

    def _to_images(self, paths: dict[str, str]) -> list[dict[str, str]]:
        """将路径字典转为结构化 images 数组。"""
        images = []
        for key in ("raw", "rotated", "rose"):
            path = paths.get(key, "")
            if path:
                label_map = {
                    "raw": "原始迹线图",
                    "rotated": "旋转迹线图",
                    "rose": "走向玫瑰图",
                }
                images.append({"key": key, "label": label_map.get(key, key), "path": path})
        return images

    def _generate_images(self, config: dict[str, Any], style_hash: str) -> dict[str, str]:
        """临时修改 matplotlib 常量，生成预览图（线程安全）。"""
        import trace_pipeline.plotting.rose_plot as rp
        import trace_pipeline.plotting.trace_plot as tp

        style = config.get("style", {})

        with _PREVIEW_LOCK:
            # 保存原始值
            orig: dict[str, Any] = {}
            for key, path in _STYLE_CONSTANTS.items():
                module_path, attr = path.split(".")
                mod = tp if module_path == "trace_plot" else rp
                orig[key] = getattr(mod, attr)

            try:
                configure_style()

                # 应用样式
                for key, val in style.items():
                    if key in _STYLE_CONSTANTS:
                        module_path, attr = _STYLE_CONSTANTS[key].split(".")
                        mod = tp if module_path == "trace_plot" else rp
                        setattr(mod, attr, val)

                # 全局字号（在 configure_style 之后应用，确保不被覆盖）
                if "global_font_size" in style:
                    matplotlib.rcParams["font.size"] = float(style["global_font_size"])

                # 加载样本数据
                trace = load_trace_data("input", f"{self._sample}_process", self._sample)
                stats_config = TraceStatisticsConfig(
                    window_strategy=config.get("window_strategy", "auto"),
                    auto_density_threshold=config.get("auto_density_threshold", 5.0),
                    tangent_window_count=config.get("tangent_window_count", 3),
                )
                statistics = compute_trace_statistics(trace, stats_config)

                raw_circles = build_raw_circle_overlays(trace, statistics)
                rotated_circles = build_rotated_circle_overlays(trace, raw_circles)
                raw_hull, rot_hull = build_selected_hull_overlays(trace, statistics)

                from trace_pipeline.geology.statistics import format_statistics_box_lines
                stats_lines = format_statistics_box_lines(statistics)

                # 节点识别
                raw_node_overlays = ()
                rotated_node_overlays = ()
                if config.get("enable_node_recognition", True):
                    node_config = NodeRecognitionConfig(
                        enabled=True,
                        merge_tolerance=config.get("node_merge_tolerance", 1e-6),
                        show_overlay=config.get("show_node_overlay", True),
                        label_mode=config.get("node_label_mode", "type"),
                    )
                    node_analysis = recognize_trace_nodes(trace.endpoints, node_config)
                    raw_node_overlays = build_node_overlays(node_analysis)
                    rotated_node_overlays = build_rotated_node_overlays(
                        node_analysis, trace.endpoints, trace.scanline_azimuth
                    )

                raw_path = PREVIEW_DIR / f"preview_{style_hash}_raw.png"
                rotated_path = PREVIEW_DIR / f"preview_{style_hash}_rotated.png"
                rose_path = PREVIEW_DIR / f"preview_{style_hash}_rose.png"

                # 旋转坐标与正北角度（与 pipeline.py 一致）
                rotated = normalize_coordinates(trace.endpoints, trace.scanline_azimuth)
                rotated_north_angle = 90.0 + float(np.degrees(fold_strike_angle(trace.scanline_azimuth)))

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
                    node_overlays=raw_node_overlays if config.get("show_node_overlay", True) else None,
                    node_label_mode=config.get("node_label_mode", "type"),
                )

                render_trace_plot(
                    rotated,
                    f"迹线长度图\n标尺（走向={trace.scanline_azimuth:.1f}°）（预览）",
                    str(PREVIEW_DIR),
                    rotated_path.name,
                    dpi=PREVIEW_DPI,
                    north_angle_deg=rotated_north_angle,
                    statistics_lines=stats_lines,
                    circle_windows=rotated_circles,
                    hull_overlay=rot_hull,
                    area_source=statistics.outcrop_area_source,
                    node_overlays=rotated_node_overlays if config.get("show_node_overlay", True) else None,
                    node_label_mode=config.get("node_label_mode", "type"),
                )

                rose_plot_path = ""
                if trace.joint_strikes.size and config.get("export_rose_plot", True):
                    rose_plot_path = str(rose_path.resolve())
                    render_rose_plot(
                        trace.joint_strikes,
                        f"产状玫瑰花瓣图（预览）",
                        str(PREVIEW_DIR),
                        rose_path.name,
                        bin_width=config.get("rose_bin_width", 10.0),
                        dpi=PREVIEW_DPI,
                    )

                return {
                    "raw": str(raw_path.resolve()),
                    "rotated": str(rotated_path.resolve()),
                    "rose": rose_plot_path,
                }
            finally:
                # 恢复原始值
                for key, val in orig.items():
                    module_path, attr = _STYLE_CONSTANTS[key].split(".")
                    mod = tp if module_path == "trace_plot" else rp
                    setattr(mod, attr, val)
