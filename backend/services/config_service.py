"""config.json 读写服务。"""

from __future__ import annotations

import copy
import json
import logging
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any

from trace_pipeline.config import (
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    load_config,
    validate_config,
)

logger = logging.getLogger(__name__)

# 处理参数键（不含路径和样式）
PROCESSING_KEYS = (
    "process_all",
    "export_rose_plot",
    "rose_dpi",
    "rose_bin_width",
    "trace_dpi",
    "rotated_trace_dpi",
    "window_strategy",
    "auto_density_threshold",
    "tangent_window_count",
    "min_intersections",
    "enable_node_recognition",
    "node_merge_tolerance",
    "show_node_overlay",
    "is_dev_mode",
    "node_label_mode",
)


class ConfigService:
    """封装配置文件的读写，提供前端友好的字典接口。

    作为 config.json 的唯一写入入口，确保所有配置变更通过此服务进行。
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else DEFAULT_CONFIG_PATH
        self._config: dict[str, Any] = {}
        self._lock = threading.RLock()
        self.reload()

    def _ensure_config_exists(self) -> None:
        """如果 config.json 不存在，用默认配置创建之（幂等）。"""
        if self._path.exists():
            return
        try:
            self._config = validate_config(dict(DEFAULT_CONFIG))
            self._save()
            logger.info("自动创建默认配置: %s", self._path)
        except (PermissionError, OSError) as exc:
            logger.warning(
                "无法创建配置文件 %s: %s，程序将继续运行",
                self._path,
                exc,
            )

    def reload(self) -> dict[str, Any]:
        """从磁盘重新加载配置；文件不存在时自动创建默认配置。"""
        with self._lock:
            if not self._path.exists():
                self._ensure_config_exists()
                return self._config
            self._config = load_config(self._path)
            logger.debug(
                "配置已重新加载: %s (%d 个字段)",
                self._path,
                len(self._config),
                extra={
                    "stage": "config_reload",
                    "path": str(self._path),
                    "field_count": len(self._config),
                },
            )
            return self._config

    def get(self) -> dict[str, Any]:
        """返回当前配置字典（深拷贝，防止外部修改）。"""
        with self._lock:
            return copy.deepcopy(self._config)

    def set(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """合并新配置，校验后写回磁盘。"""
        with self._lock:
            # 刷新磁盘最新值，避免外部修改被内存旧值覆盖
            self.reload()
            merged = {**self._config, **cfg}
            self._config = validate_config(merged)
            self._save()
            logger.info("配置已保存到 %s", self._path)
            return self._config

    def reset(self) -> dict[str, Any]:
        """恢复为默认配置。"""
        with self._lock:
            self._config = validate_config(dict(DEFAULT_CONFIG))
            self._save()
            return self._config

    def reset_processing(self) -> dict[str, Any]:
        """仅重置处理参数为默认值，保留路径和样式。"""
        with self._lock:
            for key in PROCESSING_KEYS:
                self._config[key] = DEFAULT_CONFIG[key]
            self._config = validate_config(self._config)
            self._save()
            return self._config

    def reset_style(self) -> dict[str, Any]:
        """仅重置样式为空（默认值），保留路径和处理参数。"""
        with self._lock:
            self._config["style"] = {}
            self._config = validate_config(self._config)
            self._save()
            return self._config

    def _save(self) -> None:
        """将当前配置原子写入 JSON 文件（先写临时文件再替换，防止写入中断损坏配置）。"""
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            tmp_path.write_text(
                json.dumps(self._config, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(self._path)
        except (PermissionError, OSError, TypeError) as exc:
            # 清理临时文件，避免残留；记录写入异常
            logger.warning("配置写入失败: %s — %s", self._path, exc)
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
            raise
