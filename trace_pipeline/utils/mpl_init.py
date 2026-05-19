"""matplotlib 初始化工具。"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["force_noninteractive_backend"]


def force_noninteractive_backend() -> None:
    """强制设置非交互式 matplotlib 后端（Agg），防止多进程/后台线程绘图冲突。

    幂等调用：重复执行无副作用。
    """
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        logger.debug("matplotlib 后端已强制设置为 Agg")
    except Exception:
        pass
