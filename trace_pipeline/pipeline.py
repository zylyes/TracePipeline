"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
"""
from __future__ import annotations

import logging
import time
import uuid
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
from .logging import LogContext, get_request_id
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

def load_trace_data(input_dir: str, table_stem: str, outcrop: str) -> TraceData:
    """读取迹线 Excel 表并解析为 TraceData。"""
    start = time.perf_counter()
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
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "解析完成: %d 条迹线, 走向 %.1f°, 平均端点距离 %.2f (%.3f ms)",
        result.count, result.azimuth, trace.mean_length, duration_ms,
        extra={"stage": "load", "trace_count": result.count, "duration_ms": round(duration_ms, 3)},
    )
    return trace


def run_pipeline(cfg: RunConfig) -> RunResult:
    """处理单个迹线表：加载 → 变换 → 导出 Excel → 绘图。

    Args:
        cfg: 已校验的运行参数。

    Returns:
        RunResult — 不可变结果对象，.status 为 "success" 或 "error"。
    """
    # 子进程安全：若由 ProcessPoolExecutor 调用，需独立初始化日志并重置 matplotlib 后端
    from multiprocessing import current_process

    if current_process().name != "MainProcess":
        # 强制子进程使用非交互式后端，防止继承父进程 Tkinter/Qt 状态导致崩溃
        from trace_pipeline.utils.mpl_init import force_noninteractive_backend
        force_noninteractive_backend()
        from .logging import setup_worker_logging
        setup_worker_logging()

    pipeline_start = time.perf_counter()
    with LogContext(request_id=f"pipeline-{cfg.outcrop}-{int(pipeline_start * 1000)}-{uuid.uuid4().hex[:6]}"):
        logger.info(
            "开始处理: %s", cfg.outcrop,
            extra={"stage": "pipeline_start", "config": cfg.__dict__},
        )
        try:
            # ---- 1. 加载数据 ----
            t0 = time.perf_counter()
            trace = load_trace_data(cfg.input_dir, cfg.table_stem, cfg.outcrop)
            logger.info(
                "数据加载完成: %s — %d 条迹线, 走向 %.1f° (%.3f ms)",
                cfg.outcrop, trace.count, trace.scanline_azimuth,
                (time.perf_counter() - t0) * 1000,
                extra={"stage": "load", "trace_count": trace.count},
            )

            # ---- 2. 坐标变换 ----
            t0 = time.perf_counter()
            logger.debug("  2.1 归一化坐标: %s", cfg.outcrop, extra={"stage": "transform_substep", "substep": "normalize"})
            rotated = normalize_coordinates(trace.endpoints, trace.scanline_azimuth)
            rotated_north_angle = 90.0 + float(np.degrees(fold_strike_angle(trace.scanline_azimuth)))
            statistics_config = TraceStatisticsConfig(
                window_strategy=cfg.window_strategy,
                auto_density_threshold=cfg.auto_density_threshold,
                tangent_window_count=cfg.tangent_window_count,
                min_intersections=cfg.min_intersections,
            )
            logger.debug("  2.2 计算统计量: %s", cfg.outcrop, extra={"stage": "transform_substep", "substep": "statistics"})
            statistics = compute_trace_statistics(trace, statistics_config)
            statistics_lines = format_statistics_box_lines(statistics)
            logger.debug("  2.3 构建圆窗覆盖层: %s", cfg.outcrop, extra={"stage": "transform_substep", "substep": "circles"})
            raw_circle_windows = build_raw_circle_overlays(trace, statistics)
            rotated_circle_windows = build_rotated_circle_overlays(trace, raw_circle_windows)

            if statistics.window_validation_warning:
                logger.warning(
                    "[%s] 窗口验证警告: %s", cfg.outcrop, statistics.window_validation_warning,
                    extra={"stage": "statistics", "outcrop": cfg.outcrop},
                )

            logger.debug("  2.4 构建凸包覆盖层: %s", cfg.outcrop, extra={"stage": "transform_substep", "substep": "hull"})
            raw_hull_overlay, rotated_hull_overlay = build_selected_hull_overlays(trace, statistics)
            transform_duration = (time.perf_counter() - t0) * 1000
            logger.info(
                "坐标变换与统计完成: %s (%.3f ms) — P10=%.4f, P20=%.4f, P21=%.4f, 窗口=%s",
                cfg.outcrop, transform_duration,
                statistics.p10, statistics.p20, statistics.p21, statistics.window_strategy,
                extra={
                    "stage": "transform",
                    "outcrop": cfg.outcrop,
                    "p10": round(statistics.p10, 4),
                    "p20": round(statistics.p20, 4),
                    "p21": round(statistics.p21, 4),
                    "window_strategy": statistics.window_strategy,
                    "mean_trace_length": round(statistics.mean_trace_length, 4),
                    "circle_count": len(raw_circle_windows),
                    "has_hull": raw_hull_overlay is not None,
                    "duration_ms": round(transform_duration, 3),
                },
            )

            # ---- 3. 节点识别 ----
            t0 = time.perf_counter()
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
                    "节点识别完成: %s — %d 个节点, %d 个交点事件 (%.3f ms)",
                    cfg.outcrop, node_analysis.node_count, node_analysis.intersection_count,
                    (time.perf_counter() - t0) * 1000,
                    extra={
                        "stage": "node_recognition",
                        "node_count": node_analysis.node_count,
                        "intersection_count": node_analysis.intersection_count,
                    },
                )

            # ---- 4. 导出 Excel ----
            t0 = time.perf_counter()
            output_dir = Path(cfg.output_dir)
            excel_path = output_dir / f"{cfg.output_prefix}_traces.xlsx"
            sections = build_result_workbook_sections(
                trace, rotated, statistics=statistics, node_analysis=node_analysis
            )
            write_excel_multi_sheets(str(excel_path), sections)
            logger.info(
                "Excel 导出至: %s (%.3f ms)", excel_path, (time.perf_counter() - t0) * 1000,
                extra={"stage": "export_excel", "excel_path": str(excel_path)},
            )

            # ---- 5. 绘制图片 ----
            t0 = time.perf_counter()
            from trace_pipeline.plotting.style import apply_style_overrides

            with apply_style_overrides(cfg.style):
                logger.debug("  5.1 绘制原始迹线图: %s (dpi=%d)", cfg.outcrop, cfg.trace_dpi, extra={"stage": "plot_substep", "substep": "raw"})
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
                    style=cfg.style,
                )
                logger.debug("  5.2 绘制旋转迹线图: %s (dpi=%d)", cfg.outcrop, cfg.rotated_trace_dpi, extra={"stage": "plot_substep", "substep": "rotated"})

                rot_plot = render_trace_plot(
                    rotated,
                    f"迹线长度图\n标尺（走向={trace.scanline_azimuth:.1f}°）",
                    str(output_dir),
                    f"{cfg.outcrop}_rotated(strike={trace.scanline_azimuth:.1f}).png",
                    dpi=cfg.rotated_trace_dpi,
                    north_angle_deg=rotated_north_angle,
                    statistics_lines=statistics_lines,
                    circle_windows=rotated_circle_windows,
                    hull_overlay=rotated_hull_overlay,
                    area_source=statistics.outcrop_area_source,
                    node_overlays=rotated_node_overlays if cfg.show_node_overlay else None,
                    node_label_mode=cfg.node_label_mode,
                    style=cfg.style,
                )

                rose_plot = ""
                if cfg.export_rose_plot:
                    logger.debug("  5.3 绘制玫瑰图: %s (bin=%.1f°, dpi=%d)", cfg.outcrop, cfg.rose_bin_width, cfg.rose_dpi, extra={"stage": "plot_substep", "substep": "rose"})
                    rose_plot = render_rose_plot(
                        trace.joint_strikes,
                        f"产状玫瑰花瓣图（数量={trace.count}，分箱={cfg.rose_bin_width}°）",
                        str(output_dir),
                        f"{cfg.outcrop}_rose(bin={cfg.rose_bin_width}).png",
                        bin_width=cfg.rose_bin_width,
                        dpi=cfg.rose_dpi,
                    )
                    logger.info(
                        "玫瑰图导出至: %s", rose_plot,
                        extra={"stage": "plot_rose", "outcrop": cfg.outcrop, "rose_path": rose_plot, "dpi": cfg.rose_dpi},
                    )

            plot_duration = (time.perf_counter() - t0) * 1000
            logger.info(
                "绘图完成: %s (%.3f ms)", cfg.outcrop, plot_duration,
                extra={
                    "stage": "plot",
                    "raw_plot": raw_plot,
                    "rotated_plot": rot_plot,
                    "duration_ms": round(plot_duration, 3),
                },
            )

            total_duration = (time.perf_counter() - pipeline_start) * 1000
            logger.info(
                "处理完成: %s (总耗时 %.3f ms)", cfg.outcrop, total_duration,
                extra={"stage": "pipeline_end", "duration_ms": round(total_duration, 3)},
            )

            node_summary = {
                "node_count": 0,
                "node_i_count": 0,
                "node_y_count": 0,
                "node_x_count": 0,
                "intersection_count": 0,
            }
            if node_analysis is not None:
                tc = node_analysis.type_counts
                node_summary = {
                    "node_count": node_analysis.node_count,
                    "node_i_count": tc.get("I", 0),
                    "node_y_count": tc.get("Y", 0),
                    "node_x_count": tc.get("X", 0),
                    "intersection_count": node_analysis.intersection_count,
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

        except (FileNotFoundError, ValueError, OSError, KeyError, TypeError, IndexError) as exc:
            total_duration = (time.perf_counter() - pipeline_start) * 1000
            logger.error(
                "处理 [%s] 失败 (%s): %s (%.3f ms)",
                cfg.outcrop, type(exc).__name__, exc, total_duration,
                extra={"stage": "pipeline_error", "duration_ms": round(total_duration, 3)},
            )
            return RunResult.failure(cfg.table_stem, str(exc), error_type=type(exc).__name__)
        except (MemoryError, KeyboardInterrupt):
            # 系统级异常不应静默捕获，直接抛出以保留崩溃现场
            raise
        except Exception as exc:
            total_duration = (time.perf_counter() - pipeline_start) * 1000
            import traceback
            tb = traceback.format_exc()
            logger.error(
                "处理 [%s] 时发生未预期错误: %s (%.3f ms)",
                cfg.outcrop, exc, total_duration,
                extra={"stage": "pipeline_error", "duration_ms": round(total_duration, 3)},
                exc_info=True,
            )
            return RunResult.failure(
                cfg.table_stem,
                f"{type(exc).__name__}: {exc}",
                error_type=type(exc).__name__,
                error_traceback=tb,
            )
