"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .analysis.models import NodeRecognitionConfig
from .analysis.nodes import recognize_trace_nodes
from .geology.angles import fold_strike_angle
from .geology.endpoints import compute_endpoints
from .geology.statistics import (
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from .geology.transforms import normalize_coordinates
from .io.excel_reader import read_trace_excel
from .io.excel_writer import build_result_workbook_sections, write_excel_multi_sheets
from .models import RunConfig, RunResult, TraceData
from .plotting.overlays import (
    build_node_overlays,
    build_raw_circle_overlays,
    build_rotated_circle_overlays,
    build_rotated_node_overlays,
    build_selected_hull_overlays,
)
from .plotting.rose_plot import render_rose_plot
from .plotting.trace_plot import render_trace_plot

logger = logging.getLogger(__name__)

__all__ = ["load_trace_data", "run_pipeline"]

# ── 样式应用/恢复 ─────────────────────────────────────────────

_STYLE_CONSTANTS = {
    "trace_line_color": ("trace_plot", "_TRACE_LINE_COLOR"),
    "trace_line_width": ("trace_plot", "_TRACE_LINE_WIDTH"),
    "hull_line_color": ("trace_plot", "_HULL_LINE_COLOR"),
    "hull_fill_color": ("trace_plot", "_HULL_FILL_COLOR"),
    "hull_fill_alpha": ("trace_plot", "_HULL_FILL_ALPHA"),
    "circle_window_line_color": ("trace_plot", "_CIRCLE_WINDOW_LINE_COLOR"),
    "circle_window_fill_color": ("trace_plot", "_CIRCLE_WINDOW_FILL_COLOR"),
    "circle_window_fill_alpha": ("trace_plot", "_CIRCLE_WINDOW_FILL_ALPHA"),
    "rose_bar_color": ("rose_plot", "_ROSE_BAR_COLOR"),
    "rose_bar_edge": ("rose_plot", "_ROSE_BAR_EDGE"),
    "rose_grid_color": ("rose_plot", "_ROSE_GRID_COLOR"),
}


def _apply_style(style: dict[str, Any]) -> dict[str, Any]:
    """临时应用样式到绘图模块常量，返回原始值用于恢复。"""
    import matplotlib

    import trace_pipeline.plotting.rose_plot as rp
    import trace_pipeline.plotting.trace_plot as tp

    orig: dict[str, Any] = {}
    for key, (mod_name, attr) in _STYLE_CONSTANTS.items():
        mod = tp if mod_name == "trace_plot" else rp
        if hasattr(mod, attr):
            orig[key] = getattr(mod, attr)

    try:
        for key, val in style.items():
            if key in _STYLE_CONSTANTS:
                mod_name, attr = _STYLE_CONSTANTS[key]
                mod = tp if mod_name == "trace_plot" else rp
                setattr(mod, attr, val)
        if "global_font_size" in style:
            matplotlib.rcParams["font.size"] = float(style["global_font_size"])
    except Exception as exc:
        logger.warning("样式应用失败: %s", exc)

    return orig


def _restore_style(orig: dict[str, Any]) -> None:
    """恢复绘图模块常量到原始值。"""
    import trace_pipeline.plotting.rose_plot as rp
    import trace_pipeline.plotting.trace_plot as tp

    for key, val in orig.items():
        mod_name, attr = _STYLE_CONSTANTS[key]
        mod = tp if mod_name == "trace_plot" else rp
        setattr(mod, attr, val)


def load_trace_data(input_dir: str, table_stem: str, outcrop: str) -> TraceData:
    """读取迹线 Excel 表并解析为 TraceData。"""
    logger.info("加载迹线数据: %s/%s", input_dir, table_stem)
    df = read_trace_excel(input_dir, table_stem, outcrop)

    result = compute_endpoints(df)
    trace = TraceData(
        scanline_azimuth=result.azimuth,
        count=result.count,
        endpoints=result.endpoints,
        joint_strikes=result.joint_strikes,
        segment_lengths=result.segment_lengths,
        scanline_positions=result.scanline_positions,
        measured_scanline_length=result.measured_scanline_length,
        measured_outcrop_area=result.measured_outcrop_area,
    )
    logger.info(
        "解析完成: %d 条迹线, 走向 %.1f°, 平均端点距离 %.2f",
        result.count, result.azimuth, trace.mean_length,
    )
    return trace


def run_pipeline(cfg: RunConfig) -> RunResult:
    """处理单个迹线表：加载 → 变换 → 导出 Excel → 绘图。

    Args:
        cfg: 已校验的运行参数。

    Returns:
        RunResult — 不可变结果对象，.status 为 "success" 或 "error"。
    """
    try:
        logger.info("开始处理: %s", cfg.outcrop)

        # ---- 1. 加载数据 ----
        trace = load_trace_data(cfg.input_dir, cfg.table_stem, cfg.outcrop)
        logger.info(
            "数据加载完成: %s — %d 条迹线, 走向 %.1f°",
            cfg.outcrop, trace.count, trace.scanline_azimuth,
        )

        # ---- 2. 坐标变换 ----
        rotated = normalize_coordinates(trace.endpoints, trace.scanline_azimuth)
        # 坐标按测线走向旋转后，画布中的正北方向也要同步显示该偏移。
        rotated_north_angle = 90.0 + float(np.degrees(fold_strike_angle(trace.scanline_azimuth)))
        statistics_config = TraceStatisticsConfig(
            window_strategy=cfg.window_strategy,
            auto_density_threshold=cfg.auto_density_threshold,
            tangent_window_count=cfg.tangent_window_count,
        )
        statistics = compute_trace_statistics(trace, statistics_config)
        statistics_lines = format_statistics_box_lines(statistics)
        raw_circle_windows = build_raw_circle_overlays(trace, statistics)
        rotated_circle_windows = build_rotated_circle_overlays(trace, raw_circle_windows)

        # 即时终端告警
        if statistics.window_validation_warning:
            print(f"\n[{cfg.outcrop}] 警告: {statistics.window_validation_warning}")

        raw_hull_overlay, rotated_hull_overlay = build_selected_hull_overlays(trace, statistics)

        # ---- 3. 节点识别 ----
        node_analysis = None
        raw_node_overlays = ()
        rotated_node_overlays = ()
        if cfg.enable_node_recognition:
            node_config = NodeRecognitionConfig(
                enabled=True,
                merge_tolerance=cfg.node_merge_tolerance,
                show_overlay=cfg.show_node_overlay,
                label_mode=cfg.node_label_mode,
            )
            node_analysis = recognize_trace_nodes(trace.endpoints, node_config)
            raw_node_overlays = build_node_overlays(node_analysis)
            rotated_node_overlays = build_rotated_node_overlays(
                node_analysis, trace.endpoints, trace.scanline_azimuth
            )
            logger.info(
                "节点识别完成: %s — %d 个节点, %d 个交点事件",
                cfg.outcrop, node_analysis.node_count, node_analysis.intersection_count,
            )

        # ---- 4. 导出 Excel ----
        output_dir = Path(cfg.output_dir)
        excel_path = output_dir / f"{cfg.output_prefix}_traces.xlsx"
        sections = build_result_workbook_sections(
            trace, rotated, statistics=statistics, node_analysis=node_analysis
        )
        write_excel_multi_sheets(str(excel_path), sections)
        logger.info("Excel 导出至: %s", excel_path)

        # ---- 5. 绘制图片 ----
        style_orig = _apply_style(cfg.style)
        try:
            raw_plot = render_trace_plot(
                trace.endpoints,
                "迹线长度图",
                str(output_dir),
                f"{cfg.outcrop}_raw(n={trace.count}).png",
                dpi=cfg.trace_dpi,
                statistics_lines=statistics_lines,
                circle_windows=raw_circle_windows,
                hull_overlay=raw_hull_overlay,
                area_source=statistics.outcrop_area_source,
                node_overlays=raw_node_overlays if cfg.show_node_overlay else None,
                node_label_mode=cfg.node_label_mode,
            )
            rot_plot = render_trace_plot(
                rotated,
                f"迹线长度图\n标尺（走向={trace.scanline_azimuth:.1f}°）",
                str(output_dir),
                f"{cfg.outcrop}_rotated(strike={trace.scanline_azimuth}).png",
                dpi=cfg.rotated_trace_dpi,
                north_angle_deg=rotated_north_angle,
                statistics_lines=statistics_lines,
                circle_windows=rotated_circle_windows,
                hull_overlay=rotated_hull_overlay,
                area_source=statistics.outcrop_area_source,
                node_overlays=rotated_node_overlays if cfg.show_node_overlay else None,
                node_label_mode=cfg.node_label_mode,
            )

            rose_plot = ""
            if cfg.export_rose_plot:
                rose_plot = render_rose_plot(
                    trace.joint_strikes,
                    f"产状玫瑰花瓣图（数量={trace.count}，分箱={cfg.rose_bin_width}°）",
                    str(output_dir),
                    f"{cfg.outcrop}_rose(bin={cfg.rose_bin_width}).png",
                    bin_width=cfg.rose_bin_width,
                    dpi=cfg.rose_dpi,
                )
                logger.info("玫瑰图导出至: %s", rose_plot)
        finally:
            _restore_style(style_orig)

        logger.info("处理完成: %s", cfg.outcrop)
        node_summary = {
            "node_count": 0,
            "node_i_count": 0,
            "node_y_count": 0,
            "node_x_count": 0,
            "node_overlap_count": 0,
            "node_multi_count": 0,
            "intersection_count": 0,
            "endpoint_node_count": 0,
        }
        if node_analysis is not None:
            tc = node_analysis.type_counts
            node_summary = {
                "node_count": node_analysis.node_count,
                "node_i_count": tc.get("I", 0),
                "node_y_count": tc.get("Y", 0),
                "node_x_count": tc.get("X", 0),
                "node_overlap_count": tc.get("overlap", 0),
                "node_multi_count": tc.get("multi", 0),
                "intersection_count": node_analysis.intersection_count,
                "endpoint_node_count": sum(1 for n in node_analysis.nodes if n.is_endpoint),
            }
        return RunResult.success(
            table_stem=cfg.table_stem,
            trace_count=trace.count,
            mean_length=statistics.mean_trace_length,
            scanline_azimuth=trace.scanline_azimuth,
            excel_path=str(excel_path),
            raw_plot_path=raw_plot,
            rotated_plot_path=rot_plot,
            rose_plot_path=rose_plot,
            window_strategy=statistics.window_strategy,
            area_source=statistics.outcrop_area_source,
            **node_summary,
        )

    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("处理 [%s] 失败 (%s): %s", cfg.outcrop, type(exc).__name__, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except Exception as exc:
        logger.error("处理 [%s] 时发生未预期错误: %s", cfg.outcrop, exc, exc_info=True)
        return RunResult.failure(cfg.table_stem, f"{type(exc).__name__}: {exc}")
