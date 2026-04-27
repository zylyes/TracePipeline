"""Excel 输出构建与写入。

将 ParsedTraceData 拆分为四个区域写入同一个工作表：
  A. 基本信息（走向、数量、平均长度）
  B. 原始端点坐标
  C. 旋转后端点坐标
  D. 节理走向与迹线长度

布局约定（单工作表）:
  - 基本信息从 A1 开始
  - 数据区从第 4 行开始，分三列并排：
    Cols 0-3:  原始坐标    | Cols 6-9:  旋转坐标    | Cols 12-13: 走向与长度
"""
from __future__ import annotations

import logging
import os
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd

from .data_loader import ParsedTraceData

logger = logging.getLogger(__name__)

__all__ = [
    "build_excel_sections",
    "write_excel_sections",
]

# ---------------------------------------------------------------------------
# 布局常量（startrow, startcol, header）
# ---------------------------------------------------------------------------

# 基本信息区
_BASE_INFO_ROW = 0
_BASE_INFO_COL = 0
_BASE_INFO_GAP = 3  # 基本信息与数据区之间的行间隔

# 数据区列起始
_RAW_COL_START = 0      # 原始坐标
_ROT_COL_START = 6      # 旋转坐标
_ORIENT_COL_START = 12  # 走向与长度

# 列宽调整（用于提升可读性）
_COLUMN_WIDTH = 14


# ---------------------------------------------------------------------------
# 写入
# ---------------------------------------------------------------------------


def write_excel_sections(
    excel_path: str,
    sheet_name: str,
    sections: Sequence[Tuple[pd.DataFrame, int, int, bool]],
) -> None:
    """将多个 DataFrame 按指定位置写入同一 sheet。

    Args:
        excel_path: 输出 Excel 文件路径。
        sheet_name: 工作表名称。
        sections: [(df, startrow, startcol, include_header), ...] 序列。

    Raises:
        OSError: 目录创建或文件写入失败。
    """
    output_dir = os.path.dirname(excel_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

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

        # 调整列宽
        ws = writer.sheets[sheet_name]
        for col_idx in range(14):  # 0-13 列
            col_letter = chr(ord("A") + col_idx)
            ws.column_dimensions[col_letter].width = _COLUMN_WIDTH

    logger.debug("Excel 写入完成: %s", excel_path)


# ---------------------------------------------------------------------------
# 组装
# ---------------------------------------------------------------------------


def build_excel_sections(
    trace: ParsedTraceData,
    rotated_xy: np.ndarray,
) -> List[Tuple[pd.DataFrame, int, int, bool]]:
    """由 ParsedTraceData 与旋转后坐标构建四个导出区域。

    Args:
        trace: 解析后的迹线数据。
        rotated_xy: 旋转后的端点坐标 (N, 4)。

    Returns:
        [(df, startrow, startcol, header), ...] 列表，共 4 个区域。

    Raises:
        ValueError: 当 rotated_xy 形状与 trace.xy 不一致时。
    """
    if rotated_xy.shape != trace.xy.shape:
        raise ValueError(
            f"旋转坐标形状 {rotated_xy.shape} 与原始坐标 {trace.xy.shape} 不一致"
        )
    if not np.isfinite(rotated_xy).all():
        raise ValueError("旋转坐标包含 NaN 或 inf")

    avg_len = float(trace.trace_lengths.mean()) if trace.trace_count else 0.0

    # ---- 区域 A：基本信息 ----
    base_info = pd.DataFrame({
        "测线走向(°)": [round(trace.strike_deg, 2)],
        "迹线数量": [trace.trace_count],
        "平均迹线长度": [round(avg_len, 4)],
    })

    # ---- 区域 B：原始端点坐标 ----
    raw_df = pd.DataFrame(
        trace.xy,
        columns=["起点X", "起点Y", "终点X", "终点Y"],
    )

    # ---- 区域 C：旋转后坐标 ----
    rot_df = pd.DataFrame(
        rotated_xy,
        columns=["旋转后起点X", "旋转后起点Y", "旋转后终点X", "旋转后终点Y"],
    )

    # ---- 区域 D：节理走向 + 迹线长度 ----
    orient_df = pd.DataFrame({
        "节理走向(°)": np.round(trace.joint_strike_deg, 2),
        "迹线长度": np.round(trace.trace_lengths, 4),
    })

    data_row = _BASE_INFO_ROW + _BASE_INFO_GAP
    return [
        (base_info, _BASE_INFO_ROW, _BASE_INFO_COL, True),
        (raw_df, data_row, _RAW_COL_START, True),
        (rot_df, data_row, _ROT_COL_START, True),
        (orient_df, data_row, _ORIENT_COL_START, True),
    ]
