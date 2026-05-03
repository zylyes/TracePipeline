"""迹线数据输入输出 — Excel 读取、结果写入与文件发现。

统一管理所有 Excel I/O 操作和输入文件扫描：
  - read_trace_excel: 读取原始迹线表
  - parse_trace_file: 加载并解析为 TraceData
  - build_excel_sections / write_excel_sections: 四区布局写入
  - find_trace_tables: 扫描输入目录发现迹线表文件
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

from .types import TraceData

logger = logging.getLogger(__name__)

# ===========================================================================
# 文件发现常量
# ===========================================================================

EXCEL_EXTENSIONS: Tuple[str, ...] = (".xlsx", ".xls")
TRACE_SUFFIX = "_process"

# ===========================================================================
# 布局常量（输出 Excel 四区布局）
# ===========================================================================

_BASE_INFO_ROW = 0       # 基本信息起始行
_DATA_GAP = 3             # 基本信息与数据区之间的行间隔
_RAW_COL_START = 0        # 原始坐标起始列
_ROT_COL_START = 6        # 旋转坐标起始列
_ORIENT_COL_START = 12    # 走向与长度起始列
_COLUMN_WIDTH = 14        # 统一列宽


# ===========================================================================
# 读取
# ===========================================================================


def read_trace_excel(
    base_path: str,
    table_stem: str,
    sheet: str | None = None,
) -> pd.DataFrame:
    """读取迹线 Excel 表，优先 .xlsx，缺失则回退 .xls。

    Args:
        base_path: 输入目录路径。
        table_stem: 不含扩展名的文件名。
        sheet: 工作表名；为 None 或不存在时回退到第一个 sheet。

    Returns:
        无表头的原始 DataFrame。

    Raises:
        FileNotFoundError: .xlsx 与 .xls 均不存在。
    """
    base = Path(base_path)
    candidates = [
        (base / f"{table_stem}.xlsx", "openpyxl"),
        (base / f"{table_stem}.xls", "xlrd"),
    ]

    last_error: Exception | None = None
    for path, engine in candidates:
        if not path.is_file():
            continue
        logger.debug("读取文件: %s (引擎=%s)", path, engine)
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet or 0, header=None)
        except ValueError:
            # 工作表名不存在 → 回退到第一个 sheet
            logger.debug("工作表 '%s' 不存在，回退到第一个 sheet", sheet)
            try:
                return pd.read_excel(path, engine=engine, sheet_name=0, header=None)
            except Exception as exc:
                logger.warning("读取 %s 失败 (%s)，尝试下一格式", path, exc)
                last_error = exc
                continue
        except Exception as exc:
            logger.warning("读取 %s 失败 (%s)，尝试下一格式", path, exc)
            last_error = exc
            continue

    raise FileNotFoundError(
        f"在 {base_path} 下未找到 {table_stem}.xlsx 或 {table_stem}.xls"
    ) from last_error


def parse_trace_file(
    input_dir: str,
    table_stem: str,
    outcrop: str,
) -> TraceData:
    """加载并解析迹线表，返回 TraceData。

    组合 read_trace_excel + compute_endpoints 两个阶段。
    """
    from .geometry import compute_endpoints

    logger.info("加载迹线数据: %s/%s", input_dir, table_stem)
    df = read_trace_excel(input_dir, table_stem, outcrop)

    ang0, n, XY, joint_strike = compute_endpoints(df)

    if n:
        avg_len = float(np.hypot(XY[:, 2] - XY[:, 0], XY[:, 3] - XY[:, 1]).mean())
    else:
        avg_len = 0.0
    logger.info("解析完成: %d 条迹线, 走向 %.1f°, 平均迹长 %.2f", n, ang0, avg_len)

    return TraceData(
        scanline_azimuth=ang0,
        count=n,
        endpoints=XY,
        joint_strikes=joint_strike,
    )


# ===========================================================================
# 写入
# ===========================================================================


def build_excel_sections(
    trace: TraceData,
    rotated_xy: np.ndarray,
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

    # 区域 D：节理走向 + 迹线长度
    orient_df = pd.DataFrame({
        "节理走向(°)": np.round(trace.joint_strikes, 2),
        "迹线长度": np.round(trace.lengths, 4),
    })

    data_row = _BASE_INFO_ROW + _DATA_GAP
    return [
        (base_info, _BASE_INFO_ROW, _RAW_COL_START, True),
        (raw_df, data_row, _RAW_COL_START, True),
        (rot_df, data_row, _ROT_COL_START, True),
        (orient_df, data_row, _ORIENT_COL_START, True),
    ]


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

        # 动态调整列宽（使用 openpyxl API 支持 >26 列）
        ws = writer.sheets[sheet_name]
        for col_idx in range(max_col):
            col_letter = get_column_letter(col_idx + 1)
            ws.column_dimensions[col_letter].width = _COLUMN_WIDTH

    logger.debug("Excel 写入完成: %s", excel_path)


def find_trace_tables(
    input_dir: str,
    suffix: str = TRACE_SUFFIX,
    extensions: Tuple[str, ...] = EXCEL_EXTENSIONS,
) -> List[Tuple[str, str]]:
    """扫描输入目录，返回匹配的迹线表列表 [(table_stem, outcrop), ...]。

    匹配规则：
      - 文件名以 suffix 结尾（不含扩展名）
      - 扩展名在 extensions 集合中
      - 同名文件（不同扩展名）按首次发现去重（大小写不敏感）

    Returns:
        按 outcrop 排序的列表；目录不存在或无匹配时返回空列表。
    """
    path = Path(input_dir)
    if not path.is_dir():
        logger.warning("输入目录不存在: %s", input_dir)
        return []

    matched: dict = {}
    for ext in extensions:
        for file_path in sorted(path.glob(f"*{suffix}{ext}")):
            stem = file_path.stem
            key = stem.lower()
            if key not in matched:
                outcrop = stem[: -len(suffix)] if stem.endswith(suffix) else stem
                matched[key] = (stem, outcrop)

    result = [matched[k] for k in sorted(matched)]
    if result:
        logger.info("发现 %d 个迹线表: %s", len(result), ", ".join(b for b, _ in result))
    else:
        logger.warning("在 %s 中未发现匹配的迹线表（后缀=%s）", input_dir, suffix)
    return result


__all__ = [
    "build_excel_sections",
    "find_trace_tables",
    "parse_trace_file",
    "read_trace_excel",
    "write_excel_sections",
]
