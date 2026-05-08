"""matplotlib 全局样式与 CJK 字体配置。"""
from __future__ import annotations

import functools
import logging

import matplotlib
import matplotlib.font_manager as fm

logger = logging.getLogger(__name__)

# 论文常用西文字体（优先 Times New Roman）
WESTERN_FONT_CANDIDATES: list[str] = [
    "Times New Roman",
    "DejaVu Serif",
    "serif",
]

# 优先使用宋体，与 Times New Roman 风格更协调
CJK_SERIF_CANDIDATES: list[str] = [
    "SimSun",
    "Noto Serif SC",
    "STSong",
    "FangSong",
]

# 无衬线中文 fallback
CJK_SANS_CANDIDATES: list[str] = [
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
    "Arial Unicode MS",
    "sans-serif",
]

__all__ = ["configure_style"]


@functools.lru_cache(maxsize=1)
def _get_font_cache() -> dict[str, list[str]]:
    """返回系统字体检测缓存（惰性创建、仅扫描一次）。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return {
        "cjk_serif": [f for f in CJK_SERIF_CANDIDATES if f in available],
        "cjk_sans": [f for f in CJK_SANS_CANDIDATES if f in available],
        "western": [f for f in WESTERN_FONT_CANDIDATES if f in available],
    }


def configure_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示并符合论文规范（幂等）。"""
    cache = _get_font_cache()
    available_cjk_serif = cache["cjk_serif"]
    available_cjk_sans = cache["cjk_sans"]
    available_western = cache["western"]

    # 优先选择衬线体中文（与 Times New Roman 更协调）
    primary_cjk = available_cjk_serif or available_cjk_sans

    if primary_cjk:
        # 将 font.family 直接设为列表，matplotlib 3.8+ 会按字符级别回退：
        # TNR 有字形 → 英文/数字用 TNR，TNR 无字形 → 中文回退到 SimSun
        #   中文 → 宋体，英文/数字 → Times New Roman
        font_family_list = available_western + primary_cjk + ["serif"]
        matplotlib.rcParams["font.family"] = font_family_list
        logger.info("检测到中文主字体: %s (回退)", primary_cjk[0])
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
