"""GUI 入口程序 — PyWebView 启动器。"""
from __future__ import annotations

import logging
import sys
import webbrowser
from pathlib import Path

# 强制设置 matplotlib 后端为 Agg（非交互式），避免后台线程绘图时触发 Tkinter
import matplotlib
matplotlib.use('Agg')

import webview

from .gui_api import GuiApi
from .webview2_checker import WebView2Checker

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "backend" / "static"
ICON_PATH = PROJECT_ROOT / "reference" / "ECUT.ico"


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
        "TracePipeline v1.0",
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
