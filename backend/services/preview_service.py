"""样式预览图生成服务（完全解耦版）。

预览模块与正式绘图程序彻底解耦：
- 不依赖 trace_pipeline 的任何业务逻辑（统计、节点识别、覆盖层构建等）
- 所有几何数据来自 preview_plot.PreviewDemoData 硬编码常量
- 预览仅用于观察样式参数在固定数据上的真实表现
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from typing import Any

from backend.utils.cache import TTLCache
from trace_pipeline.utils.paths import get_project_root

logger = logging.getLogger(__name__)
PREVIEW_DIR = get_project_root() / "cache" / "preview"
PREVIEW_DPI = 300

_PREVIEW_LOCK = threading.Lock()


def _hash_config(config: dict[str, Any]) -> str:
    """计算样式 + overlay 状态的哈希值，用于缓存键。"""
    # 提取影响预览的所有参数
    keys = ("style", "show_hull", "show_circles", "show_nodes")
    payload = {k: config.get(k) for k in keys}
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class PreviewService:
    """使用预设演示数据生成样式预览图，支持缓存。"""

    def __init__(self, sample_outcrop: str = "", **kwargs: Any) -> None:
        _ = sample_outcrop, kwargs
        self._cache = TTLCache(ttl=300.0, maxsize=50)
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    def generate(self, config: dict[str, Any]) -> dict[str, Any]:
        """生成预览图。"""
        style_hash = _hash_config(config)
        with _PREVIEW_LOCK:
            cached = self._cache.get(style_hash)
            if cached is not None:
                logger.info(
                    "预览缓存命中 [%s]",
                    style_hash[:8],
                    extra={"stage": "preview_cache_hit", "hash": style_hash},
                )
                return {"status": "ready", "paths": cached, "images": self._to_images(cached)}

        start = time.perf_counter()
        try:
            paths = self._generate_images(config, style_hash)
            with _PREVIEW_LOCK:
                self._cache.set(style_hash, paths)
            duration = (time.perf_counter() - start) * 1000
            logger.info(
                "预览生成完成 [%s]: %d 张图 (%.3f ms)",
                style_hash[:8],
                len(paths),
                duration,
                extra={
                    "stage": "preview_generate",
                    "hash": style_hash,
                    "image_count": len(paths),
                    "paths": paths,
                    "duration_ms": round(duration, 3),
                },
            )
            return {"status": "ready", "paths": paths, "images": self._to_images(paths)}
        except Exception as exc:
            duration = (time.perf_counter() - start) * 1000
            logger.exception(
                "预览生成失败 (%.3f ms)",
                duration,
                extra={
                    "stage": "preview_error",
                    "hash": style_hash,
                    "duration_ms": round(duration, 3),
                },
            )
            return {"status": "error", "message": str(exc)}

    def _to_images(self, paths: dict[str, str]) -> list[dict[str, str]]:
        """将路径字典转为结构化 images 数组。"""
        label_map = {
            "raw": "原始迹线图",
            "rotated": "旋转迹线图",
            "rose": "走向玫瑰图",
        }
        images = []
        for key, label in label_map.items():
            path = paths.get(key, "")
            if path:
                images.append({"key": key, "label": label, "path": path})
        return images

    def _generate_images(self, config: dict[str, Any], style_hash: str) -> dict[str, str]:
        """使用完全独立的 preview_plot 模块生成预览图。"""
        from trace_pipeline.plotting.preview_plot import (
            _DEMO_DATA,
            render_preview_rose,
            render_preview_trace,
        )
        from trace_pipeline.plotting.style import configure_style

        style = config.get("style", {})
        show_hull = config.get("show_hull", True)
        show_circles = config.get("show_circles", True)
        show_nodes = config.get("show_nodes", True)

        configure_style()

        demo = _DEMO_DATA

        raw_path = PREVIEW_DIR / f"preview_{style_hash}_raw.png"
        rotated_path = PREVIEW_DIR / f"preview_{style_hash}_rotated.png"
        rose_path = PREVIEW_DIR / f"preview_{style_hash}_rose.png"

        render_preview_trace(
            str(PREVIEW_DIR),
            raw_path.name,
            style,
            show_hull=show_hull,
            show_circles=show_circles,
            show_nodes=show_nodes,
            is_rotated=False,
            dpi=PREVIEW_DPI,
            demo=demo,
        )

        render_preview_trace(
            str(PREVIEW_DIR),
            rotated_path.name,
            style,
            show_hull=show_hull,
            show_circles=show_circles,
            show_nodes=show_nodes,
            is_rotated=True,
            dpi=PREVIEW_DPI,
            demo=demo,
        )

        rose_plot_path = ""
        if demo.joint_strikes.size:
            rose_plot_path = str(rose_path.resolve())
            render_preview_rose(
                str(PREVIEW_DIR),
                rose_path.name,
                style,
                dpi=PREVIEW_DPI,
                demo=demo,
            )

        return {
            "raw": str(raw_path.resolve()),
            "rotated": str(rotated_path.resolve()),
            "rose": rose_plot_path,
        }
