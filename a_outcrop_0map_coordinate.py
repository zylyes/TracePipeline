import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Tuple

from coordinate import coordinate


def _to_strike_from_dip_direction(dd: float) -> float:
    """
    倾向(方向) → 走向的转换，与 MATLAB 中的规则一致：
    if dd>=270: strike = dd+90-360
    elif dd>=180: strike = dd-90
    elif dd>=90: strike = dd-90
    else: strike = dd+90
    """
    if dd >= 270:
        return dd + 90 - 360
    elif dd >= 180:
        return dd - 90
    elif dd >= 90:
        return dd - 90
    else:
        return dd + 90


def main():
    # 路径设置（尽量兼容原工程路径，不存在则使用当前工作目录）
    path1 = r"D:\作业\毕业论文\周咏霖"
    path3 = r"D:\作业\毕业论文\周咏霖"
    path2 = os.getcwd()

    if not os.path.isdir(path1):
        path1 = path2
    if not os.path.isdir(path3):
        path3 = path2

    file_name = "Outcrop"
    excel_base = "O76_process"
    outcrop_name = "O76"

    # 读取 Excel（优先 .xlsx，回退 .xls）
    os.chdir(path1)
    excel_path_xlsx = os.path.join(path1, excel_base + ".xlsx")
    excel_path_xls = os.path.join(path1, excel_base + ".xls")

    def _read_excel_with_sheet(path: str, engine: str) -> pd.DataFrame:
        try:
            # 优先读取指定工作表；header=None 保证“第一行”即为数据第一行
            return pd.read_excel(path, engine=engine, sheet_name=outcrop_name, header=None)
        except ValueError:
            # 指定工作表不存在时，回退到首个工作表
            return pd.read_excel(path, engine=engine, sheet_name=0, header=None)

    if os.path.exists(excel_path_xlsx):
        df = _read_excel_with_sheet(excel_path_xlsx, engine="openpyxl")
    elif os.path.exists(excel_path_xls):
        df = _read_excel_with_sheet(excel_path_xls, engine="xlrd")
    else:
        raise FileNotFoundError(f"未找到 {excel_base}.xlsx 或 {excel_base}.xls 在路径: {path1}")

    # MATLAB 索引为 1 基，这里转换为 0 基
    ang0 = float(df.iloc[0, 7])  # 第 8 列：露头测线走向
    n_raw = df.iloc[0, 8]
    n_num = pd.to_numeric([n_raw], errors='coerce')[0]
    if np.isnan(n_num):
        raise ValueError(f"第1行第9列无法解析为数字，实际值: {n_raw!r}")
    n = int(n_num)

    # M = 位置、倾向(后改为走向)、迹长等参数：前 7 列
    M = df.iloc[:, 0:7].to_numpy(dtype=float)

    # dd = 倾向（第 3 列，索引 2） → 走向
    dd = df.iloc[:, 2].to_numpy(dtype=float)
    strike_angles = np.array([_to_strike_from_dip_direction(x) for x in dd])
    # 替换 M 的第 3 列为走向（索引 2）
    M[:, 2] = strike_angles[:M.shape[0]]

    # 计算端点坐标
    XY = np.zeros((n, 4), dtype=float)
    trace_lengths = np.zeros((n,), dtype=float)
    trace_angles = np.zeros((n,), dtype=float)

    for m in range(n):
        trace_lengths[m] = M[m, 4] + M[m, 6]
        trace_angles[m] = M[m, 2]
        X1, Y1, X2, Y2 = coordinate(
            ang0,
            M[m, 0], M[m, 1], M[m, 2], M[m, 3], M[m, 4], M[m, 5], M[m, 6]
        )
        XY[m, :] = [X1, Y1, X2, Y2]

    # 绘制裂缝底图（用 NaN 分段绘制）
    X = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()

    plt.figure(figsize=(24/2.54, 12/2.54), dpi=200)
    plt.plot(X, Y, '-', color=(0, 0, 0), linewidth=1)
    plt.axis('equal')
    ax = plt.gca()
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    try:
        ax.set_fontname('Times New Roman')
    except Exception:
        pass

    # 导出 Excel（Outcrop.xlsx, 指定 Sheet 与 A1）
    os.makedirs(path3, exist_ok=True)
    excel_out = os.path.join(path3, f"{file_name}.xlsx")
    with pd.ExcelWriter(excel_out, engine="openpyxl") as writer:
        # 写入一个仅包含 n 的 DataFrame 到指定单元起始位置
        out_df = pd.DataFrame([n])
        out_df.to_excel(writer, sheet_name=outcrop_name, index=False, header=False, startrow=0, startcol=0)
        # 追加写出计算得到的端点坐标表（X1, Y1, X2, Y2），方便检查
        xy_df = pd.DataFrame(XY, columns=["X1", "Y1", "X2", "Y2"])
        xy_df.to_excel(writer, sheet_name=outcrop_name, index=False, startrow=2, startcol=0)

    # 导出图片 PNG
    imagename = f"{outcrop_name}({n}).png"
    image_save_path = os.path.join(path3, imagename)

    ax.set_facecolor('white')
    fig = plt.gcf()
    fig.patch.set_facecolor('white')
    plt.tight_layout()
    plt.savefig(image_save_path, dpi=300, facecolor='white')

    # 收尾
    os.chdir(path2)
    plt.close(fig)


if __name__ == "__main__":
    main()
