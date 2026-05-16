"""统计数据服务。"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from typing import Any

import numpy as np

from trace_pipeline.analysis.models import NodeRecognitionConfig
from trace_pipeline.analysis.nodes import recognize_trace_nodes
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

logger = logging.getLogger(__name__)


class StatsService:
    """读取已处理结果，返回统计指标和覆盖层几何。"""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}
        self._cache_ttl = 300.0  # 5分钟缓存
        logger.info("StatsService 已初始化（带统计缓存）", extra={"stage": "stats_service_init", "cache_ttl": self._cache_ttl})

    # 影响统计结果的关键配置字段子集
    _STAT_KEYS = {
        "window_strategy", "auto_density_threshold", "tangent_window_count",
        "enable_node_recognition", "node_merge_tolerance",
    }

    def _make_key(self, outcrop: str, config: dict[str, Any] | None) -> str:
        # 仅提取影响统计结果的关键字段，避免无关字段（如 is_dev_mode、style）导致缓存失效
        effective_cfg = {k: v for k, v in (config or {}).items() if k in self._STAT_KEYS}
        cfg_str = json.dumps(effective_cfg, sort_keys=True, ensure_ascii=False)
        # 使用稳定哈希替代内置 hash()，避免进程重启后哈希随机化导致缓存失效
        cfg_hash = hashlib.sha256(cfg_str.encode("utf-8")).hexdigest()[:16]
        return f"{outcrop}:{cfg_hash}"

    def get_stats(self, outcrop: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """计算并返回指定露头的统计数据（带缓存）。"""
        start = time.perf_counter()
        key = self._make_key(outcrop, config)
        cached = self._cache.get(key)
        if cached:
            result, ts = cached
            if time.time() - ts < self._cache_ttl:
                logger.debug(
                    "get_stats 命中缓存 [%s]: trace_count=%s",
                    outcrop, result.get("trace_count"),
                    extra={"stage": "stats_cache_hit", "outcrop": outcrop, "trace_count": result.get("trace_count")},
                )
                return result

        cfg = config or {}
        input_dir = cfg.get("input_dir", "input")
        table_stem = f"{outcrop}_process"

        try:
            trace = load_trace_data(input_dir, table_stem, outcrop)
        except Exception as exc:
            logger.warning("加载 %s 失败: %s", outcrop, exc, extra={"stage": "stats_load", "outcrop": outcrop, "error": str(exc)})
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
        raw_circles = build_raw_circle_overlays(trace, statistics)
        rot_circles = build_rotated_circle_overlays(trace, raw_circles)
        raw_hull, rot_hull = build_selected_hull_overlays(trace, statistics)

        def _hull_data(hull):
            if hull is None or hull.vertices.size == 0:
                return []
            return hull.vertices.tolist()

        def _circle_data(circle_list):
            return [
                {"center_x": float(c.center_x), "center_y": float(c.center_y), "radius": float(c.radius)}
                for c in circle_list
            ]

        # 节点识别
        node_config = NodeRecognitionConfig(
            enabled=cfg.get("enable_node_recognition", True),
            merge_tolerance=cfg.get("node_merge_tolerance", 1e-6),
            show_overlay=cfg.get("show_node_overlay", True),
            label_mode=cfg.get("node_label_mode", "type"),
        )
        node_analysis = recognize_trace_nodes(trace.endpoints, node_config)
        raw_nodes = build_node_overlays(node_analysis)
        rot_nodes = build_rotated_node_overlays(node_analysis, trace.endpoints, trace.scanline_azimuth)
        tc = node_analysis.type_counts

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

        def _node_data(node_list):
            return [
                {"x": float(n.x), "y": float(n.y), "node_type": n.node_type, "node_id": n.node_id, "degree": n.degree}
                for n in node_list
            ]

        result = {
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
            "nodes_summary": {
                "node_count": node_analysis.node_count,
                "node_i_count": tc.get("I", 0),
                "node_y_count": tc.get("Y", 0),
                "node_x_count": tc.get("X", 0),
                "intersection_count": node_analysis.intersection_count,
                "degenerate_skipped": node_analysis.degenerate_skipped,
            },
            "nodes": [
                {"node_id": n.node_id, "x": round(n.x, 4), "y": round(n.y, 4), "type": n.type_label,
                 "degree": n.degree, "trace_indices": list(n.trace_indices), "event_count": n.event_count}
                for n in node_analysis.nodes
            ],
            "intersections": [
                {"trace_a": ev.trace_a, "trace_b": ev.trace_b, "x": round(ev.x, 4), "y": round(ev.y, 4),
                 "t": round(ev.t, 4), "u": round(ev.u, 4), "kind": ev.kind}
                for ev in node_analysis.intersections
            ],
            "raw_plot_overlay": {
                "data_x_min": raw_x_min,
                "data_x_max": raw_x_max,
                "data_y_min": raw_y_min,
                "data_y_max": raw_y_max,
                "has_hull": raw_hull is not None and len(raw_hull.vertices) > 0,
                "hull_vertices": _hull_data(raw_hull),
                "has_circles": len(raw_circles) > 0,
                "circles": _circle_data(raw_circles),
                "has_nodes": len(raw_nodes) > 0,
                "nodes": _node_data(raw_nodes),
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
                "has_nodes": len(rot_nodes) > 0,
                "nodes": _node_data(rot_nodes),
            },
        }
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "stats 计算完成 [%s]: trace_count=%d, P10=%.4f, P20=%.4f, P21=%.4f, nodes=%d (%.3f ms)",
            outcrop, trace.count, result["p10"] or 0, result["p20"] or 0, result["p21"] or 0,
            node_analysis.node_count, duration,
            extra={
                "stage": "stats_complete",
                "outcrop": outcrop,
                "trace_count": trace.count,
                "p10": result["p10"],
                "p20": result["p20"],
                "p21": result["p21"],
                "window_strategy": result["window_strategy"],
                "node_count": node_analysis.node_count,
                "node_i_count": tc.get("I", 0),
                "node_y_count": tc.get("Y", 0),
                "node_x_count": tc.get("X", 0),
                "intersection_count": node_analysis.intersection_count,
                "area_source": result["area_source"],
                "duration_ms": round(duration, 3),
            },
        )
        self._cache[key] = (result, time.time())
        return result

    def get_comparison(self, outcrops: list[str], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """返回多露头对比数据（优先走缓存）。"""
        results: list[dict[str, Any]] = []
        missing: list[str] = []
        now = time.time()
        for oc in outcrops:
            key = self._make_key(oc, config)
            cached = self._cache.get(key)
            if cached and (now - cached[1] < self._cache_ttl):
                results.append(cached[0])
            else:
                missing.append(oc)
        # 仅对缺失或已过期的露头重新计算
        for oc in missing:
            stats = self.get_stats(oc, config)
            if "error" not in stats:
                results.append(stats)
        return results

    def invalidate_cache(self, outcrop: str | None = None) -> None:
        """使统计缓存失效。"""
        if outcrop is None:
            count = len(self._cache)
            self._cache.clear()
            logger.debug("stats 缓存已全部清空: %d 条", count, extra={"stage": "stats_cache_invalidate_all", "count": count})
        else:
            keys = [k for k in self._cache if k.startswith(f"{outcrop}:")]
            for k in keys:
                del self._cache[k]
            logger.debug("stats 缓存已失效 [%s]: %d 条", outcrop, len(keys), extra={"stage": "stats_cache_invalidate", "outcrop": outcrop, "count": len(keys)})
