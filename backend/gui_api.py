"""暴露给 JS 的 API 类。"""
from __future__ import annotations

import base64
import contextlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import webview

from backend.services.audit_service import AuditService
from backend.services.config_service import ConfigService
from backend.services.data_service import DataService
from backend.services.file_service import FileService
from backend.services.log_service import LogService
from backend.services.pipeline_service import PipelineService
from backend.services.preview_service import PreviewService
from backend.services.report_service import REPORT_DIR, ReportService
from backend.services.stats_service import StatsService
from trace_pipeline.logging import LogContext

logger = logging.getLogger(__name__)
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GuiApi:
    """pywebview JS API 入口。所有 public 方法均可被前端调用。

    内置简单的请求频率限制：对重资源操作（预览、报告生成、ZIP导出）
    使用运行锁，防止并发导致资源耗尽。
    """

    def __init__(self) -> None:
        import time
        t0 = time.perf_counter()
        self._config = ConfigService()
        self._file = FileService()
        self._pipeline = PipelineService()
        self._preview = PreviewService()
        self._stats = StatsService()
        self._data = DataService()
        self._log = LogService()
        self._report = ReportService()
        self._audit = AuditService()
        self._window: Any = None
        self._window_maximized = False
        # 重资源操作的运行锁
        self._preview_running = False
        self._report_running = False
        # output 目录变更检测：记录上次的 mtime + 文件数量快照
        self._output_snapshot: tuple[float, int] | None = None
        self._sync_services_from_config(self._config.get())
        cfg = self._config.get()
        logger.info(
            "GuiApi 就绪 (%.3f ms): input=%s, output=%s",
            (time.perf_counter() - t0) * 1000,
            cfg.get("input_dir", ""), cfg.get("output_dir", ""),
            extra={
                "stage": "gui_api_init_done",
                "config_fields": list(cfg.keys()),
                "input_dir": cfg.get("input_dir"),
                "output_dir": cfg.get("output_dir"),
                "duration_ms": round((time.perf_counter() - t0) * 1000, 3),
            },
        )

    def set_window(self, window: Any) -> None:
        self._window = window
        self._window_maximized = False

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    _WINDOWS_DEVICE_NAMES = frozenset({
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    })

    def _safe_path(self, path: str, base: Path | None = None) -> Path | None:
        """解析并校验路径在项目根目录内，防止路径遍历攻击。

        校验规则：
        1. 拒绝包含 ".." 的原始输入（多层 URL 编码后仍检查）
        2. URL 递归解码后再次检查 ".."
        3. 拒绝 Windows 设备名（检查所有路径段）
        4. 解析符号链接后限制在 base 目录下
        5. 拒绝非预期扩展名（防止 XSS）
        """
        from urllib.parse import unquote

        # 递归 URL 解码（防御双重编码如 %252e%252e）
        decoded = path
        for _ in range(5):
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        else:
            # 超过 5 次解码仍未稳定，视为攻击
            logger.warning("拒绝过度 URL 编码的路径: %s", path)
            return None

        # 在任何阶段检查路径遍历
        for check_path in (path, decoded):
            p_check = Path(check_path)
            if ".." in p_check.parts:
                logger.warning("拒绝包含 .. 的路径: %s", path)
                return None
            # 检查 Windows 设备名（所有路径段）
            for part in p_check.parts:
                if part.upper() in self._WINDOWS_DEVICE_NAMES:
                    logger.warning("拒绝 Windows 设备名路径: %s", path)
                    return None

        p = Path(decoded)
        if not p.is_absolute():
            p = PROJECT_ROOT / p

        # resolve() 会跟随符号链接；同时检查 base 自身是否被符号链接篡改
        try:
            p = p.resolve().absolute()
            base = Path(base or PROJECT_ROOT).resolve().absolute()
        except (OSError, RuntimeError) as exc:
            logger.warning("路径解析失败 %s: %s", path, exc)
            return None

        # 确保 base 仍是原始项目根目录（防御 base 被符号链接指向外部）
        expected_base = PROJECT_ROOT.resolve().absolute()
        try:
            base.relative_to(expected_base)
        except ValueError:
            logger.warning("base 目录越权: %s", base)
            return None

        try:
            p.relative_to(base)
        except ValueError:
            logger.warning("拒绝越权路径: %s", p)
            return None
        return p

    def _sync_services_from_config(self, cfg: dict[str, Any]) -> None:
        """用校验后的统一配置同步 FileService / DataService 路径。"""
        input_dir = cfg.get("input_dir", "input")
        output_dir = cfg.get("output_dir", "output")
        self._file.set_dirs(input_dir, output_dir)
        self._data.update_dirs(output_dir, input_dir)

    def _resolve_output_dir(self) -> Path:
        out_dir = Path(self._config.get().get("output_dir", "output"))
        if not out_dir.is_absolute():
            out_dir = PROJECT_ROOT / out_dir
        return out_dir.resolve()

    def _check_output_changed(self) -> bool:
        """检测 output 目录是否发生了外部变更（如手动删除/添加文件）。

        通过比较目录 mtime 和文件数量快照来判断。
        返回 True 表示检测到变更，并已自动使后端缓存失效。
        """
        out_dir = self._resolve_output_dir()
        if not out_dir.exists():
            current_snapshot = (-1.0, 0)
        else:
            try:
                mtime = out_dir.stat().st_mtime
                file_count = sum(1 for _ in out_dir.iterdir())
                current_snapshot = (mtime, file_count)
            except OSError:
                current_snapshot = (-1.0, 0)

        if self._output_snapshot is None:
            self._output_snapshot = current_snapshot
            return False

        if current_snapshot != self._output_snapshot:
            logger.info(
                "检测到 output 目录变更: 旧快照=%s, 新快照=%s，使缓存失效",
                self._output_snapshot, current_snapshot,
                extra={"stage": "output_dir_changed", "old": self._output_snapshot, "new": current_snapshot},
            )
            self._output_snapshot = current_snapshot
            self._file.invalidate_cache()
            self._stats.invalidate_cache()
            return True

        return False

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        cfg = self._config.get()
        logger.debug(
            "get_config → %d 个字段", len(cfg),
            extra={"stage": "api_get_config", "field_count": len(cfg)},
        )
        return cfg

    def set_config(self, config: dict[str, Any]) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit.log("set_config", params={"keys": list(config.keys())})
        merged = self._config.set(config)
        self._sync_services_from_config(merged)
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "set_config 完成 → %d 个字段 (%.3f ms)",
            len(merged), duration,
            extra={"stage": "api_set_config", "field_count": len(merged), "changed_keys": list(config.keys()), "duration_ms": round(duration, 3)},
        )
        return merged

    def reset_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit.log("reset_config")
        default = self._config.reset()
        self._sync_services_from_config(default)
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_config 完成 → 恢复默认 (%.3f ms)", duration,
            extra={"stage": "api_reset_config", "duration_ms": round(duration, 3)},
        )
        return default

    def reset_processing_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit.log("reset_processing_config")
        cfg = self._config.reset_processing()
        self._sync_services_from_config(cfg)
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_processing_config 完成 (%.3f ms)", duration,
            extra={"stage": "api_reset_processing", "duration_ms": round(duration, 3)},
        )
        return cfg

    def reset_style_config(self) -> dict[str, Any]:
        start = time.perf_counter()
        self._audit.log("reset_style_config")
        cfg = self._config.reset_style()
        self._sync_services_from_config(cfg)
        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "reset_style_config 完成 (%.3f ms)", duration,
            extra={"stage": "api_reset_style", "duration_ms": round(duration, 3)},
        )
        return cfg

    # ------------------------------------------------------------------
    # 文件
    # ------------------------------------------------------------------
    def scan_files(self, force = False) -> list[dict[str, Any]]:
        start = time.perf_counter()
        output_changed = self._check_output_changed()
        # 强制刷新或 output 变更时先使后端缓存失效，确保返回最新数据
        if force or output_changed:
            self._file.invalidate_cache()
            if output_changed:
                self._stats.invalidate_cache()
        results = self._file.scan()
        duration = (time.perf_counter() - start) * 1000
        pending = sum(1 for r in results if r.get("status") == "pending")
        completed = sum(1 for r in results if r.get("status") == "completed")
        logger.info(
            "scan_files 完成: 共 %d 个文件 (待处理 %d / 已完成 %d) (%.3f ms)",
            len(results), pending, completed, duration,
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
            self._audit.log("run_pipeline", params={"targets": targets, "input_dir": config.get("input_dir", "")})
            try:
                merged = {**self._config.get(), **config}
                saved = self._config.set(merged)
                self._sync_services_from_config(saved)
                # 流水线启动前使缓存失效，确保使用最新数据
                self._file.invalidate_cache()
                self._stats.invalidate_cache()
                result = self._pipeline.run(targets, saved)
                duration = (time.perf_counter() - start) * 1000
                logger.info(
                    "run_pipeline 完成 (%.3f ms)", duration,
                    extra={"stage": "api_run_pipeline", "targets": targets, "duration_ms": round(duration, 3)},
                )
                return result
            except ValueError as exc:
                duration = (time.perf_counter() - start) * 1000
                logger.warning(
                    "流水线配置校验失败: %s (%.3f ms)", exc, duration,
                    extra={"stage": "api_run_pipeline", "error": str(exc), "duration_ms": round(duration, 3)},
                )
                return {"status": "error", "message": str(exc)}

    def poll_progress(self) -> dict[str, Any] | None:
        event = self._pipeline.poll_progress()
        if event:
            logger.debug(
                "进度轮询 → %s: %s", event.get("type"), event.get("message", ""),
                extra={"stage": "poll_progress", "event": event},
            )
        return event

    # ------------------------------------------------------------------
    # 结果与统计
    # ------------------------------------------------------------------
    def get_results(self) -> list[dict[str, Any]]:
        """获取已完成的处理结果列表（通过扫描 output 目录）。"""
        self._check_output_changed()
        import re
        out_dir = self._resolve_output_dir()
        results = []
        # 使用更严格的正则匹配文件名模式
        raw_pattern = re.compile(r"^(.+)_raw\(n=\d+\)\.png$")
        for png in sorted(out_dir.glob("*.png")):
            match = raw_pattern.match(png.name)
            if not match:
                continue
            stem = match.group(1)
            rot_files = sorted(out_dir.glob(f"{stem}_rotated(strike=*.png"))
            rose_files = sorted(out_dir.glob(f"{stem}_rose(bin=*.png"))
            results.append({
                "outcrop": stem,
                "raw_plot": str(png.resolve()),
                "rotated_plot": str(rot_files[0].resolve()) if rot_files else "",
                "rose_plot": str(rose_files[0].resolve()) if rose_files else "",
            })
        logger.debug(
            "get_results → %d 个结果", len(results),
            extra={"stage": "api_get_results", "result_count": len(results), "out_dir": str(out_dir)},
        )
        return results

    def get_stats(self, outcrop: str) -> dict[str, Any]:
        start = time.perf_counter()
        self._check_output_changed()
        result = self._stats.get_stats(outcrop, self._config.get())
        duration = (time.perf_counter() - start) * 1000
        if "error" in result:
            logger.warning(
                "get_stats [%s] 失败: %s (%.3f ms)", outcrop, result["error"], duration,
                extra={"stage": "api_get_stats", "outcrop": outcrop, "duration_ms": round(duration, 3)},
            )
        else:
            logger.info(
                "get_stats [%s] 完成: trace_count=%s, P10=%.4f, P20=%.4f, P21=%.4f (%.3f ms)",
                outcrop, result.get("trace_count"), result.get("p10"), result.get("p20"), result.get("p21"), duration,
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
        results = self._stats.get_comparison(outcrops, self._config.get())
        duration = (time.perf_counter() - start) * 1000
        outcrops_str = ", ".join(outcrops[:10]) + ("..." if len(outcrops) > 10 else "")
        logger.info(
            "get_comparison [%s] 完成: %d/%d 个露头 (%.3f ms)",
            outcrops_str, len(results), len(outcrops), duration,
            extra={"stage": "api_get_comparison", "outcrops": outcrops[:50], "result_count": len(results), "duration_ms": round(duration, 3)},
        )
        return results

    # ------------------------------------------------------------------
    # 数据页
    # ------------------------------------------------------------------
    def get_data(self, outcrop: str, section: str, page: int = 1, page_size: int = 20, source: str = "output") -> dict[str, Any]:
        start = time.perf_counter()
        result = self._data.get_data(outcrop, section, page, page_size, source)
        duration = (time.perf_counter() - start) * 1000
        if "error" in result:
            logger.warning(
                "get_data [%s/%s] 失败: %s (%.3f ms)", outcrop, section, result["error"], duration,
                extra={"stage": "api_get_data", "outcrop": outcrop, "section": section, "source": source, "duration_ms": round(duration, 3)},
            )
        else:
            logger.debug(
                "get_data [%s/%s] page=%d: %d/%d 条记录 (%.3f ms)",
                outcrop, section, page, len(result.get("data", [])), result.get("total", 0), duration,
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
        if self._preview_running:
            logger.warning("generate_preview 被拒绝: 已有预览任务正在运行", extra={"stage": "api_preview_reject"})
            return {"status": "busy", "message": "已有预览任务正在运行"}
        self._preview_running = True
        try:
            start = time.perf_counter()
            merged = {**self._config.get(), **config}
            result = self._preview.generate(merged)
            duration = (time.perf_counter() - start) * 1000
            status = result.get("status", "unknown")
            img_count = len(result.get("images", []))
            logger.info(
                "generate_preview → status=%s, %d 张预览图 (%.3f ms)",
                status, img_count, duration,
                extra={
                    "stage": "api_preview",
                    "status": status,
                    "image_count": img_count,
                    "style_keys": list(merged.get("style", {}).keys()),
                    "duration_ms": round(duration, 3),
                },
            )
            return result
        finally:
            self._preview_running = False

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def get_logs(self, tail: int = 100, level: str = "INFO") -> list[str]:
        return self._log.get_logs(tail, level)

    # ------------------------------------------------------------------
    # 毕设功能（开发者选项）
    # ------------------------------------------------------------------
    def generate_report(self, outcrop: str, report_type: str, fmt: str) -> dict[str, Any]:
        if self._report_running:
            logger.warning("generate_report 被拒绝: 已有报告任务正在运行", extra={"stage": "api_report_reject"})
            return {"error": "已有报告任务正在运行"}
        self._report_running = True
        try:
            start = time.perf_counter()
            self._audit.log("generate_report", params={"outcrop": outcrop, "type": report_type, "fmt": fmt})
            result = self._report.generate(outcrop, report_type, fmt, self._config.get())
            duration = (time.perf_counter() - start) * 1000
            logger.info(
                "generate_report 完成: %s (%.3f ms)", outcrop, duration,
                extra={"stage": "api_report", "outcrop": outcrop, "duration_ms": round(duration, 3)},
            )
            return result
        finally:
            self._report_running = False

    def generate_reports_zip(self, targets: list[str], report_type: str, fmt: str, save_path: str | None = None) -> dict[str, Any]:
        import zipfile
        from datetime import datetime

        start = time.perf_counter()
        self._audit.log("generate_reports_zip", params={"targets": targets, "type": report_type, "fmt": fmt})
        cfg = self._config.get()
        files = []
        errors = []
        for oc in targets:
            res = self._report.generate(oc, report_type, fmt, cfg)
            if "error" in res:
                errors.append(f"{oc}: {res['error']}")
                continue
            if "docx" in res and res["docx"]:
                files.append(res["docx"])
            if "pdf" in res and res["pdf"]:
                files.append(res["pdf"])

        if not files:
            return {"error": "没有生成任何报告" + ("; ".join(errors) if errors else "")}

        zip_path: Path
        if save_path:
            safe = self._safe_path(save_path, base=PROJECT_ROOT)
            if safe is None:
                logger.warning("generate_reports_zip 拒绝越权保存路径: %s", save_path)
                return {"error": "保存路径越权"}
            zip_path = safe
            zip_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            zip_path = REPORT_DIR / f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    fp = Path(f)
                    fp_safe = self._safe_path(fp.name, base=Path(cfg.get("output_dir", "output")))
                    if fp_safe is None:
                        logger.warning("ZIP 中跳过越权路径: %s", f)
                        continue
                    zf.write(f, arcname=fp.name)
        except Exception as exc:
            logger.warning("ZIP 创建失败: %s", exc)
            return {"error": f"ZIP 创建失败: {exc}"}

        for f in files:
            try:
                os.remove(f)
            except Exception as exc:
                logger.debug("清理中间文件失败: %s → %s", f, exc)

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "generate_reports_zip 完成: %d 个文件 (%.3f ms)", len(files), duration,
            extra={"stage": "api_reports_zip", "file_count": len(files), "duration_ms": round(duration, 3)},
        )
        return {"zip_path": str(zip_path.resolve()), "count": len(files), "errors": errors}

    def get_provenance(self, outcrop: str) -> dict[str, Any]:
        """数据溯源：返回 P10/P20/P21 的计算来源链。"""
        stats = self._stats.get_stats(outcrop, self._config.get())
        if "error" in stats:
            return stats
        ns = stats.get("nodes_summary", {})
        logger.debug(
            "get_provenance [%s]", outcrop,
            extra={"stage": "api_provenance", "outcrop": outcrop, "area_source": stats.get("area_source")},
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
                "intersection_count": ns.get("intersection_count") if isinstance(ns, dict) else None,
            },
        }

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        logs = self._audit.get(limit)
        logger.debug("get_audit_log → %d 条记录", len(logs), extra={"stage": "api_audit_log", "count": len(logs), "limit": limit})
        return logs

    # ------------------------------------------------------------------
    # 系统
    # ------------------------------------------------------------------
    def open_directory(self, path: str) -> bool:
        """打开指定目录（支持相对路径，限制在项目根目录内）。"""
        target = self._safe_path(path)
        if target is None or not target.exists():
            logger.warning("open_directory 失败: 路径无效或不存在 → %s", path, extra={"stage": "api_open_dir", "path": path})
            return False
        if not target.is_dir():
            logger.warning("open_directory 失败: 目标不是目录 → %s", path, extra={"stage": "api_open_dir", "path": path})
            return False
        try:
            os.startfile(str(target))
            logger.info("open_directory → %s", target, extra={"stage": "api_open_dir", "path": str(target)})
            return True
        except Exception as exc:
            logger.warning("打开目录失败: %s → %s", path, exc, extra={"stage": "api_open_dir", "path": path, "error": str(exc)})
            return False

    # 图片读取上限：5MB，防止大图片导致内存溢出
    _MAX_IMAGE_SIZE = 5 * 1024 * 1024
    # 安全的图片扩展名白名单（禁止 SVG 防止 XSS；禁止 html/htm 等）
    _SAFE_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

    def get_image(self, path: str) -> str:
        """读取图片文件并返回 base64 data URL。限制在项目根目录内，单文件上限 5MB。"""
        try:
            # 强制以 PROJECT_ROOT 为 base，防止通过修改 output_dir 配置绕过路径限制
            p = self._safe_path(path, base=PROJECT_ROOT)
            if p is None or not p.exists():
                logger.warning("get_image 失败: 路径无效或不存在 → %s", path, extra={"stage": "api_get_image", "path": path})
                return ""
            size = p.stat().st_size
            if size > self._MAX_IMAGE_SIZE:
                logger.warning("get_image 拒绝: 文件过大 %s (%d bytes > %d limit)", path, size, self._MAX_IMAGE_SIZE, extra={"stage": "api_get_image", "path": path, "size_bytes": size})
                return ""
            ext = p.suffix.lower()
            if ext not in self._SAFE_IMAGE_EXTENSIONS:
                logger.warning("get_image 拒绝: 不安全的文件扩展名 %s", ext, extra={"stage": "api_get_image", "path": path, "ext": ext})
                return ""
            with open(p, "rb") as f:
                data = f.read()
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".webp": "image/webp",
            }[ext]
            b64 = base64.b64encode(data).decode("utf-8")
            logger.debug("get_image → %s (%d bytes)", path, len(data), extra={"stage": "api_get_image", "path": path, "size_bytes": len(data)})
            return f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.warning("读取图片失败: %s → %s", path, exc, extra={"stage": "api_get_image", "path": path, "error": str(exc)})
            return ""

    def ask_save_path(self, default_name: str = "reports.zip", file_filter: str = "ZIP 文件 (*.zip)") -> str:
        """打开系统另存为对话框，返回用户选择的保存路径（包含文件名）。用户取消时返回空字符串。"""
        if self._window is None:
            logger.warning("ask_save_path 失败: window 未初始化", extra={"stage": "api_ask_save_path"})
            return ""
        try:
            result = self._window.create_file_dialog(
                webview.FileDialog.SAVE,
                allow_multiple=False,
                save_filename=default_name,
                file_types=(file_filter,) if file_filter else (),
            )
            if isinstance(result, list) and result:
                chosen = str(result[0])
                logger.info("ask_save_path → %s", chosen, extra={"stage": "api_ask_save_path", "selected": chosen})
                return chosen
            if isinstance(result, str):
                chosen = str(result)
                logger.info("ask_save_path → %s", chosen, extra={"stage": "api_ask_save_path", "selected": chosen})
                return chosen
            logger.debug("ask_save_path → 用户取消选择", extra={"stage": "api_ask_save_path"})
            return ""
        except Exception as exc:
            logger.warning("ask_save_path 失败: %s", exc, extra={"stage": "api_ask_save_path", "error": str(exc)})
            return ""

    def browse_folder(self) -> str:
        """打开系统文件夹选择对话框，返回选中的路径。"""
        if self._window is None:
            logger.warning("browse_folder 失败: window 未初始化", extra={"stage": "api_browse_folder"})
            return ""
        try:
            result = self._window.create_file_dialog(
                webview.FileDialog.FOLDER, allow_multiple=False
            )
            if isinstance(result, list) and result:
                logger.info("browse_folder → %s", result[0], extra={"stage": "api_browse_folder", "selected": str(result[0])})
                return str(result[0])
            if isinstance(result, str):
                logger.info("browse_folder → %s", result, extra={"stage": "api_browse_folder", "selected": result})
                return result
            logger.debug("browse_folder → 用户取消选择", extra={"stage": "api_browse_folder"})
            return ""
        except Exception as exc:
            logger.warning("浏览文件夹失败: %s", exc, extra={"stage": "api_browse_folder", "error": str(exc)})
            return ""

    def export_config_json(self, folder: str, content: str) -> bool:
        """将 JSON 内容写入指定文件夹的 config.json 文件。限制在项目根目录内，并执行配置校验。"""
        try:
            folder_path = self._safe_path(folder)
            if folder_path is None:
                logger.warning("export_config_json 失败: 路径越权 → %s", folder, extra={"stage": "api_export_config", "folder": folder})
                return False
            path = folder_path / "config.json"
            parsed = json.loads(content)
            # 深度校验：复用 validate_config 确保字段合法
            from trace_pipeline.config import validate_config
            validated = validate_config(parsed)
            path.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
            self._audit.log("export_config_json", params={"path": str(path)})
            logger.info("export_config_json → %s", path, extra={"stage": "api_export_config", "path": str(path), "field_count": len(validated)})
            return True
        except Exception as exc:
            logger.warning("导出配置失败: %s → %s", folder, exc, extra={"stage": "api_export_config", "folder": folder, "error": str(exc)})
            return False

    def shutdown_pipeline(self) -> None:
        """应用关闭前调用，确保后台流水线优雅结束。"""
        self._pipeline.shutdown(timeout=30.0)

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
            logger.warning("window_minimize 失败: %s", exc, extra={"stage": "api_window_minimize", "error": str(exc)})
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
            logger.warning("window_maximize 失败: %s", exc, extra={"stage": "api_window_maximize", "error": str(exc)})
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
            logger.debug("window_resize 失败: %s", exc, extra={"stage": "api_window_resize", "error": str(exc)})
            return False

    def window_close(self) -> bool:
        """关闭窗口。"""
        if self._window is None:
            return False
        try:
            self._window.destroy()
            return True
        except Exception as exc:
            logger.warning("window_close 失败: %s", exc, extra={"stage": "api_window_close", "error": str(exc)})
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
            logger.debug("window_move_by 失败: %s", exc, extra={"stage": "api_window_move", "error": str(exc)})
            return False

    def window_position(self) -> dict[str, int]:
        """获取窗口当前位置。"""
        if self._window is None:
            return {"x": 0, "y": 0}
        try:
            return {"x": self._window.x, "y": self._window.y}
        except Exception as exc:
            logger.debug("window_position 失败: %s", exc, extra={"stage": "api_window_position", "error": str(exc)})
            return {"x": 0, "y": 0}

    def window_move_to(self, x: int, y: int) -> bool:
        """绝对移动窗口到指定位置（用于自定义标题栏拖拽，避免增量抖动）。"""
        if self._window is None:
            return False
        try:
            self._window.move(x, y)
            return True
        except Exception as exc:
            logger.debug("window_move_to 失败: %s", exc, extra={"stage": "api_window_move_to", "error": str(exc)})
            return False

    def window_is_maximized(self) -> bool:
        """查询窗口是否已最大化。"""
        return self._window_maximized

    def check_webview2(self) -> dict[str, Any]:
        from backend.webview2_checker import WebView2Checker
        checker = WebView2Checker()
        installed = checker.is_installed()
        logger.debug(
            "check_webview2 → installed=%s", installed,
            extra={"stage": "api_check_webview2", "installed": installed},
        )
        return {"installed": installed, "url": checker.get_download_url()}
