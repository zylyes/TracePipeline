"""迹线 Excel 读取与数据封装。"""
from __future__ import annotations

import os
from dataclasses import dataclass
import pandas as pd
import numpy as np

from trace_pipeline.geometry import parse_trace_table


@dataclass
class ParsedTraceData:
    strike_deg: float
    trace_count: int
    xy: np.ndarray


def load_trace_table(base_path: str, excel_base: str, sheet: str) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失时回退 .xls。"""

    excel_path_xlsx = os.path.join(base_path, excel_base + ".xlsx")
    excel_path_xls = os.path.join(base_path, excel_base + ".xls")

    def read(path: str, engine: str) -> pd.DataFrame:
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet, header=None)
        except ValueError:
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    if os.path.exists(excel_path_xlsx):
        return read(excel_path_xlsx, engine="openpyxl")
    if os.path.exists(excel_path_xls):
        return read(excel_path_xls, engine="xlrd")
    raise FileNotFoundError(f"Missing {excel_base}.xlsx or {excel_base}.xls under {base_path}")


def load_trace_data(cfg: dict) -> ParsedTraceData:
    """读取 Excel 表并封装 ParsedTraceData。"""

    df = load_trace_table(cfg["input_dir"], cfg["excel_base"], cfg["outcrop_name"])
    ang0, n, XY = parse_trace_table(df)

    return ParsedTraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
    )
