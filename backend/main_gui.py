"""GUI 入口程序 — PyWebView 启动器。"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
import matplotlib

matplotlib.use('Agg')

import webview

from trace_pipeline import __version__
from trace_pipeline.cli.logging_setup import setup_logging

from backend.gui_api import GuiApi
from backend.webview2_checker import WebView2Checker

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "backend" / "static"
ICON_PATH = PROJECT_ROOT / "reference" / "ECUT.ico"

# 初始化统一结构化日志系统（控制台 + JSON Lines 文件）
start_time = time.perf_counter()
setup_logging()
init_duration = (time.perf_counter() - start_time) * 1000

logger = logging.getLogger(__name__)
logger.info(
    "=== 应用程序启动 ===",
    extra={
        "stage": "app_start",
        "version": __version__,
        "project_root": str(PROJECT_ROOT),
        "static_dir": str(STATIC_DIR),
        "icon_path": str(ICON_PATH),
        "init_duration_ms": round(init_duration, 3),
    },
)


def main() -> None:
    start = time.perf_counter()
    api = GuiApi()
    logger.info("GuiApi 初始化完成 (%.3f ms)", (time.perf_counter() - start) * 1000, extra={"stage": "gui_api_init"})

    checker = WebView2Checker()

    if not checker.is_installed():
        logger.warning("WebView2 Runtime 未安装，提示用户下载", extra={"stage": "webview2_missing"})
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
    logger.info("前端入口: %s", url, extra={"stage": "window_create", "url": url})

    window = webview.create_window(
        f"TracePipeline v{__version__}",
        url=url,
        width=1400,
        height=900,
        min_size=(1000, 600),
        js_api=api,
    )
    api.set_window(window)

    # 注册窗口关闭事件，优雅等待后台流水线完成，避免文件损坏
    def on_closing():
        api.shutdown_pipeline()

    window.events.closing += on_closing

    icon = str(ICON_PATH.resolve()) if ICON_PATH.exists() else None
    logger.info(
        "窗口已创建，等待关闭",
        extra={
            "stage": "window_open",
            "title": f"TracePipeline v{__version__}",
            "width": 1400,
            "height": 900,
            "icon": icon,
        },
    )
    webview.start(debug=False, icon=icon)
    logger.info("=== 应用程序退出 ===", extra={"stage": "app_exit"})


if __name__ == "__main__":
    main()
