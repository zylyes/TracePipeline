"""迹线 Excel 读取与数据封装。

该模块负责从输入目录读取原始 Excel 表格并将其解析为内部数据结构
ParsedTraceData，包含测线走向（角度）、迹线数量、端点坐标数组（N×4）
以及每条迹线的节理走向。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import cached_property
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
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class ParsedTraceData:
    """单张迹线表解析结果（不可变语义，字段通过 trace_lengths 计算属性扩展）。

    Attributes:
        strike_deg: 测线走向角（度），范围 [0, 360)。
        trace_count: 迹线条数。
        xy: 端点坐标 (N, 4)，列序 [x1, y1, x2, y2]。
        joint_strike_deg: 每条迹线的节理走向（度），长度 N。
    """

    strike_deg: float
    trace_count: int
    xy: np.ndarray
    joint_strike_deg: np.ndarray
    # 内部缓存（不入 repr，不参与比较）
    _trace_lengths: np.ndarray | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """构造后校验数据一致性。"""
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
        """每条迹线的二维欧氏长度（缓存）。

        Returns:
            (N,) 数组，长度 = sqrt((x2-x1)² + (y2-y1)²)。
        """
        if self.trace_count == 0:
            return np.array([], dtype=float)
        dx = self.xy[:, 2] - self.xy[:, 0]
        dy = self.xy[:, 3] - self.xy[:, 1]
        return np.hypot(dx, dy)


# ---------------------------------------------------------------------------
# 文件加载
# ---------------------------------------------------------------------------


def _build_excel_paths(base_path: str, excel_base: str) -> tuple[str, str]:
    """返回 (.xlsx 路径, .xls 路径) 元组。"""
    return (
        os.path.join(base_path, excel_base + ".xlsx"),
        os.path.join(base_path, excel_base + ".xls"),
    )


def load_trace_table(
    base_path: str,
    excel_base: str,
    sheet: str | None = None,
) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失则回退 .xls。

    Args:
        base_path: 输入目录路径。
        excel_base: 不含扩展名的 Excel 文件名。
        sheet: 工作表名。若为 None 或指定 sheet 不存在，回退到第一个 sheet。

    Returns:
        原始 DataFrame（无表头）。

    Raises:
        FileNotFoundError: .xlsx 和 .xls 均不存在时。
    """
    path_xlsx, path_xls = _build_excel_paths(base_path, excel_base)

    for path, engine in ((path_xlsx, "openpyxl"), (path_xls, "xlrd")):
        if not os.path.exists(path):
            continue
        logger.debug("读取文件: %s (引擎=%s)", path, engine)
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet or 0, header=None)
        except ValueError:
            # 指定 sheet 不存在时回退到第一个 sheet
            logger.debug("工作表 '%s' 不存在，回退到第一个 sheet", sheet)
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)
        except Exception as exc:
            logger.warning("读取 %s 失败 (%s)，尝试下一格式", path, exc)
            continue

    raise FileNotFoundError(
        f"在 {base_path} 下未找到 {excel_base}.xlsx 或 {excel_base}.xls"
    )


def load_trace_data(cfg: Mapping[str, Any]) -> ParsedTraceData:
    """根据配置字典读取 Excel 并封装为 ParsedTraceData。

    Args:
        cfg: 至少包含 "input_dir", "excel_base", "outcrop_name" 的字典。

    Returns:
        解析后的 ParsedTraceData。

    Raises:
        ValueError: 配置字段缺失。
        FileNotFoundError: Excel 文件不存在。
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
    logger.info(
        "解析完成: %d 条迹线, 走向 %.1f°, 平均迹长 %.2f",
        n, ang0, float(np.hypot(XY[:, 2] - XY[:, 0], XY[:, 3] - XY[:, 1]).mean()) if n else 0,
    )

    return ParsedTraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
        joint_strike_deg=joint_strike_deg,
    )
