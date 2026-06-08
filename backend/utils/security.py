"""路径安全校验工具 — 防止路径遍历攻击。"""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import unquote

logger = logging.getLogger(__name__)

__all__ = ["PathSecurityChecker"]


class PathSecurityChecker:
    """路径安全校验器，确保所有文件操作限制在项目根目录内。"""

    _WINDOWS_DEVICE_NAMES = frozenset({
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9",
    })

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve().absolute()

    def safe_path(
        self,
        path: str,
        base: Path | None = None,
        *,
        allow_external_base: bool = False,
    ) -> Path | None:
        """解析并校验路径在项目根目录内，防止路径遍历攻击。

        校验规则：
        1. 拒绝包含 ".." 的原始输入（多层 URL 编码后仍检查）
        2. URL 递归解码后再次检查 ".."
        3. 拒绝 Windows 设备名（检查所有路径段）
        4. 解析符号链接后限制在 base 目录下

        注意：扩展名白名单校验不在此实现，由调用方按需校验
        （例如 GuiApi.get_image 限制图片扩展名以防 XSS）。

        Args:
            path: 原始路径字符串。
            base: 允许操作的基准目录；默认使用项目根目录。

        Returns:
            校验通过的绝对 Path，或 None（表示拒绝）。
        """
        # 递归 URL 解码（防御双重编码如 %252e%252e）
        if not path or not path.strip():
            logger.warning("拒绝空路径")
            return None
        decoded = path
        for _ in range(5):
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        else:
            # 超过 5 次解码仍未稳定，视为攻击
            logger.warning("拒绝过度 URL 编码的路径: %s", path)
            return None

        # 在任何阶段检查路径遍历
        for check_path in (path, decoded):
            p_check = Path(check_path)
            if ".." in p_check.parts:
                logger.warning("拒绝包含 .. 的路径: %s", path)
                return None
            # 检查 Windows 设备名（所有路径段）
            for part in p_check.parts:
                device_candidate = part.rstrip(" .").split(".", 1)[0].upper()
                if device_candidate in self._WINDOWS_DEVICE_NAMES:
                    logger.warning("拒绝 Windows 设备名路径: %s", path)
                    return None

        p = Path(decoded)
        raw_base = Path(base) if base is not None else self._project_root
        if not p.is_absolute():
            p = raw_base / p

        # resolve() 会跟随符号链接；同时检查 base 自身是否被符号链接篡改
        try:
            p = p.resolve().absolute()
            base = raw_base.resolve().absolute()
        except (OSError, RuntimeError) as exc:
            logger.warning("路径解析失败 %s: %s", path, exc)
            return None

        # 默认只允许项目根内路径；GUI 文件对话框选择的目录可显式放宽为可信外部基准。
        if not allow_external_base:
            try:
                base.relative_to(self._project_root)
            except ValueError:
                logger.warning("base 目录越权: %s", base)
                return None

        try:
            p.relative_to(base)
        except ValueError:
            logger.warning("拒绝越权路径: %s", p)
            return None

        return p
