"""暴露给 JS 的 API 类。"""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import webview
from PIL import Image

from backend.services.audit_service import AuditService
from backend.services.config_service import ConfigService
from backend.services.data_service import DataService
from backend.services.file_service import FileService
from backend.services.log_service import LogService
from backend.services.pipeline_service import PipelineService
from backend.services.preview_service import PreviewService
from backend.services.report_service import REPORT_DIR, ReportService
from backend.services.stats_service import StatsService
from backend.utils.cache import DirectoryChangeDetector
from backend.utils.security import PathSecurityChecker
from trace_pipeline.logging import LogContext
from trace_pipeline.utils.paths import get_project_root

logger = logging.getLogger(__name__)
PROJECT_ROOT = get_project_root()
_ALLOWED_EXTERNAL_HOSTS = frozenset(
    {
        "developer.microsoft.com",
        "learn.microsoft.com",
        "go.microsoft.com",
        "aka.ms",
    }
)


class GuiApi:
    """pywebview JS API 入口。所有 public 方法均可被前端调用。

    内置简单的请求频率限制：对重资源操作（预览、报告生成、ZIP导出）
    使用运行锁，防止并发导致资源耗尽。

    服务采用分层初始化策略：
    - 启动必需（饥饿加载）：PathSecurityChecker, ConfigService, FileService, LogService
    - 按需懒加载（首次访问时创建）：PipelineService, PreviewService, StatsService,
      DataService, ReportService, AuditService
    """

    def __init__(self) -> None:
        import time

        t0 = time.perf_counter()
        # ---- 启动必需服务（饥饿加载） ----
        self._path_checker = PathSecurityChecker(PROJECT_ROOT)
        self._config = ConfigService()
        self._file = FileService()
        self._log = LogService()

        # ---- 按需懒加载服务 ----
        self._pipeline: PipelineService | None = None
        self._preview: PreviewService | None = None
        self._stats: StatsService | None = None
        self._data: DataService | None = None
        self._report: ReportService | None = None
        self._audit: AuditService | None = None

        self._window: Any = None
        self._user_selected_paths: set[Path] = set()
        self._window_maximized = False
        # 重资源操作的运行锁（线程安全）
        self._preview_lock = threading.Lock()
        self._report_lock = threading.Lock()
        # 报告导出进度队列（线程安全，前端轮询）
        self._report_progress_queue: deque[dict[str, Any]] = deque()
        self._report_progress_lock = threading.Lock()
        # output 目录变更检测器
        self._output_detector = DirectoryChangeDetector()
        self._sync_services_from_config(self._config.get())
        cfg = self._config.get()
        logger.info(
            "GuiApi 就绪 (%.3f ms): input=%s, output=%s",
            (time.perf_counter() - t0) * 1000,
            cfg.get("input_dir", ""),
            cfg.get("output_dir", ""),
            extra={
                "stage": "gui_api_init_done",
                "config_fields": list(cfg.keys()),
                "input_dir": cfg.get("input_dir"),
                "output_dir": cfg.get("output_dir"),
                "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
            },
        )

    # ---- 懒加载属性 ----
    @property
    def _pipeline_svc(self) -> PipelineService:
        if self._pipeline is None:
            self._pipeline = PipelineService()
        return self._pipeline

    @property
    def _preview_svc(self) -> PreviewService:
        if self._preview is None:
            self._preview = PreviewService()
        return self._preview

    @property
    def _stats_svc(self) -> StatsService:
        if self._stats is None:
            self._stats = StatsService()
        return self._stats

    @property
    def _data_svc(self) -> DataService:
        if self._data is None:
            self._data = DataService()
        return self._data

    @property
    def _report_svc(self) -> ReportService:
        if self._report is None:
            self._report = ReportService()
        return self._report

    @property
    def _audit_svc(self) -> AuditService:
        if self._audit is None:
            self._audit = AuditService()
        return self._audit

    def set_window(self, window: Any) -> None:
        self._window = window
        self._window_maximized = False

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _safe_path(self, path: str, base: Path | None = None) -> Path | None:
        """解析并校验路径在项目根目录内，防止路径遍历攻击。"""
        return self._path_checker.safe_path(path, base)

    def _safe_path_in_base(self, path: str, base: Path) -> Path | None:
        """校验路径位于指定可信目录内；可信目录可在项目根之外。"""
        return self._path_checker.safe_path(path, base, allow_external_base=True)

    def _resolve_configured_dir(self, key: str, default: str) -> Path:
        value = Path(self._config.get().get(key, default))
        if not value.is_absolute():
            value = PROJECT_ROOT / value
        return value.resolve()

    def _trusted_file_bases(self) -> list[Path]:
        return [
            PROJECT_ROOT,
            self._resolve_configured_dir("input_dir", "input"),
            self._resolve_configured_dir("output_dir", "output"),
            REPORT_DIR.resolve(),
        ]

    def _safe_known_path(self, path: str) -> Path | None:
        for base in self._trusted_file_bases():
            safe = self._safe_path_in_base(path, base)
            if safe is not None:
                return safe
        return None

    def _safe_user_selected_path(self, path: str, *, expect_dir: bool = False) -> Path | None:
        raw = Path(path)
        if not raw.is_absolute():
            return self._safe_known_path(path)
        try:
            resolved = raw.resolve().absolute()
        except (OSError, RuntimeError) as exc:
            logger.warning("用户选择路径解析失败 %s: %s", path, exc)
            return None
        if resolved not in self._user_selected_paths:
            logger.warning("拒绝未通过系统对话框登记的外部路径: %s", path)
            return None
        base = raw if expect_dir else raw.parent
        return self._safe_path_in_base(path, base)

    def _remember_user_selected_path(self, path: str) -> str:
        try:
            self._user_selected_paths.add(Path(path).resolve().absolute())
        except (OSError, RuntimeError) as exc:
            logger.warning("登记用户选择路径失败 %s: %s", path, exc)
        return path

    def _sync_services_from_config(self, cfg: dict[str, Any]) -> None:
        """用校验后的统一配置同步 FileService / DataService 路径。"""
        input_dir = cfg.get("input_dir", "input")
        output_dir = cfg.get("output_dir", "output")
        self._file.set_dirs(input_dir, output_dir)
        self._data_svc.update_dirs(output_dir, input_dir)

    def _invalidate_data_caches(self) -> None:
        self._file.invalidate_cache()
        self._stats_svc.invalidate_cache()
        self._output_detector.invalidate()

    def _resolve_output_dir(self) -> Path:
        out_dir = Path(self._config.get().get("output_dir", "output"))
        if not out_dir.is_absolute():
            out_dir = PROJECT_ROOT / out_dir
        return out_dir.resolve()

    def _check_output_changed(self) -> bool:
        """检测 output 目录是否发生了外部变更（如手动删除/添加文件）。

        返回 True 表示检测到变更，并已自动使后端缓存失效。
        """
        out_dir = self._resolve_output_dir()
        changed = self._output_detector.has_changed(out_dir)
        if changed:
            logger.info("检测到 output 目录变更，使缓存失效", extra={"stage": "output_dir_changed"})
            self._file.invalidate_cache()
            self._stats_svc.invalidate_cache()
        return changed

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        cfg = self._config.get()
        logger.debug(
            "get_config → %d 个字段",
            len(cfg),
            extra={"stage": "api_get_config", "field_count": len(cfg)},
        )
        return cfg

    def set_config(self, config: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit_svc.log("set_config", params={"keys": list(config.keys())})
        merged = self._config.set(config)
        self._sync_services_from_config(merged)
        self._invalidate_data_caches()
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "set_config 完成 → %d 个字段 (%.3f ms)",
            len(merged),
            duration,
            extra={
                "stage": "api_set_config",
                "field_count": len(merged),
                "changed_keys": list(config.keys()),
                "duration_ms": round(duration, 3),
            },
        )
        return merged

    def reset_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit_svc.log("reset_config")
        default = self._config.reset()
        self._sync_services_from_config(default)
        self._invalidate_data_caches()
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_config 完成 → 恢复默认 (%.3f ms)",
            duration,
            extra={"stage": "api_reset_config", "duration_ms": round(duration, 3)},
        )
        return default

    def reset_processing_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit_svc.log("reset_processing_config")
        cfg = self._config.reset_processing()
        self._sync_services_from_config(cfg)
        self._invalidate_data_caches()
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_processing_config 完成 (%.3f ms)",
            duration,
            extra={"stage": "api_reset_processing_config", "duration_ms": round(duration, 3)},
        )
        return cfg

    def reset_style_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit_svc.log("reset_style_config")
        cfg = self._config.reset_style()
        self._sync_services_from_config(cfg)
        self._invalidate_data_caches()
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_style_config 完成 (%.3f ms)",
            duration,
            extra={"stage": "api_reset_style_config", "duration_ms": round(duration, 3)},
        )
        return cfg

    # ------------------------------------------------------------------
    # 文件
    # ------------------------------------------------------------------
    def preload_fonts(self) -> dict[str, Any]:
        """预热 matplotlib 字体缓存与样式配置，减少首次绘图时的延迟。

        主动调用 configure_style() 触发 matplotlib 字体扫描与 rcParams 设置，
        而非仅读取已缓存的字体列表。这是启动画面中"准备渲染引擎"步骤的核心。
        """
        try:
            from trace_pipeline.plotting.style import _get_font_cache, configure_style

            # 主动触发 matplotlib 字体扫描与样式初始化
            configure_style()
            cache = _get_font_cache()
            return {
                "status": "ok",
                "cjk_serif": cache.get("cjk_serif", [])[:3],
                "cjk_sans": cache.get("cjk_sans", [])[:3],
                "western": cache.get("western", [])[:3],
            }
        except Exception as exc:
            logger.warning("字体缓存预热失败: %s", exc)
            return {"status": "error", "message": str(exc)}

    def scan_files(self, force=False) -> list[dict[str, Any]]:
        start = time.perf_counter()
        output_changed = self._check_output_changed()
        # 强制刷新或 output 变更时先使后端缓存失效，确保返回最新数据
        if force or output_changed:
            self._file.invalidate_cache()
            if output_changed:
                self._stats_svc.invalidate_cache()
        results = self._file.scan()
        duration = (time.perf_counter() - start) * 1000
        pending = sum(1 for r in results if r.get("status") == "pending")
        completed = sum(1 for r in results if r.get("status") == "completed")
        logger.info(
            "scan_files 完成: 共 %d 个文件 (待处理 %d / 已完成 %d) (%.3f ms)",
            len(results),
            pending,
            completed,
            duration,
            extra={
                "stage": "api_scan_files",
                "total": len(results),
                "pending": pending,
                "completed": completed,
                "duration_ms": round(duration, 3),
            },
        )
        return results

    # ------------------------------------------------------------------
    # 流水线
    # ------------------------------------------------------------------
    def run_pipeline(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        req_id = f"api-run-{int(time.perf_counter() * 1000)}"
        with LogContext(request_id=req_id):
            start = time.perf_counter()
            self._audit_svc.log(
                "run_pipeline",
                params={"targets": targets, "input_dir": config.get("input_dir", "")},
            )
            try:
                merged = {**self._config.get(), **config}
                saved = self._config.set(merged)
                self._sync_services_from_config(saved)
                # 流水线启动前使缓存失效，确保使用最新数据
                self._file.invalidate_cache()
                self._stats_svc.invalidate_cache()
                result = self._pipeline_svc.run(targets, saved)
                duration = (time.perf_counter() - start) * 1000
                logger.info(
                    "run_pipeline 完成 (%.3f ms)",
                    duration,
                    extra={
                        "stage": "api_run_pipeline",
                        "targets": targets,
                        "duration_ms": round(duration, 3),
                    },
                )
                return result
            except ValueError as exc:
                duration = (time.perf_counter() - start) * 1000
                logger.warning(
                    "流水线配置校验失败: %s (%.3f ms)",
                    exc,
                    duration,
                    extra={
                        "stage": "api_run_pipeline",
                        "error": str(exc),
                        "duration_ms": round(duration, 3),
                    },
                )
                return {"status": "error", "message": str(exc)}

    def poll_progress(self) -> dict[str, Any] | None:
        event = self._pipeline_svc.poll_progress()
        if event:
            logger.debug(
                "进度轮询 → %s: %s",
                event.get("type"),
                event.get("message", ""),
                extra={"stage": "poll_progress", "event": event},
            )
        return event

    # ------------------------------------------------------------------
    # 结果与统计
    # ------------------------------------------------------------------
    def get_results(self) -> list[dict[str, Any]]:
        """获取已完成的处理结果列表（通过扫描 output 目录）。"""
        from trace_pipeline.utils.output_paths import find_output_images

        self._check_output_changed()
        import re

        out_dir = self._resolve_output_dir()
        results = []
        raw_pattern = re.compile(r"^(.+)_raw\(n=\d+\)\.png$")
        for png in sorted(out_dir.glob("*.png")):
            match = raw_pattern.match(png.name)
            if not match:
                continue
            stem = match.group(1)
            images = find_output_images(out_dir, stem)
            results.append(
                {
                    "outcrop": stem,
                    "raw_plot": str(images["raw"].resolve()) if images["raw"] else "",
                    "rotated_plot": str(images["rotated"].resolve()) if images["rotated"] else "",
                    "rose_plot": str(images["rose"].resolve()) if images["rose"] else "",
                }
            )
        logger.debug(
            "get_results → %d 个结果",
            len(results),
            extra={
                "stage": "api_get_results",
                "result_count": len(results),
                "out_dir": str(out_dir),
            },
        )
        return results

    def get_stats(self, outcrop: str) -> dict[str, Any]:
        start = time.perf_counter()
        self._check_output_changed()
        result = self._stats_svc.get_stats(outcrop, self._config.get())
        duration = (time.perf_counter() - start) * 1000
        if "error" in result:
            logger.warning(
                "get_stats [%s] 失败: %s (%.3f ms)",
                outcrop,
                result["error"],
                duration,
                extra={
                    "stage": "api_get_stats",
                    "outcrop": outcrop,
                    "duration_ms": round(duration, 3),
                    "error": result["error"],
                },
            )
        else:
            logger.info(
                "get_stats [%s] 完成: trace_count=%s, P10=%.4f, P20=%.4f, P21=%.4f (%.3f ms)",
                outcrop,
                result.get("trace_count"),
                result.get("p10"),
                result.get("p20"),
                result.get("p21"),
                duration,
                extra={
                    "stage": "api_get_stats",
                    "outcrop": outcrop,
                    "trace_count": result.get("trace_count"),
                    "p10": result.get("p10"),
                    "p20": result.get("p20"),
                    "p21": result.get("p21"),
                    "window_strategy": result.get("window_strategy"),
                    "duration_ms": round(duration, 3),
                },
            )
        return result

    def get_comparison(self, outcrops: list[str]) -> list[dict[str, Any]]:
        start = time.perf_counter()
        self._check_output_changed()
        results = self._stats_svc.get_comparison(outcrops, self._config.get())
        duration = (time.perf_counter() - start) * 1000
        outcrops_str = ", ".join(outcrops[:10]) + ("..." if len(outcrops) > 10 else "")
        logger.info(
            "get_comparison [%s] 完成: %d/%d 个露头 (%.3f ms)",
            outcrops_str,
            len(results),
            len(outcrops),
            duration,
            extra={
                "stage": "api_get_comparison",
                "outcrops": outcrops[:50],
                "result_count": len(results),
                "duration_ms": round(duration, 3),
            },
        )
        return results

    # ------------------------------------------------------------------
    # 数据页
    # ------------------------------------------------------------------
    def get_data(
        self, outcrop: str, section: str, page: int = 1, page_size: int = 20, source: str = "output"
    ) -> dict[str, Any]:
        start = time.perf_counter()
        result = self._data_svc.get_data(outcrop, section, page, page_size, source)
        duration = (time.perf_counter() - start) * 1000
        if "error" in result:
            logger.warning(
                "get_data [%s/%s] 失败: %s (%.3f ms)",
                outcrop,
                section,
                result["error"],
                duration,
                extra={
                    "stage": "api_get_data",
                    "outcrop": outcrop,
                    "section": section,
                    "source": source,
                    "duration_ms": round(duration, 3),
                    "error": result["error"],
                },
            )
        else:
            logger.debug(
                "get_data [%s/%s] page=%d: %d/%d 条记录 (%.3f ms)",
                outcrop,
                section,
                page,
                len(result.get("data", [])),
                result.get("total", 0),
                duration,
                extra={
                    "stage": "api_get_data",
                    "outcrop": outcrop,
                    "section": section,
                    "source": source,
                    "page": page,
                    "page_size": page_size,
                    "total": result.get("total", 0),
                    "returned": len(result.get("data", [])),
                    "duration_ms": round(duration, 3),
                },
            )
        return result

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------
    def generate_preview(self, config: dict[str, Any]) -> dict[str, Any]:
        if not self._preview_lock.acquire(blocking=False):
            logger.warning(
                "generate_preview 被拒绝: 已有预览任务正在运行",
                extra={"stage": "api_preview_reject"},
            )
            return {"status": "busy", "message": "已有预览任务正在运行"}
        try:
            merged = {**self._config.get(), **config}
            result = self._preview_svc.generate(merged)
            status = result.get("status", "unknown")
            img_count = len(result.get("images", []))
            logger.info(
                "generate_preview → status=%s, %d 张预览图",
                status,
                img_count,
                extra={
                    "stage": "api_preview",
                    "status": status,
                    "image_count": img_count,
                    "style_keys": list(merged.get("style", {}).keys()),
                },
            )
            return result
        finally:
            self._preview_lock.release()

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def get_logs(self, tail: int = 100, level: str = "INFO") -> list[str]:
        return self._log.get_logs(tail, level)

    # ------------------------------------------------------------------
    # 毕设功能（开发者选项）
    # ------------------------------------------------------------------
    def poll_report_progress(self) -> dict[str, Any] | None:
        """前端轮询报告导出进度，非阻塞。"""
        with self._report_progress_lock:
            return self._report_progress_queue.popleft() if self._report_progress_queue else None

    def generate_report(
        self, outcrop: str, report_type: str, fmt: str, save_path: str | None = None
    ) -> dict[str, Any]:
        logger.info(
            "generate_report 调用: outcrop=%s type=%s fmt=%s save_path=%s",
            outcrop,
            report_type,
            fmt,
            save_path,
            extra={"stage": "api_generate_report_call"},
        )
        if not self._report_lock.acquire(blocking=False):
            logger.warning(
                "generate_report 被拒绝: 已有报告任务正在运行", extra={"stage": "api_report_reject"}
            )
            return {"status": "busy", "message": "已有报告任务正在运行"}
        try:
            self._audit_svc.log(
                "generate_report",
                params={
                    "outcrop": outcrop,
                    "type": report_type,
                    "fmt": fmt,
                    "save_path": save_path,
                },
            )
            # 清空上次的进度队列
            with self._report_progress_lock:
                self._report_progress_queue.clear()

            def _report_progress(step: str, message: str) -> None:
                with self._report_progress_lock:
                    self._report_progress_queue.append({
                        "type": "progress",
                        "step": step,
                        "message": message,
                        "outcrop": outcrop,
                    })

            result = self._report_svc.generate(
                outcrop, report_type, fmt, self._config.get(),
                progress_callback=_report_progress,
            )
            with self._report_progress_lock:
                self._report_progress_queue.append({"type": "complete"})
            logger.info(
                "generate_report 生成结果: outcrop=%s result_keys=%s",
                outcrop,
                list(result.keys()),
                extra={"stage": "api_generate_report_result", "outcrop": outcrop, "result": result},
            )
            if "error" in result:
                return result
            if save_path:
                safe_dest = self._safe_user_selected_path(save_path)
                if safe_dest is None:
                    logger.warning("generate_report 拒绝越权保存路径: %s", save_path)
                    return {"error": "保存路径越权"}
                key = "docx" if fmt == "docx" else "pdf"
                src_path = result.get(key)
                if not src_path:
                    return {"error": f"未生成 {key.upper()} 报告"}
                src_safe = self._safe_known_path(src_path)
                if src_safe is None or not src_safe.exists():
                    return {"error": "报告源文件不存在或路径越权"}
                safe_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src_safe), str(safe_dest))
                copied_path = str(safe_dest.resolve())
                logger.info(
                    "generate_report 复制完成: %s -> %s",
                    src_safe,
                    safe_dest,
                    extra={
                        "stage": "api_generate_report_copied",
                        "outcrop": outcrop,
                        "path": copied_path,
                    },
                )
                return {"path": str(safe_dest.resolve()), "format": key}
            return result
        except Exception as exc:
            logger.exception("generate_report 异常: %s", exc)
            with self._report_progress_lock:
                self._report_progress_queue.append({"type": "error", "message": str(exc)})
            return {"error": f"生成报告失败: {exc}"}
        finally:
            self._report_lock.release()

    def generate_reports_zip(
        self, targets: list[str], report_type: str, fmt: str, save_path: str | None = None
    ) -> dict[str, Any]:
        import zipfile
        from datetime import datetime

        logger.info(
            "generate_reports_zip 调用: targets=%s type=%s fmt=%s save_path=%s",
            targets,
            report_type,
            fmt,
            save_path,
            extra={"stage": "api_generate_reports_zip_call"},
        )
        # 与 generate_report 共用 _report_lock:避免并发写入同名 {outcrop}_report.docx 中间产物
        if not self._report_lock.acquire(blocking=False):
            logger.warning(
                "generate_reports_zip 被拒绝: 已有报告任务正在运行",
                extra={"stage": "api_report_reject"},
            )
            return {"status": "busy", "message": "已有报告任务正在运行"}
        try:
            self._audit_svc.log(
                "generate_reports_zip", params={"targets": targets, "type": report_type, "fmt": fmt}
            )
            # 清空上次的进度队列
            with self._report_progress_lock:
                self._report_progress_queue.clear()

            total = len(targets)
            cfg = self._config.get()
            files = []
            errors = []

            for idx, oc in enumerate(targets, 1):
                # 为每个露头创建进度闭包
                def _make_progress(outcrop_name: str, current: int) -> Any:
                    def _cb(step: str, message: str) -> None:
                        with self._report_progress_lock:
                            self._report_progress_queue.append({
                                "type": "progress",
                                "step": step,
                                "message": message,
                                "outcrop": outcrop_name,
                                "current": current,
                                "total": total,
                            })
                    return _cb

                progress_cb = _make_progress(oc, idx)
                res = self._report_svc.generate(oc, report_type, fmt, cfg, progress_callback=progress_cb)
                if "error" in res:
                    errors.append(f"{oc}: {res['error']}")
                    continue
                if "docx" in res and res["docx"]:
                    files.append(res["docx"])
                if "pdf" in res and res["pdf"]:
                    files.append(res["pdf"])

            if not files:
                detail = "; ".join(errors)
                return {"error": f"没有生成任何报告{( ': ' + detail) if detail else ''}"}

            # 打包 ZIP
            with self._report_progress_lock:
                self._report_progress_queue.append({
                    "type": "progress",
                    "step": "zip",
                    "message": "正在打包 ZIP 压缩包...",
                })

            zip_path: Path
            if save_path:
                safe = self._safe_user_selected_path(save_path)
                if safe is None:
                    logger.warning("generate_reports_zip 拒绝越权保存路径: %s", save_path)
                    return {"error": "保存路径越权"}
                zip_path = safe
                zip_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                REPORT_DIR.mkdir(parents=True, exist_ok=True)
                zip_path = REPORT_DIR / f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            # 报告产物只允许来自受信目录；保存位置来自系统对话框时可在项目外。
            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for f in files:
                        # 校验完整路径（而非仅文件名），防止路径遍历绕过
                        fp_safe = self._safe_known_path(f)
                        if fp_safe is None:
                            logger.warning("ZIP 中跳过越权路径: %s", f)
                            continue
                        if not fp_safe.exists():
                            logger.warning("ZIP 中跳过不存在的文件: %s", f)
                            continue
                        zf.write(str(fp_safe), arcname=fp_safe.name)
            except Exception as exc:
                logger.warning("ZIP 创建失败: %s", exc)
                return {"error": f"ZIP 创建失败: {exc}"}

            for f in files:
                # 安全校验后再删除，仅允许删除安全基准内的文件
                fp_clean = self._safe_known_path(f)
                if fp_clean is None or not fp_clean.exists():
                    logger.debug("跳过清理越权/不存在文件: %s", f)
                    continue
                try:
                    os.remove(str(fp_clean))
                except Exception as exc:
                    logger.debug("清理中间文件失败: %s → %s", f, exc)

            return {"zip_path": str(zip_path.resolve()), "count": len(files), "errors": errors}
        except Exception as exc:
            logger.exception("generate_reports_zip 异常: %s", exc)
            with self._report_progress_lock:
                self._report_progress_queue.append({"type": "error", "message": str(exc)})
            return {"error": f"生成报告压缩包失败: {exc}"}
        finally:
            with self._report_progress_lock:
                self._report_progress_queue.append({"type": "complete"})
            self._report_lock.release()

    def get_provenance(self, outcrop: str) -> dict[str, Any]:
        """数据溯源：返回 P10/P20/P21 的计算来源链。"""
        stats = self._stats_svc.get_stats(outcrop, self._config.get())
        if "error" in stats:
            return stats
        ns = stats.get("nodes_summary", {})
        logger.debug(
            "get_provenance [%s]",
            outcrop,
            extra={
                "stage": "api_provenance",
                "outcrop": outcrop,
                "area_source": stats.get("area_source"),
            },
        )
        return {
            "outcrop": outcrop,
            "p10": {"value": stats.get("p10"), "source": "实测测线"},
            "p20": {"value": stats.get("p20"), "source": stats.get("area_source", "unknown")},
            "p21": {"value": stats.get("p21"), "source": stats.get("area_source", "unknown")},
            "area_source": stats.get("area_source"),
            "warning": stats.get("warning"),
            "nodes": {
                "merge_tolerance": ns.get("merge_tolerance") if isinstance(ns, dict) else None,
                "node_count": ns.get("node_count") if isinstance(ns, dict) else None,
                "intersection_count": ns.get("intersection_count")
                if isinstance(ns, dict)
                else None,
            },
        }

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        logs = self._audit_svc.get(limit)
        logger.debug(
            "get_audit_log → %d 条记录",
            len(logs),
            extra={"stage": "api_audit_log", "count": len(logs), "limit": limit},
        )
        return logs

    # ------------------------------------------------------------------
    # 系统
    # ------------------------------------------------------------------
    def open_external(self, url: str) -> bool:
        """Open a trusted external URL in the system browser."""
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"}:
            logger.warning("open_external 拒绝非 HTTP(S) URL: %s", url)
            return False
        hostname = (parsed.hostname or "").lower()
        if hostname not in _ALLOWED_EXTERNAL_HOSTS:
            logger.warning(
                "open_external 拒绝未授权域名: %s",
                hostname,
                extra={"stage": "api_open_external", "url": url, "hostname": hostname},
            )
            return False
        try:
            import webbrowser

            return webbrowser.open(url)
        except Exception as exc:
            logger.warning(
                "open_external 失败: %s",
                exc,
                extra={"stage": "api_open_external", "error": str(exc)},
            )
            return False

    def open_directory(self, path: str) -> bool:
        """打开指定目录（支持相对路径，限制在项目根目录内）。"""
        target = self._safe_known_path(path)
        if target is None or not target.exists():
            logger.warning(
                "open_directory 失败: 路径无效或不存在 → %s",
                path,
                extra={"stage": "api_open_dir", "path": path},
            )
            return False
        if not target.is_dir():
            logger.warning(
                "open_directory 失败: 目标不是目录 → %s",
                path,
                extra={"stage": "api_open_dir", "path": path},
            )
            return False
        try:
            if sys.platform == "win32":
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
            logger.info(
                "open_directory → %s", target, extra={"stage": "api_open_dir", "path": str(target)}
            )
            return True
        except Exception as exc:
            logger.warning(
                "打开目录失败: %s → %s",
                path,
                exc,
                extra={"stage": "api_open_dir", "path": path, "error": str(exc)},
            )
            return False

    # 图片读取上限：5MB，防止大图片导致内存溢出
    _MAX_IMAGE_SIZE = 5 * 1024 * 1024
    # 安全的图片扩展名白名单（禁止 SVG 防止 XSS；禁止 html/htm 等）
    _SAFE_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
        {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    )
    _IMAGE_MIME_TYPES: dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }
    _MIN_THUMBNAIL_PX = 64
    _MAX_THUMBNAIL_PX = 1600

    def _safe_image_path(self, path: str, stage: str) -> tuple[Path, os.stat_result, str] | None:
        p = self._safe_known_path(path)
        if p is None or not p.exists():
            logger.warning(
                "图片读取失败: 路径无效或不存在 -> %s",
                path,
                extra={"stage": stage, "path": path},
            )
            return None
        stat = p.stat()
        if stat.st_size > self._MAX_IMAGE_SIZE:
            logger.warning(
                "图片读取拒绝: 文件过大 %s (%d bytes > %d limit)",
                path,
                stat.st_size,
                self._MAX_IMAGE_SIZE,
                extra={"stage": stage, "path": path, "size_bytes": stat.st_size},
            )
            return None
        ext = p.suffix.lower()
        if ext not in self._SAFE_IMAGE_EXTENSIONS:
            logger.warning(
                "图片读取拒绝: 不安全的文件扩展名 %s",
                ext,
                extra={"stage": stage, "path": path, "ext": ext},
            )
            return None
        return p, stat, ext

    def get_image_meta(self, path: str) -> dict[str, Any]:
        """返回图片版本元数据，用于前端缓存失效；不读取图片内容。"""
        try:
            resolved = self._safe_image_path(path, "api_get_image_meta")
            if resolved is None:
                return {}
            p, stat, ext = resolved
            return {
                "path": str(p.resolve()),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "ext": ext,
            }
        except Exception as exc:
            logger.warning(
                "读取图片元数据失败: %s -> %s",
                path,
                exc,
                extra={"stage": "api_get_image_meta", "path": path, "error": str(exc)},
            )
            return {}

    def get_image_data(self, path: str) -> dict[str, Any]:
        """返回图片 base64 data URL 及文件元数据（单次调用替代 meta+image）。"""
        try:
            resolved = self._safe_image_path(path, "api_get_image_data")
            if resolved is None:
                return {}
            p, stat, ext = resolved
            with open(p, "rb") as f:
                data = f.read()
            mime = self._IMAGE_MIME_TYPES[ext]
            b64 = base64.b64encode(data).decode("utf-8")
            logger.debug(
                "get_image_data → %s (%d bytes)",
                path,
                len(data),
                extra={"stage": "api_get_image_data", "path": path, "size_bytes": len(data)},
            )
            return {
                "data": f"data:{mime};base64,{b64}",
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
            }
        except Exception as exc:
            logger.warning(
                "读取图片数据失败: %s → %s",
                path,
                exc,
                extra={"stage": "api_get_image_data", "path": path, "error": str(exc)},
            )
            return {}

    def get_image(self, path: str) -> str:
        """读取图片文件并返回 base64 data URL。限制在项目根目录内，单文件上限 5MB。"""
        try:
            # 强制以 PROJECT_ROOT 为 base，防止通过修改 output_dir 配置绕过路径限制
            resolved = self._safe_image_path(path, "api_get_image")
            if resolved is None:
                return ""
            p, _, ext = resolved
            with open(p, "rb") as f:
                data = f.read()
            mime = self._IMAGE_MIME_TYPES[ext]
            b64 = base64.b64encode(data).decode("utf-8")
            logger.debug(
                "get_image → %s (%d bytes)",
                path,
                len(data),
                extra={"stage": "api_get_image", "path": path, "size_bytes": len(data)},
            )
            return f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.warning(
                "读取图片失败: %s → %s",
                path,
                exc,
                extra={"stage": "api_get_image", "path": path, "error": str(exc)},
            )
            return ""

    def get_image_thumbnail(self, path: str, max_px: int = 480) -> str:
        """生成图片缩略图并返回 PNG data URL。沿用图片读取安全限制。"""
        try:
            resolved = self._safe_image_path(path, "api_get_image_thumbnail")
            if resolved is None:
                return ""
            p, stat, _ = resolved
            try:
                requested_max_px = int(max_px)
            except (TypeError, ValueError):
                requested_max_px = 480
            safe_max_px = max(
                self._MIN_THUMBNAIL_PX,
                min(requested_max_px, self._MAX_THUMBNAIL_PX),
            )
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            with Image.open(p) as img:
                img.thumbnail((safe_max_px, safe_max_px), resampling)
                has_alpha = img.mode in {"RGBA", "LA"} or "transparency" in img.info
                if img.mode not in {"RGB", "RGBA"}:
                    img = img.convert("RGBA" if has_alpha else "RGB")
                with BytesIO() as output:
                    img.save(output, format="PNG", optimize=True)
                    data = output.getvalue()
            b64 = base64.b64encode(data).decode("utf-8")
            logger.debug(
                "get_image_thumbnail → %s (%d -> %d bytes)",
                path,
                stat.st_size,
                len(data),
                extra={
                    "stage": "api_get_image_thumbnail",
                    "path": path,
                    "source_size_bytes": stat.st_size,
                    "encoded_size_bytes": len(data),
                    "max_px": safe_max_px,
                },
            )
            return f"data:image/png;base64,{b64}"
        except Exception as exc:
            logger.warning(
                "读取图片缩略图失败: %s → %s",
                path,
                exc,
                extra={"stage": "api_get_image_thumbnail", "path": path, "error": str(exc)},
            )
            return ""

    def ask_save_path(
        self, default_name: str = "reports.zip", file_filter: str = "ZIP 文件 (*.zip)"
    ) -> str:
        """打开系统另存为对话框，返回用户选择的保存路径（包含文件名）。用户取消时返回空字符串。"""
        if self._window is None:
            logger.warning(
                "ask_save_path 失败: window 未初始化", extra={"stage": "api_ask_save_path"}
            )
            return ""
        try:
            file_types: tuple[str, ...] = ()
            if file_filter:
                # pywebview 官方文档推荐 tuple；tuple 可避免个别版本把 list 当作无效 filter
                file_types = (file_filter,)
            result = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                allow_multiple=False,
                save_filename=default_name,
                file_types=file_types,
            )
            logger.debug(
                "ask_save_path 原始返回值: type=%s value=%s",
                type(result).__name__,
                result,
                extra={"stage": "api_ask_save_path", "raw_result": str(result)},
            )
            if isinstance(result, (list, tuple)) and result:
                chosen = str(result[0])
                self._remember_user_selected_path(chosen)
                logger.info(
                    "ask_save_path → %s",
                    chosen,
                    extra={"stage": "api_ask_save_path", "selected": chosen},
                )
                return chosen
            if isinstance(result, str):
                chosen = str(result)
                self._remember_user_selected_path(chosen)
                logger.info(
                    "ask_save_path → %s",
                    chosen,
                    extra={"stage": "api_ask_save_path", "selected": chosen},
                )
                return chosen
            logger.debug("ask_save_path → 用户取消选择", extra={"stage": "api_ask_save_path"})
            return ""
        except Exception as exc:
            logger.warning(
                "ask_save_path 失败: %s",
                exc,
                extra={"stage": "api_ask_save_path", "error": str(exc)},
            )
            return ""

    def browse_folder(self) -> str:
        """打开系统文件夹选择对话框，返回选中的路径。"""
        if self._window is None:
            logger.warning(
                "browse_folder 失败: window 未初始化", extra={"stage": "api_browse_folder"}
            )
            return ""
        try:
            result = self._window.create_file_dialog(
                webview.FileDialog.FOLDER, allow_multiple=False
            )
            if isinstance(result, (list, tuple)) and result:
                chosen = str(result[0])
                self._remember_user_selected_path(chosen)
                logger.info(
                    "browse_folder → %s",
                    chosen,
                    extra={"stage": "api_browse_folder", "selected": chosen},
                )
                return chosen
            if isinstance(result, str):
                self._remember_user_selected_path(result)
                logger.info(
                    "browse_folder → %s",
                    result,
                    extra={"stage": "api_browse_folder", "selected": result},
                )
                return result
            logger.debug("browse_folder → 用户取消选择", extra={"stage": "api_browse_folder"})
            return ""
        except Exception as exc:
            logger.warning(
                "浏览文件夹失败: %s", exc, extra={"stage": "api_browse_folder", "error": str(exc)}
            )
            return ""

    def export_config_json(self, folder: str, content: str) -> bool:
        """将 JSON 内容写入指定文件夹的 config.json 文件。限制在项目根目录内，并执行配置校验。"""
        try:
            folder_path = self._safe_user_selected_path(folder, expect_dir=True)
            if folder_path is None:
                logger.warning(
                    "export_config_json 失败: 路径越权 → %s",
                    folder,
                    extra={"stage": "api_export_config", "folder": folder},
                )
                return False
            path = folder_path / "config.json"
            parsed = json.loads(content)
            # 深度校验：复用 validate_config 确保字段合法
            from trace_pipeline.config import validate_config

            validated = validate_config(parsed)
            path.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
            self._audit_svc.log("export_config_json", params={"path": str(path)})
            logger.info(
                "export_config_json → %s",
                path,
                extra={
                    "stage": "api_export_config",
                    "path": str(path),
                    "field_count": len(validated),
                },
            )
            return True
        except Exception as exc:
            logger.warning(
                "导出配置失败: %s → %s",
                folder,
                exc,
                extra={"stage": "api_export_config", "folder": folder, "error": str(exc)},
            )
            return False

    def shutdown_pipeline(self) -> None:
        """应用关闭前调用，确保后台流水线优雅结束。"""
        self._pipeline_svc.shutdown(timeout=30.0)

    # ------------------------------------------------------------------
    # 窗口控制（无边框窗口支持）
    # ------------------------------------------------------------------
    def window_minimize(self) -> bool:
        """最小化窗口。"""
        if self._window is None:
            return False
        try:
            self._window.minimize()
            return True
        except Exception as exc:
            logger.warning(
                "window_minimize 失败: %s",
                exc,
                extra={"stage": "api_window_minimize", "error": str(exc)},
            )
            return False

    def window_maximize(self) -> bool:
        """最大化/还原窗口切换。"""
        if self._window is None:
            return False
        try:
            # 使用内部状态跟踪，pywebview 的 maximized 属性在 Windows 上不可靠
            if self._window_maximized:
                self._window.restore()
                self._window_maximized = False
            else:
                self._window.maximize()
                self._window_maximized = True
            return True
        except Exception as exc:
            logger.warning(
                "window_maximize 失败: %s",
                exc,
                extra={"stage": "api_window_maximize", "error": str(exc)},
            )
            return False

    def window_resize(self, width: int, height: int) -> bool:
        """调整窗口尺寸（用于自定义 resize grip）。"""
        if self._window is None:
            return False
        try:
            # 确保最小尺寸
            w = max(1000, width)
            h = max(600, height)
            self._window.resize(w, h)
            return True
        except Exception as exc:
            logger.debug(
                "window_resize 失败: %s",
                exc,
                extra={"stage": "api_window_resize", "error": str(exc)},
            )
            return False

    def window_close(self) -> bool:
        """关闭窗口。"""
        if self._window is None:
            return False
        try:
            self._window.destroy()
            return True
        except Exception as exc:
            logger.warning(
                "window_close 失败: %s", exc, extra={"stage": "api_window_close", "error": str(exc)}
            )
            return False

    def window_move_by(self, dx: int, dy: int) -> bool:
        """相对移动窗口位置（用于自定义标题栏拖拽）。"""
        if self._window is None:
            return False
        try:
            current_x = self._window.x
            current_y = self._window.y
            self._window.move(current_x + dx, current_y + dy)
            return True
        except Exception as exc:
            logger.debug(
                "window_move_by 失败: %s",
                exc,
                extra={"stage": "api_window_move", "error": str(exc)},
            )
            return False

    def window_position(self) -> dict[str, int]:
        """获取窗口当前位置。"""
        if self._window is None:
            return {"x": 0, "y": 0}
        try:
            return {"x": self._window.x, "y": self._window.y}
        except Exception as exc:
            logger.debug(
                "window_position 失败: %s",
                exc,
                extra={"stage": "api_window_position", "error": str(exc)},
            )
            return {"x": 0, "y": 0}

    def window_move_to(self, x: int, y: int) -> bool:
        """绝对移动窗口到指定位置（用于自定义标题栏拖拽，避免增量抖动）。"""
        if self._window is None:
            return False
        try:
            self._window.move(x, y)
            return True
        except Exception as exc:
            logger.debug(
                "window_move_to 失败: %s",
                exc,
                extra={"stage": "api_window_move_to", "error": str(exc)},
            )
            return False

    def window_is_maximized(self) -> bool:
        """查询窗口是否已最大化。"""
        return self._window_maximized

    def check_webview2(self) -> dict[str, Any]:
        from backend.webview2_checker import WebView2Checker

        checker = WebView2Checker()
        installed = checker.is_installed()
        logger.debug(
            "check_webview2 → installed=%s",
            installed,
            extra={"stage": "api_check_webview2", "installed": installed},
        )
        return {"installed": installed, "url": checker.get_download_url()}
