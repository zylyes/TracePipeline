"""迹线处理流水线 — 单目标全流程编排。

职责：串联"加载 → 变换 → 导出 Excel → 绘制图片"四个阶段，
不包含几何计算或绘图细节，仅做编排与错误包装。

对外暴露:
  - PipelineRunConfig: 单目标运行参数（不可变数据类）
  - process_target: 处理单个迹线表，返回摘要字典
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict, Mapping

from .data_loader import ParsedTraceData, load_trace_data
from .excel_export import build_excel_sections, write_excel_sections
from .plotting import build_nan_lines, render_rose_plot, render_trace_plot
from .transforms import norm_rotate_lines

logger = logging.getLogger(__name__)

__all__ = [
    "PipelineRunConfig",
    "process_target",
]

# ---------------------------------------------------------------------------
# 运行配置
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PipelineRunConfig:
    """单目标流水线运行参数（不可变）。"""

    input_dir: str
    output_dir: str
    file_name: str
    excel_base: str
    outcrop_name: str
    export_rose_plot: bool = True
    rose_bin_width: float = 10.0
    rose_dpi: int = 400

    @classmethod
    def from_mapping(cls, run_cfg: Mapping[str, Any]) -> "PipelineRunConfig":
        """从字典构造，执行字段级校验。"""
        required = ("input_dir", "output_dir", "file_name", "excel_base", "outcrop_name")
        missing = [k for k in required if str(run_cfg.get(k, "")).strip() == ""]
        if missing:
            raise ValueError(f"缺少必要流水线字段: {', '.join(missing)}")

        try:
            rose_bin_width = float(run_cfg.get("rose_bin_width", 10.0))
        except (TypeError, ValueError) as exc:
            raise ValueError("rose_bin_width 必须为数值") from exc
        if not (0 < rose_bin_width <= 180):
            raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")

        try:
            rose_dpi = int(run_cfg.get("rose_dpi", 400))
        except (TypeError, ValueError) as exc:
            raise ValueError("rose_dpi 必须为整数") from exc
        if rose_dpi <= 0:
            raise ValueError("rose_dpi 必须为正整数")

        return cls(
            input_dir=str(run_cfg["input_dir"]),
            output_dir=str(run_cfg["output_dir"]),
            file_name=str(run_cfg["file_name"]),
            excel_base=str(run_cfg["excel_base"]),
            outcrop_name=str(run_cfg["outcrop_name"]),
            export_rose_plot=bool(run_cfg.get("export_rose_plot", True)),
            rose_bin_width=rose_bin_width,
            rose_dpi=rose_dpi,
        )

    def to_loader_config(self) -> Dict[str, str]:
        """提取数据加载所需的最小配置。"""
        return {
            "input_dir": self.input_dir,
            "excel_base": self.excel_base,
            "outcrop_name": self.outcrop_name,
        }


# ---------------------------------------------------------------------------
# 单目标处理
# ---------------------------------------------------------------------------


def _summary_context(
    run_cfg: Mapping[str, Any] | PipelineRunConfig,
) -> tuple[str, str]:
    """安全提取 outcrop_name 与 excel_base，用于日志。"""
    if isinstance(run_cfg, PipelineRunConfig):
        return run_cfg.outcrop_name, run_cfg.excel_base
    return (
        str(run_cfg.get("outcrop_name", "<unknown>")),
        str(run_cfg.get("excel_base", "<unknown>")),
    )


def _make_success_summary(cfg: PipelineRunConfig, trace: ParsedTraceData,
                          excel_out: str, raw_plot: str, rot_plot: str,
                          rose_plot: str | None) -> Dict[str, Any]:
    return {
        "excel_base": cfg.excel_base,
        "excel_out": excel_out,
        "raw_plot": raw_plot,
        "rotated_plot": rot_plot,
        "trace_count": trace.trace_count,
        "rose_plot": rose_plot,
        "status": "success",
    }


def _make_error_summary(excel_base: str, error_msg: str) -> Dict[str, Any]:
    return {
        "excel_base": excel_base,
        "status": "error",
        "error": error_msg,
    }


def process_target(run_cfg: Mapping[str, Any] | PipelineRunConfig) -> Dict[str, Any]:
    """处理单个迹线表：生成 Excel 与图片，返回摘要。

    步骤:
      1. 校验配置 → 2. 加载数据 → 3. 坐标变换 → 4. 导出 Excel → 5. 绘制图片

    Args:
        run_cfg: 字典或 PipelineRunConfig，包含处理所需全部参数。

    Returns:
        摘要字典，status 为 "success" 或 "error"。
        成功时包含 excel_out, raw_plot, rotated_plot, trace_count 等字段。
        失败时包含 error 字段。
    """
    outcrop_name, excel_base = _summary_context(run_cfg)

    try:
        # ---- 0. 校验配置 ----
        cfg = (
            run_cfg
            if isinstance(run_cfg, PipelineRunConfig)
            else PipelineRunConfig.from_mapping(run_cfg)
        )
        outcrop_name, excel_base = cfg.outcrop_name, cfg.excel_base
        logger.info("开始处理: %s", outcrop_name)

        # ---- 1. 加载数据 ----
        trace = load_trace_data(cfg.to_loader_config())
        logger.info(
            "数据加载完成: %s — %d 条迹线, 走向 %.1f°",
            outcrop_name, trace.trace_count, trace.strike_deg,
        )

        # ---- 2. 坐标变换 ----
        rotated = norm_rotate_lines(trace.xy, trace.strike_deg)
        X_raw, Y_raw = build_nan_lines(trace.xy)
        X_rot, Y_rot = build_nan_lines(rotated)
        logger.debug("坐标变换完成: %s", outcrop_name)

        # ---- 3. 导出 Excel ----
        output_dir = Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        excel_out = output_dir / f"{cfg.file_name}_traces.xlsx"
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(str(excel_out), outcrop_name, sections)
        logger.info("Excel 导出至: %s", excel_out)

        # ---- 4. 绘制图片 ----
        # 4a. 原始迹线图
        raw_title = f"迹线长度图（数量={trace.trace_count}）"
        raw_name = f"{outcrop_name}_raw(n={trace.trace_count}).png"
        raw_path = render_trace_plot(
            X_raw, Y_raw, raw_title, str(output_dir), raw_name, dpi=300,
        )

        # 4b. 旋转后迹线图
        rot_title = (
            f"迹线长度图（数量={trace.trace_count}）\n"
            f"标尺（走向={trace.strike_deg}°）"
        )
        rot_name = f"{outcrop_name}_rotated(strike={trace.strike_deg}).png"
        rot_path = render_trace_plot(
            X_rot, Y_rot, rot_title, str(output_dir), rot_name, dpi=600,
        )

        # 4c. 玫瑰花瓣图（可选）
        rose_path: str | None = None
        if cfg.export_rose_plot:
            rose_title = (
                f"产状玫瑰花瓣图（数量={trace.trace_count}"
                f"，分箱={cfg.rose_bin_width}°）"
            )
            rose_name = f"{outcrop_name}_rose(bin={cfg.rose_bin_width}).png"
            rose_path = render_rose_plot(
                trace.joint_strike_deg,
                rose_title,
                str(output_dir),
                rose_name,
                bin_width=cfg.rose_bin_width,
                dpi=cfg.rose_dpi,
            )
            logger.info("玫瑰图导出至: %s", rose_path)

        logger.info("处理完成: %s", outcrop_name)
        return _make_success_summary(
            cfg, trace, str(excel_out), raw_path, rot_path, rose_path,
        )

    except FileNotFoundError as exc:
        logger.error("文件未找到 [%s]: %s", outcrop_name, exc)
        return _make_error_summary(excel_base, str(exc))
    except ValueError as exc:
        logger.error("数据校验失败 [%s]: %s", outcrop_name, exc)
        return _make_error_summary(excel_base, str(exc))
    except OSError as exc:
        logger.error("文件写入失败 [%s]: %s", outcrop_name, exc)
        return _make_error_summary(excel_base, str(exc))
    except Exception as exc:
        logger.error(
            "处理 %s 时发生未预期错误: %s",
            outcrop_name, exc, exc_info=True,
        )
        return _make_error_summary(excel_base, str(exc))
