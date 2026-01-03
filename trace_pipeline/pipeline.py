"""迹线处理流水线：读取数据、生成 Excel 与图片。

此模块封装单个目标的完整处理流程：
1. 读取并解析 Excel，得到测线走向、迹线数量和端点坐标
2. 对坐标执行平移/旋转规范化以便绘图
3. 构造用于绘图的一维坐标序列并导出原始与旋转后的图片
4. 生成并写入 Excel 输出（包含原始坐标与旋转后坐标）

返回的字典包含运行摘要便于上层记录与统计。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from .data_loader import ParsedTraceData, load_trace_data
from .excel_export import build_excel_sections, write_excel_sections
from .plotting import build_nan_lines, render_trace_plot
from .transforms import norm_rotate_lines

logger = logging.getLogger(__name__)


def process_target(run_cfg: Dict) -> dict:
    """处理单个迹线表：生成 Excel 与图片并返回摘要信息。"""
    
    outcrop_name = run_cfg['outcrop_name']
    logger.info(f"开始处理: {outcrop_name}")

    try:
        # 1) 读取并解析 Excel 数据，得到端点坐标与测线走向（角度）
        trace: ParsedTraceData = load_trace_data(run_cfg)
        logger.debug(f"数据加载完成: {trace.trace_count} 条迹线, 走向 {trace.strike_deg}°")

        # 2) 对坐标进行标准化处理（先平移后旋转），便于绘图和对比
        rotated = norm_rotate_lines(trace.xy, trace.strike_deg)
        # 构造用于 matplotlib 的一维 X/Y 序列（包含 NaN 分隔）
        X_raw, Y_raw = build_nan_lines(trace.xy)
        X_rot, Y_rot = build_nan_lines(rotated)

        # 3) 生成并写入 Excel 输出（包含基本信息、原始坐标和旋转后坐标）
        output_dir = Path(run_cfg["output_dir"])
        excel_out = output_dir / f"{run_cfg['file_name']}_traces.xlsx"
        sections = build_excel_sections(trace, rotated)
        write_excel_sections(str(excel_out), outcrop_name, sections)
        logger.debug(f"Excel 导出至: {excel_out}")

        # 4) 绘制并导出原始与旋转后的迹线图，分别使用不同分辨率
        raw_title = f"迹线长度图（数量={trace.trace_count}）"
        raw_name = f"{outcrop_name}_raw(n={trace.trace_count}).png"
        render_trace_plot(X_raw, Y_raw, raw_title, str(output_dir), raw_name, dpi=300)

        rot_title = f"迹线长度图（数量={trace.trace_count}）\n标尺（走向={trace.strike_deg}）"
        rot_name = f"{outcrop_name}_rotated(strike={trace.strike_deg}).png"
        render_trace_plot(X_rot, Y_rot, rot_title, str(output_dir), rot_name, dpi=600)
        logger.debug(f"图片导出完成")

        # 返回运行摘要，供上层记录统计
        return {
            "excel_base": run_cfg["excel_base"],
            "excel_out": str(excel_out),
            "trace_count": trace.trace_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"处理 {outcrop_name} 时发生错误: {e}", exc_info=True)
        return {
            "excel_base": run_cfg["excel_base"],
            "status": "error",
            "error": str(e)
        }
