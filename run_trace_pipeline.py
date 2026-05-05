"""迹线处理入口脚本 — 薄 shim，调用 trace_pipeline.cli.main。

命令行参数与使用方式详见:
    python run_trace_pipeline.py --help

也可等价使用:
    python -m trace_pipeline [options]
"""
from trace_pipeline.cli import main

if __name__ == "__main__":
    main()
