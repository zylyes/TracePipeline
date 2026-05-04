"""matplotlib 全局样式与 CJK 字体配置。"""
from __future__ import annotations

import logging
from typing import List

import matplotlib
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

CJK_FONT_CANDIDATES: List[str] = [
    "SimHei",
    "Microsoft YaHei",
    "Arial Unicode MS",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "sans-serif",
]

__all__ = ["configure_style"]


def _detect_cjk_fonts() -> List[str]:
    """扫描系统已安装的 CJK 字体，返回可用字体名列表。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return [f for f in CJK_FONT_CANDIDATES if f in available]


def configure_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示（幂等）。"""
    available_cjk = _detect_cjk_fonts()

    existing = list(matplotlib.rcParams.get("font.sans-serif", ["sans-serif"]))
    existing_filtered = [f for f in existing if f not in available_cjk]

    if available_cjk:
        font_list = available_cjk + existing_filtered
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = font_list
        logger.info("检测到 CJK 字体: %s", ", ".join(available_cjk[:3]))
    else:
        matplotlib.rcParams["font.sans-serif"] = existing_filtered
        logger.warning(
            "未检测到 CJK 字体，中文标题可能无法正常显示。"
            "建议安装 SimHei / Microsoft YaHei 等中文字体。"
        )

    matplotlib.rcParams["axes.unicode_minus"] = False
    logger.debug("matplotlib 全局样式已配置")
