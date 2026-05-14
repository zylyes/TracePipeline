"""统计数据服务。"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np

from trace_pipeline.models import RunConfig
from trace_pipeline.pipeline import load_trace_data
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
