"""绘图通用辅助 — Figure 创建与保存。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

__all__ = ["new_figure", "save_figure"]


def new_figure(
    figsize_cm: tuple[float, float],
    dpi: int = 300,
    subplot_kw: dict | None = None,
) -> tuple[plt.Figure, plt.Axes]:
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
    pad_inches: float = 0.12,
    bbox_inches: str | None = "tight",
) -> str:
    """保存并关闭图形，返回完整输出路径。

    若 figure 已设为透明背景（alpha == 0.0），保存时保持透明。
    采用原子写入策略：先写入临时文件，成功后再重命名为目标文件名，
    避免进程异常中断时产生不完整的损坏文件。
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest_path = out / filename
    tmp_path = dest_path.with_suffix(f".tmp-{__import__('os').getpid()}{dest_path.suffix}")
    try:
        transparent = fig.patch.get_alpha() == 0.0
        kwargs: dict = {
            "dpi": dpi,
            "bbox_inches": bbox_inches,
            "pad_inches": pad_inches,
        }
        if transparent:
            kwargs["transparent"] = True
        else:
            kwargs["facecolor"] = "white"
        fig.savefig(str(tmp_path), **kwargs)
        # 原子重命名，确保文件完整性
        tmp_path.replace(dest_path)
    finally:
        plt.close(fig)
        # 清理可能残留的临时文件
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return str(dest_path.resolve())
