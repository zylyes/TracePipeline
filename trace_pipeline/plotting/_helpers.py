"""绘图通用辅助 — Figure 创建、保存与共享装饰元素。"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

from trace_pipeline.utils.mpl_init import force_noninteractive_backend

force_noninteractive_backend()

import matplotlib.pyplot as plt

from .style import text_font_kwargs

__all__ = ["new_figure", "save_figure", "add_data_north_arrow", "compute_data_bounds"]


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
    tmp_path = dest_path.with_suffix(f".tmp-{os.getpid()}{dest_path.suffix}")
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


_ANNOTATION_ZORDER = 12


def _north_arrow_geometry(
    north_angle_deg: float,
    center_x: float,
    center_y: float,
    arrow_len: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], float, float]:
    """计算指北针的 base/tip/label 坐标与方向分量。

    供数据坐标版与 transAxes 版共享几何计算,消除重复。

    Returns:
        (base_xy, tip_xy, label_xy, dx, dy)
    """
    angle = math.radians(north_angle_deg)
    dx, dy = math.cos(angle), math.sin(angle)
    label_gap = arrow_len * 0.25
    base = (center_x - arrow_len * dx * 0.50, center_y - arrow_len * dy * 0.50)
    tip = (center_x + arrow_len * dx * 0.50, center_y + arrow_len * dy * 0.50)
    label = (tip[0] + label_gap * dx, tip[1] + label_gap * dy)
    return base, tip, label, dx, dy


def add_data_north_arrow(
    ax: plt.Axes,
    north_angle_deg: float,
    north_x: float,
    north_y: float,
    arrow_len: float,
) -> None:
    """在数据坐标系下绘制指北针（供 trace_plot.py / preview_plot.py 共用）。

    Args:
        ax: 数据轴。
        north_angle_deg: 北方向角度（度）。
        north_x: 指北针中心 X（数据坐标）。
        north_y: 指北针中心 Y（数据坐标）。
        arrow_len: 箭头长度（数据坐标单位）。
    """
    (base_x, base_y), (tip_x, tip_y), (label_x, label_y), _dx, _dy = _north_arrow_geometry(
        north_angle_deg, north_x, north_y, arrow_len
    )
    ax.annotate(
        "",
        xy=(tip_x, tip_y),
        xytext=(base_x, base_y),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.85, mutation_scale=11),
        clip_on=False,
        zorder=15,
    )
    ax.text(
        label_x,
        label_y,
        "N",
        ha="center",
        va="center",
        clip_on=False,
        zorder=15,
        **text_font_kwargs(fontsize=9.2, fontweight="bold", color="black"),
    )


def compute_data_bounds(
    segments: np.ndarray,
    extra_xs: np.ndarray | None = None,
    extra_ys: np.ndarray | None = None,
) -> tuple[float, float, float, float]:
    """计算迹线图的数据范围 (x_min, x_max, y_min, y_max)。

    统一使用 numpy 向量化实现，供 trace_plot.py / preview_plot.py 共用。

    Args:
        segments: (N, 4) 线段数组。
        extra_xs: 额外的 X 坐标（凸包、圆窗、节点等）。
        extra_ys: 额外的 Y 坐标（凸包、圆窗、节点等）。
    """
    if segments.size == 0 and (extra_xs is None or extra_xs.size == 0):
        return 0.0, 1.0, 0.0, 1.0

    if segments.size > 0:
        seg_xs = segments[:, [0, 2]].ravel()
        seg_ys = segments[:, [1, 3]].ravel()
        if not np.isfinite(seg_xs).all() or not np.isfinite(seg_ys).all():
            raise ValueError("segments 包含 NaN 或 inf，无法绘制迹线图")
    else:
        seg_xs = np.array([], dtype=float)
        seg_ys = np.array([], dtype=float)

    if extra_xs is not None and extra_xs.size > 0:
        seg_xs = np.concatenate([seg_xs, extra_xs])
    if extra_ys is not None and extra_ys.size > 0:
        seg_ys = np.concatenate([seg_ys, extra_ys])

    return float(seg_xs.min()), float(seg_xs.max()), float(seg_ys.min()), float(seg_ys.max())
