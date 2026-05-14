"""统计数据服务。"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np

from trace_pipeline.models import RunConfig
from trace_pipeline.pipeline import load_trace_data, _raw_circle_overlays, _rotated_circle_overlays, _selected_hull_overlays
from trace_pipeline.geology.statistics import TraceStatisticsConfig, compute_trace_statistics
from trace_pipeline.geology.transforms import normalize_coordinates

logger = logging.getLogger(__name__)


class StatsService:
    """读取已处理结果，返回统计指标和覆盖层几何。"""

    def get_stats(self, outcrop: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """计算并返回指定露头的统计数据。"""
        cfg = config or {}
        input_dir = cfg.get("input_dir", "input")
        table_stem = f"{outcrop}_process"

        try:
            trace = load_trace_data(input_dir, table_stem, outcrop)
        except Exception as exc:
            logger.warning("加载 %s 失败: %s", outcrop, exc)
            return {"error": str(exc)}

        stats_config = TraceStatisticsConfig(
            window_strategy=cfg.get("window_strategy", "auto"),
            auto_density_threshold=cfg.get("auto_density_threshold", 5.0),
            tangent_window_count=cfg.get("tangent_window_count", 3),
        )
        statistics = compute_trace_statistics(trace, stats_config)

        # 构建直方图数据
        lengths = trace.lengths
        hist, edges = np.histogram(lengths, bins=10) if lengths.size else (np.array([]), np.array([]))

        # 圆窗几何
        circles = []
        for diag in statistics.diagnostics:
            if diag.valid and diag.radius > 0:
                circles.append({
                    "center_x": diag.center_x,
                    "center_y": diag.center_y,
                    "radius": diag.radius,
                })

        # 覆盖层几何（用于前端 Canvas 叠加）
        raw_circles = _raw_circle_overlays(trace, statistics)
        rot_circles = _rotated_circle_overlays(trace, raw_circles)
        raw_hull, rot_hull = _selected_hull_overlays(trace, statistics)

        def _hull_data(hull):
            if hull is None or hull.vertices.size == 0:
                return []
            return hull.vertices.tolist()

        def _circle_data(circle_list):
            return [
                {"center_x": float(c.center_x), "center_y": float(c.center_y), "radius": float(c.radius)}
                for c in circle_list
            ]

        # 计算数据边界（用于前端坐标映射）
        endpoints = trace.endpoints
        raw_xs = endpoints[:, [0, 2]].ravel()
        raw_ys = endpoints[:, [1, 3]].ravel()
        raw_x_min, raw_x_max = float(raw_xs.min()), float(raw_xs.max())
        raw_y_min, raw_y_max = float(raw_ys.min()), float(raw_ys.max())

        rotated = normalize_coordinates(endpoints, trace.scanline_azimuth)
        rot_xs = rotated[:, [0, 2]].ravel()
        rot_ys = rotated[:, [1, 3]].ravel()
        rot_x_min, rot_x_max = float(rot_xs.min()), float(rot_xs.max())
        rot_y_min, rot_y_max = float(rot_ys.min()), float(rot_ys.max())

        return {
            "outcrop": outcrop,
            "scanline_azimuth": round(trace.scanline_azimuth, 2),
            "trace_count": trace.count,
            "mean_trace_length": round(statistics.mean_trace_length, 4) if math.isfinite(statistics.mean_trace_length) else None,
            "p10": round(statistics.p10, 4) if math.isfinite(statistics.p10) else None,
            "p20": round(statistics.p20, 4) if math.isfinite(statistics.p20) else None,
            "p21": round(statistics.p21, 4) if math.isfinite(statistics.p21) else None,
            "type_i": statistics.type_i_count,
            "type_ii": statistics.type_ii_count,
            "type_iii": statistics.type_iii_count,
            "scanline_length": round(statistics.scanline_length, 4) if math.isfinite(statistics.scanline_length) else None,
            "outcrop_area": round(statistics.outcrop_area, 4) if math.isfinite(statistics.outcrop_area) else None,
            "area_source": statistics.outcrop_area_source,
            "window_strategy": statistics.window_strategy,
            "histogram": {
                "bins": hist.tolist(),
                "edges": edges.tolist(),
            },
            "strikes": trace.joint_strikes.tolist(),
            "circles": circles,
            "warning": statistics.window_validation_warning,
            "raw_plot_overlay": {
                "data_x_min": raw_x_min,
                "data_x_max": raw_x_max,
                "data_y_min": raw_y_min,
                "data_y_max": raw_y_max,
                "has_hull": raw_hull is not None and len(raw_hull.vertices) > 0,
                "hull_vertices": _hull_data(raw_hull),
                "has_circles": len(raw_circles) > 0,
                "circles": _circle_data(raw_circles),
            },
            "rotated_plot_overlay": {
                "data_x_min": rot_x_min,
                "data_x_max": rot_x_max,
                "data_y_min": rot_y_min,
                "data_y_max": rot_y_max,
                "has_hull": rot_hull is not None and len(rot_hull.vertices) > 0,
                "hull_vertices": _hull_data(rot_hull),
                "has_circles": len(rot_circles) > 0,
                "circles": _circle_data(rot_circles),
            },
        }

    def get_comparison(self, outcrops: list[str], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """返回多露头对比数据。"""
        results = []
        for oc in outcrops:
            stats = self.get_stats(oc, config)
            if "error" in stats:
                continue
            results.append(stats)
        return results
