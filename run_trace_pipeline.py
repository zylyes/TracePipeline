"""迹线处理入口脚本 — 调用 trace_pipeline.cli.main。

命令行参数与使用方式详见:
    python run_trace_pipeline.py --help
"""
from trace_pipeline.config import ensure_workspace_dirs
from trace_pipeline.cli import main

if __name__ == "__main__":
    ensure_workspace_dirs()
    main()
