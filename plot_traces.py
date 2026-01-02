# 功能：读取迹线数据，绘制原始与旋转后的迹线图，并在一次运行中导出 Excel 与 PNG 结果。
import os
import pandas as pd
import matplotlib.pyplot as plt
from settings import RunConfig, default_config
from trace_utils import build_polyline_arrays, style_trace_axes
from rotation import rotate_lines
from trace_pipeline import (
    build_excel_sections,
    export_figure,
    load_trace_data,
    write_excel_sections,
)


def _render_trace_plot(X_plot, Y_plot, title: str, output_dir: str, filename: str, dpi: int = 300):
    """绘制单张迹线图并导出到指定目录。"""
    fig = plt.figure(figsize=(24 / 2.54, 12 / 2.54), dpi=dpi)
    ax = fig.gca()
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    ax = style_trace_axes(ax)
    ax.set_title(title, fontsize=12, fontname="Times New Roman")
    export_figure(fig, output_dir, filename, dpi=dpi)
    plt.close(fig)


def main(cfg: RunConfig | None = None):
    cfg = cfg or default_config()
    trace, paths = load_trace_data(cfg)

    rotated = rotate_lines(trace.xy, trace.strike_deg)
    X_raw, Y_raw = build_polyline_arrays(trace.xy)
    X_rot, Y_rot = build_polyline_arrays(rotated)

    excel_out = os.path.join(paths.output_dir, f"{cfg.file_name}_traces.xlsx")
    sections = build_excel_sections(trace, rotated)
    write_excel_sections(excel_out, cfg.outcrop_name, sections)

    raw_title = f"Trace length map (number={trace.trace_count})"
    raw_name = f"{cfg.outcrop_name}_raw(n={trace.trace_count}).png"
    _render_trace_plot(X_raw, Y_raw, raw_title, paths.output_dir, raw_name, dpi=300)

    rot_title = f"Trace length map (number={trace.trace_count})\nScaline (strike={trace.strike_deg})"
    rot_name = f"{cfg.outcrop_name}_rotated(strike={trace.strike_deg}).png"
    _render_trace_plot(X_rot, Y_rot, rot_title, paths.output_dir, rot_name, dpi=600)


if __name__ == "__main__":
    main()
