"""迹线处理流水线 — 数据模型与校验。

所有不可变数据类集中定义于此：
  - TraceData  : 单张迹线表的完整解析结果
  - RunConfig  : 单次流水线运行的参数（含校验）
  - RunResult  : 单次流水线运行的结果

（历史文件名：types.py）
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .validation import coerce_scalar_config_fields

__all__ = [
    "RunConfig",
    "RunResult",
    "TraceData",
]


# ===========================================================================
# TraceData — 解析后的迹线数据
# ===========================================================================


@dataclass(frozen=True)
class TraceData:
    """单张迹线表的完整解析结果（不可变数据容器）。

    Attributes:
        scanline_azimuth: 测线走向角（度），已规范化到 [0, 360)。
        count: 迹线条数，≥ 0。
        endpoints: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]。
        joint_strikes: 各节理走向角（度），长度 N。
        segment_lengths: 沿测段的迹线长度 r5+r7（MATLAB 定义），长度 N。
        scanline_positions: 沿测线位移 r1，长度 N。
        measured_scanline_length: 实测测线长度（m），缺失时为 None。
        measured_outcrop_area: 实测露头面积（m²），缺失时为 None。
    """

    scanline_azimuth: float
    count: int
    endpoints: np.ndarray
    joint_strikes: np.ndarray
    segment_lengths: np.ndarray
    scanline_positions: np.ndarray
    measured_scanline_length: float | None = None
    measured_outcrop_area: float | None = None

    def __post_init__(self) -> None:
        endpoints = np.array(self.endpoints, dtype=float, copy=True)
        joint_strikes = np.array(self.joint_strikes, dtype=float, copy=True)
        segment_lengths = np.array(self.segment_lengths, dtype=float, copy=True)
        scanline_positions = np.array(self.scanline_positions, dtype=float, copy=True)
        object.__setattr__(self, "endpoints", endpoints)
        object.__setattr__(self, "joint_strikes", joint_strikes)
        object.__setattr__(self, "segment_lengths", segment_lengths)
        object.__setattr__(self, "scanline_positions", scanline_positions)

        if not np.isfinite(self.scanline_azimuth):
            raise ValueError("scanline_azimuth 必须为有限浮点数")
        if self.count < 0:
            raise ValueError(f"count 不能为负数: {self.count}")
        if endpoints.shape != (self.count, 4):
            raise ValueError(
                f"endpoints 形状 {endpoints.shape} 与 count={self.count} 不一致"
            )
        if joint_strikes.shape != (self.count,):
            raise ValueError(
                f"joint_strikes 形状 {joint_strikes.shape} "
                f"与 count={self.count} 不一致"
            )
        if segment_lengths.shape != (self.count,):
            raise ValueError(
                f"segment_lengths 形状 {segment_lengths.shape} "
                f"与 count={self.count} 不一致"
            )
        if scanline_positions.shape != (self.count,):
            raise ValueError(
                f"scanline_positions 形状 {scanline_positions.shape} "
                f"与 count={self.count} 不一致"
            )
        if not np.isfinite(endpoints).all():
            raise ValueError("endpoints 包含 NaN 或 inf")
        if not np.isfinite(joint_strikes).all():
            raise ValueError("joint_strikes 包含 NaN 或 inf")
        if not np.isfinite(segment_lengths).all():
            raise ValueError("segment_lengths 包含 NaN 或 inf")
        if not np.isfinite(scanline_positions).all():
            raise ValueError("scanline_positions 包含 NaN 或 inf")
        object.__setattr__(
            self,
            "measured_scanline_length",
            self._validate_optional_positive(
                self.measured_scanline_length,
                "measured_scanline_length",
            ),
        )
        object.__setattr__(
            self,
            "measured_outcrop_area",
            self._validate_optional_positive(
                self.measured_outcrop_area,
                "measured_outcrop_area",
            ),
        )
        endpoints.flags.writeable = False
        joint_strikes.flags.writeable = False
        segment_lengths.flags.writeable = False
        scanline_positions.flags.writeable = False

    @staticmethod
    def _validate_optional_positive(value: float | None, name: str) -> float | None:
        if value is None:
            return None
        value = float(value)
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} 必须为正的有限浮点数")
        return value

    # ---- 派生属性 ----

    @property
    def lengths(self) -> np.ndarray:
        """迹线端点间的二维欧氏距离 (N,)，首次访问后缓存。"""
        try:
            cached: np.ndarray = self.__dict__["_lengths"]
            return cached
        except KeyError:
            pass
        if self.count == 0:
            result = np.array([], dtype=float)
        else:
            dx = self.endpoints[:, 2] - self.endpoints[:, 0]
            dy = self.endpoints[:, 3] - self.endpoints[:, 1]
            result = np.hypot(dx, dy)
        result.flags.writeable = False
        self.__dict__["_lengths"] = result
        return result

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
        window_strategy: 圆形取样窗策略。
        auto_density_threshold: auto 策略的粗估面密度阈值。
        tangent_window_count: tangent 策略每侧切圆数量。
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
    window_strategy: str = "auto"
    auto_density_threshold: float = 5.0
    tangent_window_count: int = 3

    def __post_init__(self) -> None:
        for name in ("table_stem", "outcrop", "output_prefix", "input_dir", "output_dir"):
            normalized = str(getattr(self, name)).strip()
            if not normalized:
                raise ValueError(f"{name} 不能为空")
            object.__setattr__(self, name, normalized)

        field_values = {
            k: getattr(self, k)
            for k in ("export_rose_plot", "rose_bin_width", "rose_dpi",
                      "trace_dpi", "rotated_trace_dpi", "window_strategy",
                      "auto_density_threshold", "tangent_window_count")
        }
        coerce_scalar_config_fields(field_values)
        for k, v in field_values.items():
            object.__setattr__(self, k, v)

    # ---- 工厂方法 ----

    @classmethod
    def from_mapping(cls, cfg: Mapping[str, Any]) -> RunConfig:
        """从配置字典构造，执行字段级校验。"""
        return cls(
            input_dir=str(cfg["input_dir"]),
            output_dir=str(cfg["output_dir"]),
            output_prefix=str(cfg["output_prefix"]),
            table_stem=str(cfg["table_stem"]),
            outcrop=str(cfg["outcrop"]),
            export_rose_plot=cfg.get("export_rose_plot", True),
            rose_bin_width=cfg.get("rose_bin_width", 10.0),
            rose_dpi=cfg.get("rose_dpi", 400),
            trace_dpi=cfg.get("trace_dpi", 300),
            rotated_trace_dpi=cfg.get("rotated_trace_dpi", 600),
            window_strategy=cfg.get("window_strategy", "auto"),
            auto_density_threshold=cfg.get("auto_density_threshold", 5.0),
            tangent_window_count=cfg.get("tangent_window_count", 3),
        )


# ===========================================================================
# RunResult — 流水线运行结果
# ===========================================================================


@dataclass(frozen=True)
class RunResult:
    """单次流水线运行结果（不可变）。"""

    table_stem: str
    status: Literal["success", "error"]
    trace_count: int = 0
    mean_length: float = 0.0
    scanline_azimuth: float = 0.0
    excel_path: str = ""
    raw_plot_path: str = ""
    rotated_plot_path: str = ""
    rose_plot_path: str = ""
    window_strategy: str = ""
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
        window_strategy: str = "",
    ) -> RunResult:
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
            window_strategy=window_strategy,
        )

    @classmethod
    def failure(cls, table_stem: str, error: str) -> RunResult:
        return cls(table_stem=table_stem, status="error", error=error)
