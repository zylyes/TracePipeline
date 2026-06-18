"""GUI 入口程序 — PyWebView 启动器。"""

from __future__ import annotations

import ctypes
import logging
import time

from trace_pipeline.utils.mpl_init import force_noninteractive_backend
from trace_pipeline.utils.paths import get_project_root, get_resource_root


def get_screen_size() -> tuple[int, int]:
    """获取主显示器的屏幕分辨率（像素）。

    支持 Windows/macOS/Linux，使用 ctypes 调用系统 API，
    无需第三方依赖，兼容所有分辨率和 DPI 缩放设置。
    """
    try:
        # Windows: 使用 user32.GetSystemMetrics
        # DPI 感知已在 run_gui.py 入口处设置，这里直接获取物理像素
        width = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
        height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return width, height
    except Exception:
        # ctypes 调用失败（非 Windows 或权限不足），降级到 tkinter
        pass

    # 回退方案：tkinter（几乎所有 Python 环境都有）
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    except Exception:
        # tkinter 不可用（无头环境），降级到硬编码默认值
        pass

    # 终极回退：返回常用默认值
    return 1920, 1080


def get_window_position(window_width: int, window_height: int) -> tuple[int, int]:
    """根据屏幕尺寸和窗口尺寸计算居中坐标。

    Args:
        window_width: 窗口宽度（像素）
        window_height: 窗口高度（像素）

    Returns:
        (x, y) 窗口左上角在屏幕上的坐标
    """
    screen_width, screen_height = get_screen_size()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    # 确保不会超出屏幕边界（坐标为负值）
    return max(0, x), max(0, y)


force_noninteractive_backend()

import webview  # noqa: E402

from backend.gui_api import GuiApi  # noqa: E402
from backend.webview2_checker import WebView2Checker  # noqa: E402
from trace_pipeline import __version__  # noqa: E402
from trace_pipeline.cli.logging_setup import setup_logging  # noqa: E402

PROJECT_ROOT = get_project_root()
RESOURCE_ROOT = get_resource_root()
STATIC_DIR = RESOURCE_ROOT / "backend" / "static"
ICON_PATH = RESOURCE_ROOT / "reference" / "favicon.ico"

logger = logging.getLogger(__name__)


def main() -> None:
    start_time = time.perf_counter()
    setup_logging()
    init_duration = (time.perf_counter() - start_time) * 1000
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

    # P2: 先检查 WebView2 是否安装，避免在缺失时浪费 Service 初始化时间
    checker = WebView2Checker()

    if not checker.is_installed():
        logger.warning("WebView2 Runtime 未安装，提示用户下载", extra={"stage": "webview2_missing"})
        download_url = checker.get_download_url()
        html = f"""
        <html>
        <head><meta charset="utf-8"><title>WebView2 未安装</title></head>
        <body style="font-family:SimSun,sans-serif;text-align:center;padding:40px;">
            <h2>需要安装 WebView2 Runtime</h2>
            <p>请点击下方链接下载并安装后重新启动程序。</p>
            <a
                href="{download_url}"
                onclick="pywebview.api.open_external(this.href);return false;"
            >
                前往下载页面
            </a>
        </body>
        </html>
        """
        # WebView2 未安装提示窗口也居中显示
        w, h = 400, 250
        x, y = get_window_position(w, h)
        window = webview.create_window(
            "WebView2 未安装",
            html=html,
            width=w,
            height=h,
            x=x,
            y=y,
            js_api=None,  # GuiApi 未初始化，无需绑定 API
            frameless=True,
            easy_drag=True,
        )
        webview.start(debug=False)
        return

    start = time.perf_counter()
    api = GuiApi()
    logger.info(
        "GuiApi 初始化完成 (%.3f ms)",
        (time.perf_counter() - start) * 1000,
        extra={"stage": "gui_api_init"},
    )

    # 确定入口文件
    index_html = STATIC_DIR / "index.html"
    url = str(index_html.resolve()) if index_html.exists() else str(STATIC_DIR.resolve())
    logger.info("前端入口: %s", url, extra={"stage": "window_create", "url": url})

    # 窗口尺寸常量
    win_width = 1400
    win_height = 900
    # 计算居中位置
    x, y = get_window_position(win_width, win_height)
    logger.info(
        "窗口居中计算: 屏幕=%dx%d, 窗口=%dx%d, 位置=(%d, %d)",
        *get_screen_size(),
        win_width,
        win_height,
        x,
        y,
        extra={"stage": "window_position", "x": x, "y": y},
    )

    window = webview.create_window(
        f"TracePipeline v{__version__}",
        url=url,
        width=win_width,
        height=win_height,
        x=x,
        y=y,
        min_size=(1000, 600),
        js_api=api,
        frameless=True,
        easy_drag=False,
    )
    api.set_window(window)

    # 窗口显示后再次强制居中，并子类化启用原生拖拽 / resize
    def on_shown():
        window.move(x, y)
        logger.info(
            "窗口显示后强制居中到 (%d, %d)", x, y, extra={"stage": "window_shown", "x": x, "y": y}
        )

    window.events.shown += on_shown

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
            "width": win_width,
            "height": win_height,
            "x": x,
            "y": y,
            "icon": icon,
        },
    )
    webview.start(debug=False, icon=icon)
    logger.info("=== 应用程序退出 ===", extra={"stage": "app_exit"})


if __name__ == "__main__":
    main()
