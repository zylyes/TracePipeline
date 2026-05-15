"""config.json 读写服务。"""
from __future__ import annotations

import copy
import json
import logging
import sys
from pathlib import Path
from typing import Any

from trace_pipeline.config import (
    DEFAULT_CONFIG,
    DEFAULT_CONFIG_PATH,
    load_config,
    validate_config,
)

logger = logging.getLogger(__name__)

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

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
    "enable_node_recognition",
    "node_merge_tolerance",
    "show_node_overlay",
    "node_label_mode",
)


class ConfigService:
    """封装配置文件的读写，提供前端友好的字典接口。"""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else DEFAULT_CONFIG_PATH
        self._config: dict[str, Any] = {}
        self.reload()

    def reload(self) -> dict[str, Any]:
        """从磁盘重新加载配置。"""
        self._config = load_config(self._path)
        return self._config

    def get(self) -> dict[str, Any]:
        """返回当前配置字典（深拷贝，防止外部修改）。"""
        return copy.deepcopy(self._config)

    def set(self, cfg: dict[str, Any]) -> dict[str, Any]:
        """合并新配置，校验后写回磁盘。"""
        merged = {**self._config, **cfg}
        self._config = validate_config(merged)
        self._save()
        logger.info("配置已保存到 %s", self._path)
        return self._config

    def reset(self) -> dict[str, Any]:
        """恢复为默认配置。"""
        self._config = validate_config(dict(DEFAULT_CONFIG))
        self._save()
        return self._config

    def reset_processing(self) -> dict[str, Any]:
        """仅重置处理参数为默认值，保留路径和样式。"""
        for key in PROCESSING_KEYS:
            self._config[key] = DEFAULT_CONFIG[key]
        self._config = validate_config(self._config)
        self._save()
        return self._config

    def reset_style(self) -> dict[str, Any]:
        """仅重置样式为空（默认值），保留路径和处理参数。"""
        self._config["style"] = {}
        self._config = validate_config(self._config)
        self._save()
        return self._config

    def _save(self) -> None:
        """将当前配置写回 JSON 文件。"""
        self._path.write_text(
            json.dumps(self._config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
