"""迹线处理入口脚本 — 调用 trace_pipeline.cli.main。

命令行参数与使用方式详见:
    python run_trace_pipeline.py --help
"""
import multiprocessing

try:
    multiprocessing.set_start_method("spawn")
except RuntimeError:
    if multiprocessing.get_start_method(allow_none=True) != "spawn":
        import warnings
        warnings.warn(
            "当前多进程启动方法不是 'spawn'，并行模式下 matplotlib 状态可能冲突。"
            "建议通过 `multiprocessing.set_start_method('spawn')` 显式设置。",
            RuntimeWarning,
            stacklevel=2,
        )

from trace_pipeline.config import ensure_workspace_dirs
from trace_pipeline.cli import main

if __name__ == "__main__":
    ensure_workspace_dirs()
    main()


def _get_spawn_context():
    """返回 spawn 多进程上下文，避免全局修改启动方法。"""
    return multiprocessing.get_context("spawn")
