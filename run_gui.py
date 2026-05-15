"""TracePipeline GUI 入口文件。

运行方式:
    python run_gui.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
import matplotlib

matplotlib.use('Agg')

# 确保项目根目录在 PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main_gui import main  # noqa: E402

if __name__ == "__main__":
    main()
