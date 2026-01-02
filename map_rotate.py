import os
import math
from typing import Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from map_utils import (
    resolve_paths,
    read_trace_table,
    parse_trace_geometry,
    style_trace_axes,
)


def _rotate_vector(x: float, y: float, rad: float) -> Tuple[float, float]:
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    return x * cos_a - y * sin_a, x * sin_a + y * cos_a


def _rotate_angle_from_strike(ang0: float) -> float:
    """Piecewise conversion that mirrors the MATLAB branch logic."""
    if ang0 > 270:
        return -(360 - ang0) * math.pi / 180.0
    if ang0 > 180:
        return (ang0 - 180) * math.pi / 180.0
    if ang0 > 90:
        return -(180 - ang0) * math.pi / 180.0
    return ang0 * math.pi / 180.0


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

    min_x = abs(np.round(np.min([XY[:, 0].min(), XY[:, 2].min()]))).astype(float) + 1.0
    min_y = abs(np.round(np.min([XY[:, 1].min(), XY[:, 3].min()]))).astype(float) + 1.0
    lines = np.column_stack([
        XY[:, 0] + min_x,
        XY[:, 1] + min_y,
        XY[:, 2] + min_x,
        XY[:, 3] + min_y,
    ])

    rotate_angle = _rotate_angle_from_strike(ang0)
    rot_lines = np.zeros_like(lines)
    for i in range(lines.shape[0]):
        rot_lines[i, 0:2] = _rotate_vector(lines[i, 0], lines[i, 1], rotate_angle)
        rot_lines[i, 2:4] = _rotate_vector(lines[i, 2], lines[i, 3], rotate_angle)

    min_rot_x = abs(np.round(np.min([rot_lines[:, 0].min(), rot_lines[:, 2].min()]))).astype(float)
    min_rot_y = abs(np.round(np.min([rot_lines[:, 1].min(), rot_lines[:, 3].min()]))).astype(float)
    rotate_lines = np.column_stack([
        rot_lines[:, 0] + min_rot_x,
        rot_lines[:, 1] + min_rot_y,
        rot_lines[:, 2] + min_rot_x,
        rot_lines[:, 3] + min_rot_y,
    ])

    n_lines = rotate_lines.shape[0]
    X_plot = np.column_stack([rotate_lines[:, 0], rotate_lines[:, 2], np.full((n_lines,), np.nan)]).ravel()
    Y_plot = np.column_stack([rotate_lines[:, 1], rotate_lines[:, 3], np.full((n_lines,), np.nan)]).ravel()

    plt.figure(figsize=(24 / 2.54, 12 / 2.54), dpi=300)
    plt.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    ax = style_trace_axes(plt.gca())
    plt.title(
        f"Trace length map (number={n})\nScaline (strike={ang0})",
        fontsize=12,
        fontname="Times New Roman",
    )

    os.makedirs(path3, exist_ok=True)
    excel_out = os.path.join(path3, f"{file_name}.xlsx")
    with pd.ExcelWriter(excel_out, engine="openpyxl") as writer:
        out_df = pd.DataFrame([ang0])
        out_df.to_excel(writer, sheet_name=outcrop_name, index=False, header=False, startrow=0, startcol=0)
        xy_df = pd.DataFrame(XY, columns=["X1", "Y1", "X2", "Y2"])
        xy_df.to_excel(writer, sheet_name=outcrop_name, index=False, startrow=2, startcol=0)
        rot_df = pd.DataFrame(rotate_lines, columns=["RX1", "RY1", "RX2", "RY2"])
        rot_df.to_excel(writer, sheet_name=outcrop_name, index=False, startrow=2, startcol=6)

    imagename = f"{outcrop_name}({ang0}).png"
    image_save_path = os.path.join(path3, imagename)
    plt.tight_layout()
    plt.savefig(image_save_path, dpi=600, facecolor="white")

    os.chdir(path2)
    plt.close()


if __name__ == "__main__":
    main()
