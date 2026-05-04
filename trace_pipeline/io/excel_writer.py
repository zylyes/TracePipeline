"""Excel 结果写入 — 四区布局与节的构造。

Excel 布局（单工作表内）:
  区域 A（基本信息）          —— 顶部 1 行
  区域 B（原始端点坐标）       ┐
  区域 C（旋转后端点坐标）     ├─ 均从 data_row 开始，横向排列
  区域 D（节理走向 + 迹线长度）┘
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

from ..models import TraceData

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_LAYOUT",
    "ExcelLayout",
    "build_excel_sections",
    "write_excel_sections",
]


@dataclass(frozen=True)
class ExcelLayout:
    """Excel 输出工作表的布局规格。"""
    base_info_row: int = 0
    data_gap: int = 3
    raw_col_start: int = 0
    rot_col_start: int = 6
    orient_col_start: int = 12
    column_width: int = 14


DEFAULT_LAYOUT = ExcelLayout()


def build_excel_sections(
    trace: TraceData,
    rotated_xy: np.ndarray,
    layout: ExcelLayout = DEFAULT_LAYOUT,
) -> List[Tuple[pd.DataFrame, int, int, bool]]:
    """由 TraceData 与旋转后坐标构建四个导出区域。

    Returns:
        [(df, startrow, startcol, header), ...] 共 4 个区域。
    """
    if rotated_xy.shape != trace.endpoints.shape:
        raise ValueError(
            f"旋转坐标形状 {rotated_xy.shape} 与原始坐标 {trace.endpoints.shape} 不一致"
        )
    if not np.isfinite(rotated_xy).all():
        raise ValueError("旋转坐标包含 NaN 或 inf")

    avg_len = trace.mean_length

    # 区域 A：基本信息
    base_info = pd.DataFrame({
        "测线走向(°)": [round(trace.scanline_azimuth, 2)],
        "迹线数量": [trace.count],
        "平均迹线长度": [round(avg_len, 4)],
    })

    # 区域 B：原始端点坐标
    raw_df = pd.DataFrame(
        trace.endpoints,
        columns=["起点X", "起点Y", "终点X", "终点Y"],
    )

    # 区域 C：旋转后坐标
    rot_df = pd.DataFrame(
        rotated_xy,
        columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"],
    )

    # 区域 D：节理走向 + 端点距离 + 测段长度(r5+r7)
    orient_df = pd.DataFrame({
        "节理走向(°)": np.round(trace.joint_strikes, 2),
        "端点距离": np.round(trace.lengths, 4),
        "测段长度(r5+r7)": np.round(trace.segment_lengths, 4),
    })

    data_row = layout.base_info_row + layout.data_gap
    return [
        (base_info, layout.base_info_row, layout.raw_col_start, True),
        (raw_df, data_row, layout.raw_col_start, True),
        (rot_df, data_row, layout.rot_col_start, True),
        (orient_df, data_row, layout.orient_col_start, True),
    ]


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[Tuple[pd.DataFrame, int, int, bool]],
    layout: ExcelLayout = DEFAULT_LAYOUT,
) -> None:
    """将多个 DataFrame 按指定位置写入同一 sheet。

    Args:
        excel_path: 输出 Excel 文件路径。
        sheet_name: 工作表名称。
        sections: [(df, startrow, startcol, include_header), ...] 序列。
        layout: 布局规格（用于列宽）。
    """
    output_dir = os.path.dirname(excel_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    max_col = 0
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
            max_col = max(max_col, startcol + df.shape[1])

        ws = writer.sheets[sheet_name]
        for col_idx in range(max_col):
            col_letter = get_column_letter(col_idx + 1)
            ws.column_dimensions[col_letter].width = layout.column_width

    logger.debug("Excel 写入完成: %s", excel_path)
