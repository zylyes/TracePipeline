"""Excel 输出相关工具。

提供将多个 pandas DataFrame 写入同一工作表不同区域的能力，
以及根据 ParsedTraceData 组装需要写入的表格片段（分区）。
"""
from __future__ import annotations

import os
from typing import Sequence, Tuple
import pandas as pd
import numpy as np

from trace_pipeline.data_loader import ParsedTraceData


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[Tuple[pd.DataFrame, int, int, bool]],
):
    """将多个 DataFrame 写入同一工作表的不同区域。"""

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


def build_excel_sections(trace: ParsedTraceData, rotated_xy: np.ndarray) -> Sequence[Tuple[pd.DataFrame, int, int, bool]]:
    """组装 Excel 写入所需的分块信息。"""

    # 第一块：基本信息（走向与数量）
    base_info = pd.DataFrame({"测线走向(°)": [trace.strike_deg], "迹线数量": [trace.trace_count]})
    # 第二块：原始端点坐标，每行 [起点X, 起点Y, 终点X, 终点Y]
    raw_df = pd.DataFrame(trace.xy, columns=["起点X", "起点Y", "终点X", "终点Y"])
    # 第三块：旋转/平移后的坐标，便于后续可视化或量算比对
    rot_df = pd.DataFrame(rotated_xy, columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"])
    # 返回一个列表，每个元素为 (DataFrame, startrow, startcol, include_header)
    return [
        (base_info, 0, 0, True),
        (raw_df, 3, 0, True),
        (rot_df, 3, 6, True),
    ]
