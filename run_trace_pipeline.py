"""迹线处理脚本：读取 Excel、计算几何、导出表格与图片。"""
from __future__ import annotations # 类型注解延迟加载

from pathlib import Path
from typing import Dict

from trace_pipeline.config import ensure_io_paths, find_trace_tables, load_config
from trace_pipeline.data_loader import ParsedTraceData, load_trace_data
from trace_pipeline.excel_export import build_excel_sections, write_excel_sections
from trace_pipeline.plotting import build_nan_lines, render_trace_plot
from trace_pipeline.transforms import norm_rotate_lines


def process_target(run_cfg: Dict) -> dict:
    """处理单个迹线表：生成 Excel 与图片并返回摘要信息。"""

    # 读取并解析 Excel 数据，得到端点坐标与走向
    trace: ParsedTraceData = load_trace_data(run_cfg)

    # 坐标平移+旋转，构造绘图序列
    rotated = norm_rotate_lines(trace.xy, trace.strike_deg)
    X_raw, Y_raw = build_nan_lines(trace.xy)
    X_rot, Y_rot = build_nan_lines(rotated)

    # 生成 Excel 输出并写入
    excel_out = Path(run_cfg["output_dir"]) / f"{run_cfg['file_name']}_traces.xlsx"
    sections = build_excel_sections(trace, rotated)
    write_excel_sections(str(excel_out), run_cfg["outcrop_name"], sections)

    # 绘制原始与旋转后的迹线图
    raw_title = f"迹线长度图（数量={trace.trace_count}）"
    raw_name = f"{run_cfg['outcrop_name']}_raw(n={trace.trace_count}).png"
    render_trace_plot(X_raw, Y_raw, raw_title, run_cfg["output_dir"], raw_name, dpi=300)

    rot_title = f"迹线长度图（数量={trace.trace_count}）\n标尺（走向={trace.strike_deg}）"
    rot_name = f"{run_cfg['outcrop_name']}_rotated(strike={trace.strike_deg}).png"
    render_trace_plot(X_rot, Y_rot, rot_title, run_cfg["output_dir"], rot_name, dpi=600)

    return {
        "excel_base": run_cfg["excel_base"],
        "excel_out": str(excel_out),
        "trace_count": trace.trace_count,
    }


def main(cfg: dict | None = None):
    cfg = cfg or load_config()

    # 校验输入/输出路径并确定待处理的 Excel 列表
    input_dir, output_dir = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    discovered = find_trace_tables(input_dir)
    targets = discovered if (cfg.get("process_all") and discovered) else [(cfg["excel_base"], cfg["outcrop_name"])]

    print(f"输入目录：{input_dir}", flush=True)
    print(f"输出目录：{output_dir}", flush=True)
    print(f"待处理文件数：{len(targets)}", flush=True)

    run_summaries: list[dict] = []

    for idx, (excel_base, outcrop_name) in enumerate(targets, start=1):
        # 合并运行时配置，方便传递给后续函数
        run_cfg = {
            **cfg,
            "input_dir": input_dir,
            "output_dir": output_dir,
            "file_name": outcrop_name,
            "excel_base": excel_base,
            "outcrop_name": outcrop_name,
        }

        summary = process_target(run_cfg)
        run_summaries.append(summary)

        print(
            f"[{idx}/{len(targets)}] 已处理 {excel_base} -> {summary['excel_out']} (迹线数={summary['trace_count']})",
            flush=True,
        )

    if not run_summaries:
        print(f"未找到可处理的文件，请检查输入目录：{input_dir}", flush=True)
        return

    print(f"处理完成，文件数：{len(run_summaries)}", flush=True)


if __name__ == "__main__":
    main()
