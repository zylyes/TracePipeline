# 功能：读取迹线数据，绘制原始与旋转后的迹线图，并在一次运行中导出 Excel 与 PNG 结果。
import os
import matplotlib.pyplot as plt
from settings import load_config
from trace_plotting import build_nan_separated_lines, style_trace_axes
from trace_io import find_trace_tables, ensure_io_paths
from trace_transform import normalize_and_rotate_lines
from trace_processing import (
    build_excel_sections,
    export_figure,
    load_trace_data,
    write_excel_sections,
)


def render_trace_plot(X_plot, Y_plot, title: str, output_dir: str, filename: str, dpi: int = 300):
    """绘制单张迹线图并导出到指定目录。"""
    fig = plt.figure(figsize=(24 / 2.54, 12 / 2.54), dpi=dpi)
    ax = fig.gca()
    ax.plot(X_plot, Y_plot, "-", color=(0, 0, 0), linewidth=1)
    ax = style_trace_axes(ax)
    ax.set_title(title, fontsize=12, fontname="Times New Roman")
    export_figure(fig, output_dir, filename, dpi=dpi)
    plt.close(fig)


def main(cfg: dict | None = None):
    cfg = cfg or load_config()

    input_dir, output_dir, _ = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    discovered = find_trace_tables(input_dir)
    targets = discovered if (cfg.get("process_all") and discovered) else [(cfg["excel_base"], cfg["outcrop_name"])]

    for excel_base, outcrop_name in targets:
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        trace, paths = load_trace_data(run_cfg)

        rotated = normalize_and_rotate_lines(trace.xy, trace.strike_deg)
        X_raw, Y_raw = build_nan_separated_lines(trace.xy)
        X_rot, Y_rot = build_nan_separated_lines(rotated)

        excel_out = os.path.join(paths.output_dir, f"{run_cfg['file_name']}_traces.xlsx")
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(excel_out, run_cfg["outcrop_name"], sections)

        raw_title = f"Trace length map (number={trace.trace_count})"
        raw_name = f"{run_cfg['outcrop_name']}_raw(n={trace.trace_count}).png"
        render_trace_plot(X_raw, Y_raw, raw_title, paths.output_dir, raw_name, dpi=300)

        rot_title = f"Trace length map (number={trace.trace_count})\nScaline (strike={trace.strike_deg})"
        rot_name = f"{run_cfg['outcrop_name']}_rotated(strike={trace.strike_deg}).png"
        render_trace_plot(X_rot, Y_rot, rot_title, paths.output_dir, rot_name, dpi=600)

        print(f"Processed {excel_base} -> {excel_out} and figures in {paths.output_dir}")


if __name__ == "__main__":
    main()
