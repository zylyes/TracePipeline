"""迹线 Excel 读取与数据封装。

该模块负责从输入目录读取原始 Excel 表格并将其解析为内部数据结构
ParsedTraceData，包含测线走向（角度）、迹线数量、端点坐标数组（N×4）
以及每条迹线的节理走向。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Mapping

import numpy as np
import pandas as pd

from trace_pipeline.geometry import parse_trace_table


@dataclass
class ParsedTraceData:
    """单张迹线表解析结果。"""

    strike_deg: float
    trace_count: int
    xy: np.ndarray
    joint_strike_deg: np.ndarray
    # 内部缓存
    _trace_lengths: np.ndarray | None = field(default=None, repr=False, compare=False)

    @cached_property
    def trace_lengths(self) -> np.ndarray:
        """每条迹线的二维欧氏长度（缓存）。"""
        dx = self.xy[:, 2] - self.xy[:, 0]
        dy = self.xy[:, 3] - self.xy[:, 1]
        return np.hypot(dx, dy)


def _build_excel_paths(base_path: str, excel_base: str) -> tuple[str, str]:
    """返回 (.xlsx 路径, .xls 路径) 元组。"""
    return (
        os.path.join(base_path, excel_base + ".xlsx"),
        os.path.join(base_path, excel_base + ".xls"),
    )


def load_trace_table(base_path: str, excel_base: str, sheet: str) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失则回退 .xls。

    Raises:
        FileNotFoundError: 两种格式均不存在时抛出，附带明确路径提示。
    """
    path_xlsx, path_xls = _build_excel_paths(base_path, excel_base)

    for path, engine in ((path_xlsx, "openpyxl"), (path_xls, "xlrd")):
        if not os.path.exists(path):
            continue
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet, header=None)
        except ValueError:
            # 指定 sheet 不存在时回退到第一个 sheet
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    raise FileNotFoundError(
        f"在 {base_path} 下未找到 {excel_base}.xlsx 或 {excel_base}.xls"
    )


def load_trace_data(cfg: Mapping[str, Any]) -> ParsedTraceData:
    """根据配置字典读取 Excel 并封装为 ParsedTraceData。"""
    required = ("input_dir", "excel_base", "outcrop_name")
    missing = [k for k in required if str(cfg.get(k, "")).strip() == ""]
    if missing:
        raise ValueError(f"缺少必要配置字段: {', '.join(missing)}")

    df = load_trace_table(
        str(cfg["input_dir"]),
        str(cfg["excel_base"]),
        str(cfg["outcrop_name"]),
    )
    ang0, n, XY, joint_strike_deg = parse_trace_table(df)
    return ParsedTraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
        joint_strike_deg=joint_strike_deg,
    )
