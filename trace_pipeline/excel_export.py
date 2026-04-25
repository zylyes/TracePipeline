"""Excel 输出构建与写入。

将 ParsedTraceData 拆分为四个区域写入同一个工作表：
- 基本信息（走向、数量、平均长度）
- 原始端点坐标
- 旋转后端点坐标
- 节理走向与迹线长度
"""
from __future__ import annotations

import os
from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from trace_pipeline.data_loader import ParsedTraceData

# ---------------------------------------------------------------------------
# 布局常量（startrow, startcol）
# ---------------------------------------------------------------------------

_BASE_INFO_ROW, _BASE_INFO_COL = 0, 0
_BASE_INFO_GAP = 3  # 基本信息与数据块之间的行间隔

_RAW_COL_START = 0
_ROT_COL_START = 6
_ORIENT_COL_START = 12


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[Tuple[pd.DataFrame, int, int, bool]],
) -> None:
    """将多个 DataFrame 按指定位置写入同一工作表的同一 sheet。"""
    os.makedirs(os.path.dirname(excel_path) or ".", exist_ok=True)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for df, startrow, startcol, header in sections:
            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
                header=header,
                startrow=startrow,
                startcol=startcol,
            )


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------


def build_excel_sections(
    trace: ParsedTraceData,
    rotated_xy: np.ndarray,
) -> Sequence[Tuple[pd.DataFrame, int, int, bool]]:
    """由 ParsedTraceData 与旋转后坐标构建四个导出区域。

    Raises:
        ValueError: 当 rotated_xy 形状与 trace.xy 不一致时。
    """
    if rotated_xy.shape != trace.xy.shape:
        raise ValueError(
            f"旋转坐标形状 {rotated_xy.shape} 与原始坐标 {trace.xy.shape} 不一致"
        )

    avg_len = float(trace.trace_lengths.mean()) if trace.trace_count else 0.0

    # 区域 A：基本信息
    base_info = pd.DataFrame({
        "测线走向(°)": [trace.strike_deg],
        "迹线数量": [trace.trace_count],
        "平均迹线长度": [avg_len],
    })

    # 区域 B：原始端点坐标
    raw_df = pd.DataFrame(
        trace.xy,
        columns=["起点X", "起点Y", "终点X", "终点Y"],
    )

    # 区域 C：旋转后坐标
    rot_df = pd.DataFrame(
        rotated_xy,
        columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"],
    )

    # 区域 D：节理走向 + 迹线长度
    orient_df = pd.DataFrame({
        "节理走向(°)": trace.joint_strike_deg,
        "迹线长度": trace.trace_lengths,
    })

    data_row = _BASE_INFO_ROW + _BASE_INFO_GAP
    return [
        (base_info, _BASE_INFO_ROW, _BASE_INFO_COL, True),
        (raw_df, data_row, _RAW_COL_START, True),
        (rot_df, data_row, _ROT_COL_START, True),
        (orient_df, data_row, _ORIENT_COL_START, True),
    ]
