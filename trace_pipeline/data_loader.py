"""迹线 Excel 读取与 ParsedTraceData 数据封装。

从输入目录读取原始 Excel 表格，经 geometry.parse_trace_table 解析后，
封装为不可变数据类 ParsedTraceData（含校验与自动计算迹线长度）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from trace_pipeline.geometry import parse_trace_table

logger = logging.getLogger(__name__)

__all__ = [
    "ParsedTraceData",
    "load_trace_data",
    "load_trace_table",
]


# ---------------------------------------------------------------------------
# ParsedTraceData
# ---------------------------------------------------------------------------

@dataclass
class ParsedTraceData:
    """单张迹线表的完整解析结果。

    Attributes:
        strike_deg: 测线走向角（度），已规范化到 [0, 360)。
        trace_count: 迹线条数，≥ 0。
        xy: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]。
        joint_strike_deg: 节理走向（度），长度 N。
    """

    strike_deg: float
    trace_count: int
    xy: np.ndarray
    joint_strike_deg: np.ndarray
    _trace_lengths: np.ndarray | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.strike_deg):
            raise ValueError("strike_deg 必须为有限浮点数")
        if self.trace_count < 0:
            raise ValueError(f"trace_count 不能为负数: {self.trace_count}")
        if self.trace_count > 0:
            if self.xy.shape != (self.trace_count, 4):
                raise ValueError(
                    f"xy 形状 {self.xy.shape} 与 trace_count={self.trace_count} 不一致"
                )
            if len(self.joint_strike_deg) != self.trace_count:
                raise ValueError(
                    f"joint_strike_deg 长度 {len(self.joint_strike_deg)} "
                    f"与 trace_count={self.trace_count} 不一致"
                )

    @cached_property
    def trace_lengths(self) -> np.ndarray:
        """迹线二维欧氏长度 (N,)，首次访问后缓存。"""
        if self.trace_count == 0:
            return np.array([], dtype=float)
        dx = self.xy[:, 2] - self.xy[:, 0]
        dy = self.xy[:, 3] - self.xy[:, 1]
        return np.hypot(dx, dy)


# ---------------------------------------------------------------------------
# 文件加载
# ---------------------------------------------------------------------------

def load_trace_table(
    base_path: str,
    excel_base: str,
    sheet: str | None = None,
) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失则回退 .xls。

    Args:
        base_path: 输入目录路径。
        excel_base: 不含扩展名的文件名。
        sheet: 工作表名；为 None 或不存在时回退到第一个 sheet。

    Returns:
        无表头的原始 DataFrame。

    Raises:
        FileNotFoundError: .xlsx 与 .xls 均不存在。
    """
    base = Path(base_path)
    candidates = [
        (base / f"{excel_base}.xlsx", "openpyxl"),
        (base / f"{excel_base}.xls", "xlrd"),
    ]

    last_error: Exception | None = None
    for path, engine in candidates:
        if not path.is_file():
            continue
        logger.debug("读取文件: %s (引擎=%s)", path, engine)
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet or 0, header=None)
        except ValueError:
            logger.debug("工作表 '%s' 不存在，回退到第一个 sheet", sheet)
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)
        except Exception as exc:
            logger.warning("读取 %s 失败 (%s)，尝试下一格式", path, exc)
            last_error = exc
            continue

    raise FileNotFoundError(
        f"在 {base_path} 下未找到 {excel_base}.xlsx 或 {excel_base}.xls"
    ) from last_error


def load_trace_data(cfg: Mapping[str, Any]) -> ParsedTraceData:
    """从配置字典加载并解析迹线表，返回 ParsedTraceData。

    cfg 必须包含: input_dir, excel_base, outcrop_name。
    """
    required = ("input_dir", "excel_base", "outcrop_name")
    missing = [k for k in required if str(cfg.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    input_dir = str(cfg["input_dir"])
    excel_base = str(cfg["excel_base"])
    outcrop_name = str(cfg["outcrop_name"])

    logger.info("加载迹线数据: %s/%s", input_dir, excel_base)
    df = load_trace_table(input_dir, excel_base, outcrop_name)

    ang0, n, XY, joint_strike_deg = parse_trace_table(df)

    if n:
        avg_len = float(np.hypot(XY[:, 2] - XY[:, 0], XY[:, 3] - XY[:, 1]).mean())
    else:
        avg_len = 0.0
    logger.info("解析完成: %d 条迹线, 走向 %.1f°, 平均迹长 %.2f", n, ang0, avg_len)

    return ParsedTraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
        joint_strike_deg=joint_strike_deg,
    )
