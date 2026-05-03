"""迹线处理流水线 — 数据模型。

所有不可变数据类集中定义于此：
  - TraceData  : 单张迹线表的完整解析结果
  - RunConfig  : 单次流水线运行的参数
  - RunResult  : 单次流水线运行的结果
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Mapping

import numpy as np

__all__ = [
    "RunConfig",
    "RunResult",
    "TraceData",
]


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
    """

    scanline_azimuth: float
    count: int
    endpoints: np.ndarray
    joint_strikes: np.ndarray

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

    # ---- 派生属性 ----

    @cached_property
    def lengths(self) -> np.ndarray:
        """迹线二维欧氏长度 (N,)，首次访问后缓存。"""
        if self.count == 0:
            return np.array([], dtype=float)
        dx = self.endpoints[:, 2] - self.endpoints[:, 0]
        dy = self.endpoints[:, 3] - self.endpoints[:, 1]
        return np.hypot(dx, dy)

    @property
    def mean_length(self) -> float:
        """平均迹线长度。"""
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
        export_rose: 是否导出玫瑰花瓣图。
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
    export_rose: bool = True
    rose_bin_width: float = 10.0
    rose_dpi: int = 400
    trace_dpi: int = 300
    rotated_trace_dpi: int = 600

    # ---- 工厂方法 ----

    @classmethod
    def from_mapping(cls, cfg: Mapping[str, Any]) -> "RunConfig":
        """从配置字典构造，执行字段级校验。

        自动兼容旧版键名（excel_base→table_stem, outcrop_name→outcrop,
        file_name→output_prefix）。
        """
        from .config import validate_dpi, validate_rose_bin_width

        # 兼容旧键名
        normalized = dict(cfg)
        for old_key, new_key in [
            ("excel_base", "table_stem"),
            ("outcrop_name", "outcrop"),
            ("file_name", "output_prefix"),
        ]:
            if old_key in normalized and new_key not in normalized:
                normalized[new_key] = normalized.pop(old_key)

        required = ("input_dir", "output_dir", "output_prefix", "table_stem", "outcrop")
        missing = [k for k in required if str(normalized.get(k, "")).strip() == ""]
        if missing:
            raise ValueError(f"缺少必要字段: {', '.join(missing)}")

        return cls(
            input_dir=str(normalized["input_dir"]),
            output_dir=str(normalized["output_dir"]),
            output_prefix=str(normalized["output_prefix"]),
            table_stem=str(normalized["table_stem"]),
            outcrop=str(normalized["outcrop"]),
            export_rose=bool(normalized.get("export_rose_plot", True)),
            rose_bin_width=validate_rose_bin_width(normalized.get("rose_bin_width", 10.0)),
            rose_dpi=validate_dpi(normalized.get("rose_dpi", 400)),
            trace_dpi=validate_dpi(normalized.get("trace_dpi", 300)),
            rotated_trace_dpi=validate_dpi(normalized.get("rotated_trace_dpi", 600)),
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
