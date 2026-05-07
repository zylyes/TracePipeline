"""绘图通用辅助 — Figure 创建与保存。"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt

__all__ = ["new_figure", "save_figure"]


def new_figure(
    figsize_cm: Tuple[float, float],
    dpi: int = 300,
    subplot_kw: dict | None = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """创建指定厘米尺寸的图形并返回 (fig, ax)，背景为白色。"""
    w_inch, h_inch = figsize_cm[0] / 2.54, figsize_cm[1] / 2.54
    fig, ax = plt.subplots(
        figsize=(w_inch, h_inch),
        dpi=dpi,
        subplot_kw=subplot_kw or {},
    )
    fig.patch.set_facecolor("white")
    return fig, ax


def save_figure(
    fig: plt.Figure,
    output_dir: str,
    filename: str,
    dpi: int = 300,
    pad_inches: float = 0.08,
) -> str:
    """保存并关闭图形，返回完整输出路径。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    full_path = str(out / filename)
    try:
        fig.tight_layout(pad=0.6)
        fig.savefig(full_path, dpi=dpi, facecolor="white", bbox_inches="tight", pad_inches=pad_inches)
    finally:
        plt.close(fig)
    return full_path
