"""迹线处理入口脚本 — 调用 trace_pipeline.cli.main。

命令行参数与使用方式详见:
    python run_trace_pipeline.py --help
"""
import multiprocessing

# 并行模式下使用 spawn 启动子进程，避免继承父进程的 matplotlib 全局状态
# 必须在任何多进程代码之前设置
try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    pass

from trace_pipeline.cli import main

if __name__ == "__main__":
    main()
