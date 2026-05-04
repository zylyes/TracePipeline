"""迹线处理流水线 — 数据模型与校验。

所有不可变数据类集中定义于此：
  - TraceData  : 单张迹线表的完整解析结果
  - RunConfig  : 单次流水线运行的参数（含校验）
  - RunResult  : 单次流水线运行的结果

（历史文件名：types.py）
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any, Mapping

import numpy as np

__all__ = [
    "RunConfig",
    "RunResult",
    "TraceData",
]


# ===========================================================================
# 内部校验
# ===========================================================================


def _validate_rose_bin_width(value: Any) -> float:
    """校验 rose_bin_width：必须为数值且在 (0, 180] 范围内。"""
    try:
        width = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("rose_bin_width 必须为数值") from exc
    if not (0 < width <= 180):
        raise ValueError("rose_bin_width 必须在 (0, 180] 范围内")
    return width


def _validate_dpi(value: Any) -> int:
    """校验 DPI 参数：必须为正整数。"""
    try:
        dpi = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("DPI 必须为整数") from exc
    if dpi <= 0:
        raise ValueError("DPI 必须为正整数")
    return dpi


# ===========================================================================
# TraceData — 解析后的迹线数据
# ===========================================================================


@dataclass
class TraceData:
    """单张迹线表的完整解析结果（不可变数据容器）。

    Attributes:
        scanline_azimuth: 测线走向角（度），已规范化到 [0, 360)。
        count: 迹线条数，≥ 0。
        endpoints: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]。
        joint_strikes: 各节理走向角（度），长度 N。
        segment_lengths: 沿测段的迹线长度 r5+r7（MATLAB 定义），长度 N。
    """

    scanline_azimuth: float
    count: int
    endpoints: np.ndarray
    joint_strikes: np.ndarray
    segment_lengths: np.ndarray

    def __post_init__(self) -> None:
        if not np.isfinite(self.scanline_azimuth):
            raise ValueError("scanline_azimuth 必须为有限浮点数")
        if self.count < 0:
            raise ValueError(f"count 不能为负数: {self.count}")
        if self.count > 0:
            if self.endpoints.shape != (self.count, 4):
                raise ValueError(
                    f"endpoints 形状 {self.endpoints.shape} 与 count={self.count} 不一致"
                )
            if len(self.joint_strikes) != self.count:
                raise ValueError(
                    f"joint_strikes 长度 {len(self.joint_strikes)} "
                    f"与 count={self.count} 不一致"
                )
            if len(self.segment_lengths) != self.count:
                raise ValueError(
                    f"segment_lengths 长度 {len(self.segment_lengths)} "
                    f"与 count={self.count} 不一致"
                )

    # ---- 派生属性 ----

    @cached_property
    def lengths(self) -> np.ndarray:
        """迹线端点间的二维欧氏距离 (N,)，首次访问后缓存。"""
        if self.count == 0:
            return np.array([], dtype=float)
        dx = self.endpoints[:, 2] - self.endpoints[:, 0]
        dy = self.endpoints[:, 3] - self.endpoints[:, 1]
        return np.hypot(dx, dy)

    @property
    def mean_length(self) -> float:
        """平均迹线长度（基于端点距离）。"""
        return float(self.lengths.mean()) if self.count else 0.0


# ===========================================================================
# RunConfig — 流水线运行参数
# ===========================================================================


@dataclass(frozen=True)
class RunConfig:
    """单次流水线运行参数（不可变）。

    Attributes:
        input_dir: 输入目录绝对路径。
        output_dir: 输出目录绝对路径。
        output_prefix: 输出文件命名前缀。
        table_stem: 迹线表文件名（不含扩展名）。
        outcrop: 露头标识（也是 Excel 工作表名）。
        export_rose_plot: 是否导出玫瑰花瓣图。
        rose_bin_width: 玫瑰图分箱宽度（度）。
        rose_dpi: 玫瑰图分辨率。
        trace_dpi: 原始迹线图分辨率。
        rotated_trace_dpi: 旋转迹线图分辨率。
    """

    input_dir: str
    output_dir: str
    output_prefix: str
    table_stem: str
    outcrop: str
    export_rose_plot: bool = True
    rose_bin_width: float = 10.0
    rose_dpi: int = 400
    trace_dpi: int = 300
    rotated_trace_dpi: int = 600

    def __post_init__(self) -> None:
        for name in ("table_stem", "outcrop", "output_prefix", "input_dir", "output_dir"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} 不能为空")
        _validate_rose_bin_width(self.rose_bin_width)
        _validate_dpi(self.rose_dpi)
        _validate_dpi(self.trace_dpi)
        _validate_dpi(self.rotated_trace_dpi)

    # ---- 工厂方法 ----

    @classmethod
    def from_mapping(cls, cfg: Mapping[str, Any]) -> "RunConfig":
        """从配置字典构造，执行字段级校验。"""
        return cls(
            input_dir=str(cfg["input_dir"]),
            output_dir=str(cfg["output_dir"]),
            output_prefix=str(cfg["output_prefix"]),
            table_stem=str(cfg["table_stem"]),
            outcrop=str(cfg["outcrop"]),
            export_rose_plot=bool(cfg.get("export_rose_plot", True)),
            rose_bin_width=float(cfg.get("rose_bin_width", 10.0)),
            rose_dpi=int(cfg.get("rose_dpi", 400)),
            trace_dpi=int(cfg.get("trace_dpi", 300)),
            rotated_trace_dpi=int(cfg.get("rotated_trace_dpi", 600)),
        )


# ===========================================================================
# RunResult — 流水线运行结果
# ===========================================================================


@dataclass(frozen=True)
class RunResult:
    """单次流水线运行结果（不可变）。"""

    table_stem: str
    status: str  # "success" | "error"
    trace_count: int = 0
    mean_length: float = 0.0
    scanline_azimuth: float = 0.0
    excel_path: str = ""
    raw_plot_path: str = ""
    rotated_plot_path: str = ""
    rose_plot_path: str = ""
    error: str = ""

    @classmethod
    def success(
        cls,
        table_stem: str,
        trace_count: int,
        mean_length: float = 0.0,
        scanline_azimuth: float = 0.0,
        excel_path: str = "",
        raw_plot_path: str = "",
        rotated_plot_path: str = "",
        rose_plot_path: str = "",
    ) -> "RunResult":
        return cls(
            table_stem=table_stem,
            status="success",
            trace_count=trace_count,
            mean_length=mean_length,
            scanline_azimuth=scanline_azimuth,
            excel_path=excel_path,
            raw_plot_path=raw_plot_path,
            rotated_plot_path=rotated_plot_path,
            rose_plot_path=rose_plot_path,
        )

    @classmethod
    def failure(cls, table_stem: str, error: str) -> "RunResult":
        return cls(table_stem=table_stem, status="error", error=error)
