"""目录变更检测与统一 TTL 缓存工具。"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["DirectoryChangeDetector", "TTLCache"]


class TTLCache:
    """线程安全的 TTL + LRU 缓存。

    Args:
        ttl: 缓存条目生存时间（秒）。
        maxsize: 最大缓存条目数，0 表示无上限。
    """

    def __init__(self, ttl: float = 300.0, maxsize: int = 0) -> None:
        self._ttl = ttl
        self._maxsize = maxsize
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        """获取缓存值，过期或不存在返回 None。"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, value = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        """写入缓存，并淘汰过期/超限条目。"""
        with self._lock:
            self._store[key] = (time.monotonic(), value)
            self._store.move_to_end(key)
            self._evict_expired()
            self._trim()

    def invalidate(self, key: str | None = None) -> None:
        """使指定键或全部缓存失效。"""
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        """使所有以 prefix 开头的键失效。"""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl * 2]
        for k in expired:
            del self._store[k]

    def _trim(self) -> None:
        if self._maxsize > 0:
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)


class DirectoryChangeDetector:
    """Detect external changes from a shallow directory content snapshot."""

    def __init__(self) -> None:
        self._snapshot: tuple[Any, ...] | None = None

    def has_changed(self, directory: Path) -> bool:
        """检测目录是否发生了外部变更。

        Args:
            directory: 待检测的目录路径。

        Returns:
            True 表示检测到变更（且已更新内部快照），False 表示无变更。
        """
        if not directory.exists():
            current_snapshot = ("missing",)
        else:
            try:
                dir_stat = directory.stat()
                children: list[tuple[str, bool, int, int]] = []
                for child in directory.iterdir():
                    try:
                        stat = child.stat()
                    except OSError:
                        children.append((child.name, False, -1, -1))
                        continue
                    children.append((child.name, child.is_dir(), stat.st_size, stat.st_mtime_ns))
                current_snapshot = (dir_stat.st_mtime_ns, tuple(sorted(children)))
            except OSError:
                current_snapshot = ("error",)

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
