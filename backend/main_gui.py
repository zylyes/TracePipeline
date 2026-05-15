"""GUI 入口程序 — PyWebView 启动器。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
import matplotlib

matplotlib.use('Agg')

import webview

from trace_pipeline import __version__
from trace_pipeline.cli.logging_setup import setup_logging

from backend.gui_api import GuiApi
from backend.webview2_checker import WebView2Checker

# 先配置 trace_pipeline 双通道日志（控制台 + 文件）
setup_logging()

# 控制台日志保留
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "backend" / "static"
ICON_PATH = PROJECT_ROOT / "reference" / "ECUT.ico"

# 为 backend 包追加同一日志文件，保证前后端日志统一落盘
_log_dir = PROJECT_ROOT / "logs"
if _log_dir.is_dir():
    _log_files = sorted(_log_dir.glob("pipeline_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if _log_files:
        _latest_log = _log_files[0]
        _backend_logger = logging.getLogger("backend")
        _backend_logger.setLevel(logging.DEBUG)
        if not any(isinstance(h, logging.FileHandler) for h in _backend_logger.handlers):
            _fh = logging.FileHandler(str(_latest_log), encoding="utf-8")
            _fh.setLevel(logging.DEBUG)
            _fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
            _backend_logger.addHandler(_fh)


def main() -> None:
    api = GuiApi()
    checker = WebView2Checker()

    if not checker.is_installed():
        html = f"""
        <html>
        <head><meta charset="utf-8"><title>WebView2 未安装</title></head>
        <body style="font-family:SimSun,sans-serif;text-align:center;padding:40px;">
            <h2>需要安装 WebView2 Runtime</h2>
            <p>请点击下方链接下载并安装后重新启动程序。</p>
            <a href="{checker.get_download_url()}" onclick="pywebview.api.open_external(this.href);return false;">
                前往下载页面
            </a>
        </body>
        </html>
        """
        window = webview.create_window(
            "WebView2 未安装",
            html=html,
            width=400,
            height=250,
            js_api=api,
        )
        webview.start(debug=False)
        return

    # 确定入口文件
    index_html = STATIC_DIR / "index.html"
    url = str(index_html.resolve()) if index_html.exists() else str(STATIC_DIR.resolve())

    window = webview.create_window(
        f"TracePipeline v{__version__}",
        url=url,
        width=1400,
        height=900,
        min_size=(1000, 600),
        js_api=api,
    )
    api.set_window(window)
    icon = str(ICON_PATH.resolve()) if ICON_PATH.exists() else None
    webview.start(debug=False, icon=icon)


if __name__ == "__main__":
    main()
