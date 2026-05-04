"""matplotlib 全局样式与 CJK 字体配置。"""
from __future__ import annotations

import logging
from typing import List

import matplotlib
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

# 论文常用西文字体（优先 Times New Roman）
WESTERN_FONT_CANDIDATES: List[str] = [
    "Times New Roman",
    "DejaVu Serif",
    "serif",
]

# 优先使用宋体，与 Times New Roman 风格更协调
CJK_SERIF_CANDIDATES: List[str] = [
    "SimSun",
    "Noto Serif SC",
    "STSong",
    "FangSong",
]

# 无衬线中文 fallback
CJK_SANS_CANDIDATES: List[str] = [
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "Arial Unicode MS",
    "sans-serif",
]

__all__ = ["configure_style"]


def _detect_cjk_fonts(candidates: List[str]) -> List[str]:
    """扫描系统已安装的 CJK 字体，返回可用字体名列表。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return [f for f in candidates if f in available]


def _detect_western_fonts() -> List[str]:
    """扫描系统已安装的西文字体，返回可用字体名列表。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return [f for f in WESTERN_FONT_CANDIDATES if f in available]


def configure_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示并符合论文规范（幂等）。"""
    available_cjk_serif = _detect_cjk_fonts(CJK_SERIF_CANDIDATES)
    available_cjk_sans = _detect_cjk_fonts(CJK_SANS_CANDIDATES)
    available_western = _detect_western_fonts()

    # 优先选择衬线体中文（与 Times New Roman 更协调）
    if available_cjk_serif:
        primary_cjk = available_cjk_serif
    else:
        primary_cjk = available_cjk_sans

    if primary_cjk:
        # 必须把支持中文的字体放在第一位，否则中文无法显示。
        # 西文如果该字体支持则共用，否则 fallback 到后面的字体。
        serif_list = primary_cjk + available_western + ["serif"]
        matplotlib.rcParams["font.family"] = "serif"
        matplotlib.rcParams["font.serif"] = serif_list
        matplotlib.rcParams["font.sans-serif"] = primary_cjk + available_western + ["sans-serif"]
        logger.info("检测到中文主字体: %s", primary_cjk[0])
    else:
        existing = list(matplotlib.rcParams.get("font.sans-serif", ["sans-serif"]))
        matplotlib.rcParams["font.sans-serif"] = existing
        logger.warning(
            "未检测到 CJK 字体，中文标题可能无法正常显示。"
            "建议安装 Noto Serif CJK / SimSun / SimHei 等中文字体。"
        )

    # 论文常用全局设置
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["axes.linewidth"] = 0.8
    matplotlib.rcParams["xtick.major.width"] = 0.6
    matplotlib.rcParams["ytick.major.width"] = 0.6
    matplotlib.rcParams["lines.linewidth"] = 1.0
    matplotlib.rcParams["lines.markersize"] = 4
    matplotlib.rcParams["figure.dpi"] = 300

    logger.debug("matplotlib 全局样式已配置（论文风格）")
