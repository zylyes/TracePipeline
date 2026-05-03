"""迹线处理流水线 — 单目标全流程编排。

串联「加载 → 计算 → 变换 → 导出 Excel → 绘制图片」五个阶段。
不包含几何计算或绘图细节，仅做编排与异常包装。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Mapping

from .io import build_excel_sections, parse_trace_file, write_excel_sections
from .models import RunConfig, RunResult
from .transforms import normalize_coordinates
from .plotting import segments_to_plot_xy, render_rose_plot, render_trace_plot

logger = logging.getLogger(__name__)


# ===========================================================================
# 单目标处理
# ===========================================================================


def run_pipeline(run_cfg: Mapping[str, Any] | RunConfig) -> RunResult:
    """处理单个迹线表：加载 → 变换 → 导出 Excel → 绘图。

    支持两种输入：
      - RunConfig 实例（推荐）
      - 配置字典（兼容旧代码，自动升级）

    Returns:
        RunResult — 不可变结果对象，.status 为 "success" 或 "error"。
    """
    # ---- 配置解析 ----
    try:
        if isinstance(run_cfg, RunConfig):
            cfg = run_cfg
        else:
            cfg = RunConfig.from_mapping(run_cfg)
    except Exception as exc:
        logger.error("配置校验失败: %s", exc)
        table_stem = _safe_table_stem(run_cfg)
        return RunResult.failure(table_stem, str(exc))

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
        X_raw, Y_raw = segments_to_plot_xy(trace.endpoints)
        X_rot, Y_rot = segments_to_plot_xy(rotated)

        # ---- 3. 导出 Excel ----
        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        excel_path = output_dir / f"{cfg.output_prefix}_traces.xlsx"
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(str(excel_path), cfg.outcrop, sections)
        logger.info("Excel 导出至: %s", excel_path)

        # ---- 4. 绘制图片 ----
        raw_plot = render_trace_plot(
            X_raw, Y_raw,
            f"迹线长度图（数量={trace.count}）",
            str(output_dir),
            f"{cfg.outcrop}_raw(n={trace.count}).png",
            dpi=cfg.trace_dpi,
        )

        rot_plot = render_trace_plot(
            X_rot, Y_rot,
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


# ===========================================================================
# 辅助
# ===========================================================================


def _safe_table_stem(run_cfg: Mapping[str, Any] | RunConfig | None) -> str:
    """安全提取 table_stem/excel_base，配置无效时返回空字符串。"""
    if run_cfg is None:
        return ""
    if isinstance(run_cfg, RunConfig):
        return run_cfg.table_stem
    try:
        return str(run_cfg.get("table_stem", run_cfg.get("excel_base", "")))
    except Exception:
        return ""


__all__ = [
    "run_pipeline",
]
