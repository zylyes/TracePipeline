# 功能：统一处理路径解析、数据加载、Excel 分区写入与图像导出。
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Sequence, Tuple
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from trace_io import ensure_io_paths, load_trace_table
from trace_geometry import parse_trace_table


@dataclass
class TraceData:
    """用于在管线中传递的迹线数据包。"""

    strike_deg: float  # 测线走向角度
    trace_count: int  # 迹线数量
    xy: np.ndarray  # 每条迹线两端点坐标 (n, 4)
    trace_lengths: np.ndarray  # 每条迹线长度
    trace_angles: np.ndarray  # 每条迹线走向角度


@dataclass
class PathContext:
    """保存输入、输出和当前工作目录，避免散落字符串。"""

    input_dir: str
    output_dir: str
    cwd: str


@contextmanager
def working_directory(path: str):
    """临时切换工作目录，退出上下文后自动还原。"""
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def load_trace_data(cfg: dict) -> tuple[TraceData, PathContext]:
    """读取 Excel 表并封装成 TraceData，同时返回路径上下文。"""
    input_dir, output_dir, cwd = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    with working_directory(input_dir):
        df = load_trace_table(input_dir, cfg["excel_base"], cfg["outcrop_name"])
        ang0, n, XY, trace_lengths, trace_angles = parse_trace_table(df)

    trace = TraceData(
        strike_deg=ang0,
        trace_count=n,
        xy=XY,
        trace_lengths=trace_lengths,
        trace_angles=trace_angles,
    )
    paths = PathContext(input_dir=input_dir, output_dir=output_dir, cwd=cwd)
    return trace, paths


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


def build_excel_sections(trace: TraceData, rotated_xy: np.ndarray) -> Sequence[Tuple[pd.DataFrame, int, int, bool]]:
    """组装 Excel 写入所需的分块信息，便于复用。"""
    base_info = pd.DataFrame({"strike_deg": [trace.strike_deg], "trace_count": [trace.trace_count]})
    raw_df = pd.DataFrame(trace.xy, columns=["X1", "Y1", "X2", "Y2"])
    rot_df = pd.DataFrame(rotated_xy, columns=["RX1", "RY1", "RX2", "RY2"])
    return [
        (base_info, 0, 0, True),
        (raw_df, 3, 0, True),
        (rot_df, 3, 6, True),
    ]


def export_figure(fig: Figure, output_dir: str, filename: str, dpi: int = 300) -> str:
    """导出图片到输出目录并返回完整路径。"""
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(full_path, dpi=dpi, facecolor="white")
    return full_path
