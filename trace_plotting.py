"""迹线可视化辅助工具。"""
import numpy as np
import matplotlib.pyplot as plt


def build_nan_separated_lines(XY: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """构造用 NaN 分隔的坐标数组，以单次 plot 绘制多段折线。"""
    n = XY.shape[0]
    X_plot = np.column_stack([XY[:, 0], XY[:, 2], np.full((n,), np.nan)]).ravel()
    Y_plot = np.column_stack([XY[:, 1], XY[:, 3], np.full((n,), np.nan)]).ravel()
    return X_plot, Y_plot


def style_trace_axes(ax: plt.Axes) -> plt.Axes:
    """统一设置迹线图的坐标轴样式。"""
    plt.axis("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1)
    ax.tick_params(labelsize=14)
    try:
        ax.set_fontname("Times New Roman")
    except Exception:
        pass
    ax.set_facecolor("white")
    fig = ax.get_figure()
    fig.patch.set_facecolor("white")
    return ax
