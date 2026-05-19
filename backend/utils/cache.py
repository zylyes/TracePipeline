"""目录变更检测与缓存管理工具。"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["DirectoryChangeDetector"]


class DirectoryChangeDetector:
    """通过比较目录 mtime 和文件数量快照，检测目录是否发生了外部变更。"""

    def __init__(self) -> None:
        self._snapshot: tuple[float, int] | None = None

    def has_changed(self, directory: Path) -> bool:
        """检测目录是否发生了外部变更。

        Args:
            directory: 待检测的目录路径。

        Returns:
            True 表示检测到变更（且已更新内部快照），False 表示无变更。
        """
        if not directory.exists():
            current_snapshot = (-1.0, 0)
        else:
            try:
                mtime = directory.stat().st_mtime
                file_count = sum(1 for _ in directory.iterdir())
                current_snapshot = (mtime, file_count)
            except OSError:
                current_snapshot = (-1.0, 0)

        if self._snapshot is None:
            self._snapshot = current_snapshot
            return False

        if current_snapshot != self._snapshot:
            self._snapshot = current_snapshot
            return True

        return False

    def invalidate(self) -> None:
        """手动使缓存失效，下次调用 has_changed 时将重新建立快照。"""
        self._snapshot = None
