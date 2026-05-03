"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
不包含几何计算或绘图细节，仅做编排与异常包装。
"""
from __future__ import annotations

import logging
from pathlib import Path

from .io import build_excel_sections, parse_trace_file, write_excel_sections
from .plotting import render_rose_plot, render_trace_plot
from .transforms import normalize_coordinates, segments_to_xy
from .types import RunConfig, RunResult

logger = logging.getLogger(__name__)


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
        trace = parse_trace_file(cfg.input_dir, cfg.table_stem, cfg.outcrop)
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
        if cfg.export_rose:
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

    except FileNotFoundError as exc:
        logger.error("文件未找到 [%s]: %s", cfg.outcrop, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except ValueError as exc:
        logger.error("数据校验失败 [%s]: %s", cfg.outcrop, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except OSError as exc:
        logger.error("文件写入失败 [%s]: %s", cfg.outcrop, exc)
        return RunResult.failure(cfg.table_stem, str(exc))
    except Exception as exc:
        logger.error("处理 [%s] 时发生未预期错误: %s", cfg.outcrop, exc, exc_info=True)
        return RunResult.failure(cfg.table_stem, str(exc))


__all__ = [
    "run_pipeline",
]