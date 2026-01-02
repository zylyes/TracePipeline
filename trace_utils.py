# 功能：提供路径解析、迹线表读取与几何计算工具函数。
import os # 操作系统接口模块
import numpy as np # 数值计算模块
import pandas as pd # 数据处理模块
import matplotlib.pyplot as plt # 绘图库
from typing import Tuple, List # 类型提示模块
from coordinate_math import coordinate # 导入坐标转换函数


def resolve_paths(input_dir: str, output_dir: str) -> Tuple[str, str, str]:
    """返回可用的输入输出目录以及当前工作目录作为兜底。"""
    cwd = os.getcwd() # 当前工作目录
    in_dir = input_dir if os.path.isdir(input_dir) else cwd # 输入目录
    out_dir = output_dir if os.path.isdir(output_dir) else cwd # 输出目录
    return in_dir, out_dir, cwd # 返回路径元组


def discover_trace_tables(input_dir: str, suffix: str = "_process", extensions: Tuple[str, ...] = (".xlsx", ".xls")) -> List[Tuple[str, str]]:
    """在输入目录中查找符合命名规则的迹线表，返回 (excel_base, outcrop_name) 列表。

    - suffix: 例如 "_process"，用于从文件名提取区名。
    - extensions: 优先顺序，默认优先使用 .xlsx，其次 .xls。
    """

    if not os.path.isdir(input_dir):
        return []

    matched: dict[str, Tuple[str, str]] = {}
    files = sorted(os.listdir(input_dir))

    for ext in extensions:
        for name in files:
            if not name.lower().endswith(ext):
                continue

            base, _ = os.path.splitext(name)
            if not base.endswith(suffix):
                continue

            # 使用 lower 作为键，避免同名 xlsx/xls 重复。
            key = base.lower()
            if key in matched:
                continue

            outcrop_name = base[: -len(suffix)] if suffix and base.endswith(suffix) else base
            matched[key] = (base, outcrop_name)

    return list(matched.values())

def dip_to_strike(dd: float) -> float:
    """将倾向角转换为走向角，遵循原 MATLAB 规则。"""
    if dd >= 270: # 倾向角大于等于 270 度，转换为走向角
        return dd + 90 - 360
    if dd >= 180: # 倾向角大于等于 180 度，转换为走向角
        return dd - 90
    if dd >= 90: # 倾向角大于等于 90 度，转换为走向角
        return dd - 90
    return dd + 90


def read_trace_table(base_path: str, excel_base: str, sheet: str) -> pd.DataFrame:
    """读取断层迹线表，优先尝试 .xlsx，失败再回退到 .xls。"""
    excel_path_xlsx = os.path.join(base_path, excel_base + ".xlsx") # .xlsx 文件路径
    excel_path_xls = os.path.join(base_path, excel_base + ".xls") # .xls 文件路径

    def read(path: str, engine: str) -> pd.DataFrame:
        # 部分文件工作表命名不一致，先按指定名读，失败则退回第一个工作表
        try:
            return pd.read_excel(path, engine=engine, sheet_name=sheet, header=None)
        except ValueError:
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    if os.path.exists(excel_path_xlsx):
        return read(excel_path_xlsx, engine="openpyxl")
    if os.path.exists(excel_path_xls):
        return read(excel_path_xls, engine="xlrd")
    raise FileNotFoundError(f"未找到 {excel_base}.xlsx 或 {excel_base}.xls 在路径: {base_path}")


def parse_trace_geometry(df: pd.DataFrame) -> Tuple[float, int, np.ndarray, np.ndarray, np.ndarray]:
    """从原始表格提取起始方位、迹线数量，并计算端点坐标与角度。"""
    ang0 = float(df.iloc[0, 7])
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors="coerce")[0]
    if np.isnan(n_num):
        raise ValueError(f"第1行第9列无法解析为数字，实际值: {n_raw!r}")
    n = int(n_num)

    M = df.iloc[:, 0:7].to_numpy(dtype=float)
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([dip_to_strike(x) for x in dd])
    M[:, 2] = strike_angles[: M.shape[0]]

    XY = np.zeros((n, 4), dtype=float)
    trace_lengths = np.zeros((n,), dtype=float)
    trace_angles = np.zeros((n,), dtype=float)

    for m in range(n):
        trace_lengths[m] = M[m, 4] + M[m, 6]
        trace_angles[m] = M[m, 2]
        # coordinate 返回迹线两端点在平面直角坐标系下的坐标
        X1, Y1, X2, Y2 = coordinate(
            ang0,
            M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6],
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    return ang0, n, XY, trace_lengths, trace_angles


def build_polyline_arrays(XY: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """生成包含 NaN 间隔的坐标数组，便于用单条折线绘制多段。"""
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    """为迹线图设置统一的坐标轴样式。"""
    plt.axis("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    try:
        ax.set_fontname("Times New Roman")
    except Exception:
        pass
    ax.set_facecolor("white")
    fig = ax.get_figure()
    fig.patch.set_facecolor("white")
    return ax
