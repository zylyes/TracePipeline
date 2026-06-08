"""WebView2 Runtime 检测。"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    import winreg
else:  # pragma: no cover - only exercised on non-Windows platforms
    winreg = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_WEBVIEW2_REG_KEYS = [
    (
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    ),
    (
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    ),
    (
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
    ),
]

_DOWNLOAD_URL = "https://developer.microsoft.com/en-us/microsoft-edge/webview2/"


class WebView2Checker:
    """检测系统是否已安装 WebView2 Runtime。"""

    def is_installed(self) -> bool:
        """通过注册表检查 WebView2 是否存在。"""
        if winreg is None:
            return True
        for hive, key_path in _WEBVIEW2_REG_KEYS:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, "pv")
                    if value and str(value).strip():
                        logger.info("检测到 WebView2 版本: %s", value)
                        return True
            except OSError:
                continue
        # 备选：检查常见 DLL 路径
        dll_paths = [
            Path(r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft\\EdgeWebView\\Application",
        ]
        return any(dp.exists() and any(dp.iterdir()) for dp in dll_paths)

    def get_download_url(self) -> str:
        return _DOWNLOAD_URL
