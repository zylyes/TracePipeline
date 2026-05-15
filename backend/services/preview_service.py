"""样式预览图生成服务（150 DPI + 缓存）。"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
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
from trace_pipeline.models import TraceData
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

if getattr(sys, 'frozen', False):
    _PREVIEW_BASE = Path(sys.executable).parent
else:
    _PREVIEW_BASE = Path(__file__).resolve().parent.parent.parent
PREVIEW_DIR = _PREVIEW_BASE / "output" / "preview"
PREVIEW_DPI = 150
CACHE_TTL = 300  # 5分钟

# 线程安全锁，保护缓存和预览生成串行化
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

    @staticmethod
    def _create_demo_trace() -> TraceData:
        """返回内置 demo 迹线数据，不依赖 input 文件夹。"""
        endpoints = np.array([
            [0.0, 0.0, 10.0, 5.0],
            [2.0, 8.0, 12.0, 2.0],
            [5.0, 0.0, 5.0, 10.0],
            [0.0, 5.0, 10.0, 5.0],
            [8.0, 0.0, 8.0, 8.0],
            [3.0, 3.0, 10.0, 8.0],
            [1.0, 7.0, 9.0, 1.0],
            [6.0, 2.0, 6.0, 9.0],
        ], dtype=float)
        joint_strikes = np.array([63.43, 120.96, 0.0, 90.0, 0.0, 54.46, 126.87, 0.0])
        segment_lengths = np.array([11.18, 11.66, 10.0, 10.0, 8.0, 8.60, 10.0, 7.0])
        scanline_positions = np.array([0.0, 2.0, 5.0, 0.0, 8.0, 3.0, 1.0, 6.0])
        return TraceData(
            scanline_azimuth=298.0,
            count=8,
            endpoints=endpoints,
            joint_strikes=joint_strikes,
            segment_lengths=segment_lengths,
            scanline_positions=scanline_positions,
        )

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
        """使用共享样式覆盖上下文管理器生成预览图（线程安全）。"""
        from trace_pipeline.plotting.style import apply_style_overrides

        style = config.get("style", {})
        configure_style()

        with _PREVIEW_LOCK:
            with apply_style_overrides(style):
                # 使用内置 demo 数据，不依赖 input 文件夹
                trace = self._create_demo_trace()
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

                # 节点识别（预览始终启用，不受设置影响）
                node_config = NodeRecognitionConfig(
                    enabled=True,
                    merge_tolerance=config.get("node_merge_tolerance", 1e-6),
                    show_overlay=True,
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
                    node_overlays=raw_node_overlays,
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
                    node_overlays=rotated_node_overlays,
                    node_label_mode=config.get("node_label_mode", "type"),
                )

                rose_plot_path = ""
                if trace.joint_strikes.size:
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
