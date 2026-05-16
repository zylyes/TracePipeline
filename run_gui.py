"""TracePipeline GUI 入口文件。

运行方式:
    python run_gui.py
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

# 在导入任何 GUI 库之前设置 DPI 感知，确保获取正确的屏幕物理像素
# Per-Monitor V2 (-4) 是 Windows 10 1607+ 推荐方案，支持多显示器不同 DPI
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
import matplotlib

matplotlib.use('Agg')

# 确保项目根目录在 PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trace_pipeline.config import ensure_workspace_dirs
from backend.main_gui import main

if __name__ == "__main__":
    ensure_workspace_dirs()
    main()
