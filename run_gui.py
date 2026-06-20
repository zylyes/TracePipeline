"""TracePipeline GUI 入口文件。

运行方式:
    python run_gui.py
"""

from __future__ import annotations

import ctypes
import logging
import multiprocessing
import sys
import traceback
from contextlib import suppress

from trace_pipeline.utils.mpl_init import force_noninteractive_backend
from trace_pipeline.utils.paths import get_project_root

# freeze_support() 必须在任何 spawn 子进程创建之前调用，
# 确保子进程不会重复执行 GUI 初始化代码（webview、DPI 等）
multiprocessing.freeze_support()

# 在导入任何 GUI 库之前设置 DPI 感知，确保获取正确的屏幕物理像素
# Per-Monitor V2 是 Windows 10 1607+ 推荐方案，支持多显示器不同 DPI
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
except Exception:
    with suppress(Exception):
        ctypes.windll.user32.SetProcessDPIAware()

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
force_noninteractive_backend()

# 确保项目根目录在 PYTHONPATH
PROJECT_ROOT = get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    from backend.main_gui import main  # noqa: E402
    from trace_pipeline.config import ensure_workspace_dirs  # noqa: E402

    try:
        ensure_workspace_dirs()
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        try:
            logging.exception("TracePipeline GUI 启动失败")
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)
        error_msg = "TracePipeline 启动失败，请检查配置或环境。"
        try:
            ctypes.windll.user32.MessageBoxW(0, error_msg, "TracePipeline 启动失败", 0x10)
        except Exception:
            pass
        sys.exit(1)
