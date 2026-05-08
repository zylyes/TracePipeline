"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .geology.angles import fold_strike_angle
from .geology.endpoints import compute_endpoints
from .geology.statistics import (
    TraceStatistics,
    TraceStatisticsConfig,
    compute_trace_statistics,
    format_statistics_box_lines,
)
from .geology.transforms import (
    local_points_to_global,
    normalize_coordinates,
    normalize_points_like_lines,
)
from .io.excel_reader import read_trace_excel
from .io.excel_writer import build_excel_sections, write_excel_sections
from .models import RunConfig, RunResult, TraceData
from .plotting.rose_plot import render_rose_plot
from .plotting.trace_plot import CircleWindowOverlay, render_trace_plot

logger = logging.getLogger(__name__)

__all__ = ["load_trace_data", "run_pipeline"]


def _circle_window_overlays_for_raw_plot(
    trace: TraceData,
    statistics: TraceStatistics,
) -> tuple[CircleWindowOverlay, ...]:
    centers: list[tuple[float, float]] = []
    radii: list[float] = []
    for diagnostic in statistics.diagnostics:
        geometry = np.array(
            [diagnostic.center_x, diagnostic.center_y, diagnostic.radius],
            dtype=float,
        )
        if diagnostic.valid and np.isfinite(geometry).all() and diagnostic.radius > 0.0:
            centers.append((diagnostic.center_x, diagnostic.center_y))
            radii.append(float(diagnostic.radius))

    if not centers:
        return ()

    global_centers = local_points_to_global(np.array(centers, dtype=float), trace.scanline_azimuth)
    return tuple(
        CircleWindowOverlay(float(center[0]), float(center[1]), radius)
        for center, radius in zip(global_centers, radii)
    )


def _circle_window_overlays_for_rotated_plot(
    trace: TraceData,
    raw_overlays: tuple[CircleWindowOverlay, ...],
) -> tuple[CircleWindowOverlay, ...]:
    if not raw_overlays:
        return ()

    centers = np.array(
        [(overlay.center_x, overlay.center_y) for overlay in raw_overlays],
        dtype=float,
    )
    rotated_centers = normalize_points_like_lines(centers, trace.endpoints, trace.scanline_azimuth)
    return tuple(
        CircleWindowOverlay(float(center[0]), float(center[1]), overlay.radius)
        for center, overlay in zip(rotated_centers, raw_overlays)
    )


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
        raw_circle_windows = _circle_window_overlays_for_raw_plot(trace, statistics)
        rotated_circle_windows = _circle_window_overlays_for_rotated_plot(trace, raw_circle_windows)

        # ---- 3. 导出 Excel ----
        output_dir = Path(cfg.output_dir)
        excel_path = output_dir / f"{cfg.output_prefix}_traces.xlsx"
        sections = build_excel_sections(trace, rotated, statistics=statistics)
        write_excel_sections(str(excel_path), cfg.outcrop, sections)
        logger.info("Excel 导出至: %s", excel_path)

        # ---- 4. 绘制图片 ----
        raw_plot = render_trace_plot(
            trace.endpoints,
            "迹线长度图",
            str(output_dir),
            f"{cfg.outcrop}_raw(n={trace.count}).png",
            dpi=cfg.trace_dpi,
            statistics_lines=statistics_lines,
            circle_windows=raw_circle_windows,
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

        logger.info("处理完成: %s", cfg.outcrop)
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
        )

    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("处理 [%s] 失败 (%s): %s", cfg.outcrop, type(exc).__name__, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except Exception as exc:
        logger.error("处理 [%s] 时发生未预期错误: %s", cfg.outcrop, exc, exc_info=True)
        return RunResult.failure(cfg.table_stem, f"{type(exc).__name__}: {exc}")
