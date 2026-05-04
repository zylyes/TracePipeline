"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .geology.endpoints import compute_endpoints
from .geology.transforms import normalize_coordinates
from .io.excel_reader import read_trace_excel
from .io.excel_writer import build_excel_sections, write_excel_sections
from .models import RunConfig, RunResult, TraceData
from .plotting.rose_plot import render_rose_plot
from .plotting.trace_plot import render_trace_plot

logger = logging.getLogger(__name__)

__all__ = ["load_trace_data", "run_pipeline"]


def load_trace_data(input_dir: str, table_stem: str, outcrop: str) -> TraceData:
    """读取迹线 Excel 表并解析为 TraceData。"""
    logger.info("加载迹线数据: %s/%s", input_dir, table_stem)
    df = read_trace_excel(input_dir, table_stem, outcrop)

    azimuth, n, endpoints, joint_strikes, segment_lengths = compute_endpoints(df)
    trace = TraceData(
        scanline_azimuth=azimuth,
        count=n,
        endpoints=endpoints,
        joint_strikes=joint_strikes,
        segment_lengths=segment_lengths,
    )
    logger.info(
        "解析完成: %d 条迹线, 走向 %.1f°, 平均端点距离 %.2f",
        n, azimuth, trace.mean_length,
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

        # ---- 3. 导出 Excel ----
        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        excel_path = output_dir / f"{cfg.output_prefix}_traces.xlsx"
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(str(excel_path), cfg.outcrop, sections)
        logger.info("Excel 导出至: %s", excel_path)

        # ---- 4. 绘制图片 ----
        raw_plot = render_trace_plot(
            trace.endpoints,
            f"迹线长度图（数量={trace.count}）",
            str(output_dir),
            f"{cfg.outcrop}_raw(n={trace.count}).png",
            dpi=cfg.trace_dpi,
        )
        rot_plot = render_trace_plot(
            rotated,
            f"迹线长度图（数量={trace.count}）\n标尺（走向={trace.scanline_azimuth}°）",
            str(output_dir),
            f"{cfg.outcrop}_rotated(strike={trace.scanline_azimuth}).png",
            dpi=cfg.rotated_trace_dpi,
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
            mean_length=trace.mean_length,
            scanline_azimuth=trace.scanline_azimuth,
            excel_path=str(excel_path),
            raw_plot_path=raw_plot,
            rotated_plot_path=rot_plot,
            rose_plot_path=rose_plot,
        )

    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("处理 [%s] 失败 (%s): %s", cfg.outcrop, type(exc).__name__, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except Exception as exc:
        logger.error("处理 [%s] 时发生未预期错误: %s", cfg.outcrop, exc, exc_info=True)
        return RunResult.failure(cfg.table_stem, str(exc))
