"""matplotlib 全局样式与 CJK 字体配置。"""
from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any

import matplotlib
import matplotlib.font_manager as fm

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.text import Text

logger = logging.getLogger(__name__)

WESTERN_PRIMARY_FONT = "Times New Roman"
CJK_PRIMARY_FONT = "SimSun"

# 论文常用西文字体（优先 Times New Roman）
WESTERN_FONT_CANDIDATES: list[str] = [
    WESTERN_PRIMARY_FONT,
    "Liberation Serif",
    "DejaVu Serif",
    "serif",
]

# 优先使用宋体，与 Times New Roman 风格更协调
CJK_SERIF_CANDIDATES: list[str] = [
    CJK_PRIMARY_FONT,
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

__all__ = [
    "configure_style",
    "text_font_kwargs",
]


@functools.lru_cache(maxsize=1)
def _get_font_cache() -> dict[str, list[str]]:
    """返回系统字体检测缓存（惰性创建、仅扫描一次）。"""
    available = {f.name for f in fm.fontManager.ttflist}
    return {
        "cjk_serif": [f for f in CJK_SERIF_CANDIDATES if f in available],
        "cjk_sans": [f for f in CJK_SANS_CANDIDATES if f in available],
        "western": [f for f in WESTERN_FONT_CANDIDATES if f in available],
    }


def _dedupe_fonts(fonts: list[str]) -> list[str]:
    result: list[str] = []
    for font in fonts:
        if font and font not in result:
            result.append(font)
    return result


def _preferred_font_stack(
    western_fonts: list[str],
    cjk_serif_fonts: list[str],
    cjk_sans_fonts: list[str],
) -> list[str]:
    return _dedupe_fonts([
        WESTERN_PRIMARY_FONT,
        CJK_PRIMARY_FONT,
        *western_fonts,
        *cjk_serif_fonts,
        *cjk_sans_fonts,
        "serif",
    ])


def _current_font_family() -> list[str]:
    family = matplotlib.rcParams.get("font.family", [WESTERN_PRIMARY_FONT, CJK_PRIMARY_FONT])
    if isinstance(family, str):
        return [family]
    return list(family)


def text_font_kwargs(**kwargs: object) -> dict[str, Any]:
    """返回绘图文本统一使用的字体参数。"""
    merged: dict[str, Any] = {"fontfamily": _current_font_family()}
    merged.update(kwargs)
    return merged


def apply_text_font(text: Text) -> Text:
    """将单个 matplotlib 文本对象设置为统一字体族。"""
    text.set_fontfamily(_current_font_family())
    return text


def apply_axis_text_fonts(ax: Axes) -> None:
    """统一坐标轴刻度与网格标签字体。"""
    for text in (*ax.get_xticklabels(), *ax.get_yticklabels()):
        apply_text_font(text)


def configure_style() -> None:
    """配置 matplotlib 全局样式以支持中文显示并符合论文规范（幂等）。"""
    cache = _get_font_cache()
    available_cjk_serif = cache["cjk_serif"]
    available_cjk_sans = cache["cjk_sans"]
    available_western = cache["western"]

    font_family_list = _preferred_font_stack(
        available_western,
        available_cjk_serif,
        available_cjk_sans,
    )
    matplotlib.rcParams["font.family"] = font_family_list
    matplotlib.rcParams["font.serif"] = font_family_list
    matplotlib.rcParams["font.sans-serif"] = _dedupe_fonts([
        CJK_PRIMARY_FONT,
        *available_cjk_sans,
        *available_cjk_serif,
        "sans-serif",
    ])

    if WESTERN_PRIMARY_FONT not in available_western:
        logger.warning("未检测到 %s，英文和数字将使用可用衬线字体回退。", WESTERN_PRIMARY_FONT)
    if CJK_PRIMARY_FONT not in available_cjk_serif:
        logger.warning("未检测到 %s，中文将使用可用 CJK 字体回退。", CJK_PRIMARY_FONT)

    # 数学文本中的英文、数字和单位显式使用 Times New Roman。
    matplotlib.rcParams["mathtext.fontset"] = "custom"
    matplotlib.rcParams["mathtext.rm"] = WESTERN_PRIMARY_FONT
    matplotlib.rcParams["mathtext.it"] = f"{WESTERN_PRIMARY_FONT}:italic"
    matplotlib.rcParams["mathtext.bf"] = f"{WESTERN_PRIMARY_FONT}:bold"
    matplotlib.rcParams["mathtext.sf"] = WESTERN_PRIMARY_FONT
    matplotlib.rcParams["mathtext.default"] = "regular"

    # 论文常用全局设置
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["font.size"] = 8.5
    matplotlib.rcParams["axes.linewidth"] = 0.7
    matplotlib.rcParams["xtick.major.width"] = 0.55
    matplotlib.rcParams["ytick.major.width"] = 0.55
    matplotlib.rcParams["xtick.major.size"] = 3.0
    matplotlib.rcParams["ytick.major.size"] = 3.0
    matplotlib.rcParams["xtick.labelsize"] = 8.0
    matplotlib.rcParams["ytick.labelsize"] = 8.0
    matplotlib.rcParams["lines.linewidth"] = 0.85
    matplotlib.rcParams["lines.markersize"] = 3.5
    matplotlib.rcParams["figure.dpi"] = 300
    matplotlib.rcParams["savefig.dpi"] = 300
    matplotlib.rcParams["savefig.facecolor"] = "white"

    logger.debug("matplotlib 全局样式已配置（论文风格）")
