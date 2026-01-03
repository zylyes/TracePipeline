"""迹线处理脚本：读取 Excel、计算几何、导出表格与图片。"""
from __future__ import annotations

import logging
import sys
from typing import List

from trace_pipeline import ensure_io_paths, find_trace_tables, load_config
from trace_pipeline.pipeline import process_target

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main(cfg: dict | None = None):
    try:
        cfg = cfg or load_config()
    except Exception as e:
        logger.critical(f"无法加载配置: {e}")
        return

    # 校验输入/输出路径并确定待处理的 Excel 列表
    input_dir, output_dir = ensure_io_paths(cfg["input_dir"], cfg["output_dir"])
    
    logger.info(f"输入目录：{input_dir}")
    logger.info(f"输出目录：{output_dir}")

    discovered = find_trace_tables(input_dir)
    targets = discovered if (cfg.get("process_all") and discovered) else [(cfg["excel_base"], cfg["outcrop_name"])]

    logger.info(f"待处理文件数：{len(targets)}")

    run_summaries: List[dict] = []

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

        if summary["status"] == "success":
            logger.info(
                f"[{idx}/{len(targets)}] 完成 {excel_base} -> {summary['excel_out']} (迹线数={summary['trace_count']})"
            )
        else:
            logger.warning(f"[{idx}/{len(targets)}] 失败 {excel_base}: {summary.get('error')}")

    if not run_summaries:
        logger.warning(f"未找到可处理的文件，请检查输入目录：{input_dir}")
        return

    success_count = sum(1 for s in run_summaries if s["status"] == "success")
    logger.info(f"处理完成，成功: {success_count}/{len(run_summaries)}")


if __name__ == "__main__":
    main()
