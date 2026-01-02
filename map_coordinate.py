import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt # 导入绘图库

from map_utils import (
    resolve_paths,
    read_trace_table,
    parse_trace_geometry,
    build_polyline_arrays,
    style_trace_axes,
)


def main():
    path1_default = r"D:\作业\毕业论文\周咏霖\input"
    path3_default = r"D:\作业\毕业论文\周咏霖\output"
    path1, path3, path2 = resolve_paths(path1_default, path3_default)

    file_name = "Outcrop"
    excel_base = "O76_process"
    outcrop_name = "O76"

    os.chdir(path1)
    df = read_trace_table(path1, excel_base, outcrop_name)
    ang0, n, XY, trace_lengths, trace_angles = parse_trace_geometry(df)
    X, Y = build_polyline_arrays(XY)

    plt.figure(figsize=(24/2.54, 12/2.54), dpi=200)
    plt.plot(X, Y, '-', color=(0, 0, 0), linewidth=1)
    ax = style_trace_axes(plt.gca())
    fig = ax.get_figure()

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

    plt.tight_layout()
    plt.savefig(image_save_path, dpi=300, facecolor='white')

    # 收尾
    os.chdir(path2)
    plt.close(fig)


if __name__ == "__main__":
    main()
