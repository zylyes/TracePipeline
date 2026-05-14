"""暴露给 JS 的 API 类。"""
from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .services.audit_service import AuditService
from .services.config_service import ConfigService
from .services.data_service import DataService
from .services.file_service import FileService
from .services.log_service import LogService
from .services.pipeline_service import PipelineService
from .services.preview_service import PreviewService
from .services.report_service import REPORT_DIR, ReportService
from .services.stats_service import StatsService

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GuiApi:
    """pywebview JS API 入口。所有 public 方法均可被前端调用。"""

    def __init__(self) -> None:
        self._config = ConfigService()
        self._file = FileService(self._config.get().get("input_dir", "input"))
        self._pipeline = PipelineService()
        self._preview = PreviewService()
        self._stats = StatsService()
        self._data = DataService(self._config.get().get("output_dir", "output"))
        self._log = LogService()
        self._report = ReportService()
        self._audit = AuditService()
        self._window: Any = None

    def set_window(self, window: Any) -> None:
        self._window = window

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        return self._config.get()

    def set_config(self, config: dict[str, Any]) -> dict[str, Any]:
        self._audit.log("set_config", params=config)
        self._file.set_input_dir(config.get("input_dir", "input"))
        self._data = DataService(config.get("output_dir", "output"))
        # 同步更新内部绝对路径引用
        return self._config.set(config)

    def reset_config(self) -> dict[str, Any]:
        self._audit.log("reset_config")
        return self._config.reset()

    # ------------------------------------------------------------------
    # 文件
    # ------------------------------------------------------------------
    def scan_files(self) -> list[dict[str, Any]]:
        return self._file.scan()

    # ------------------------------------------------------------------
    # 流水线
    # ------------------------------------------------------------------
    def run_pipeline(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        self._audit.log("run_pipeline", params={"targets": targets, "config": config})
        return self._pipeline.run(targets, config)

    def poll_progress(self) -> dict[str, Any] | None:
        return self._pipeline.poll_progress()

    # ------------------------------------------------------------------
    # 结果与统计
    # ------------------------------------------------------------------
    def get_results(self) -> list[dict[str, Any]]:
        """获取已完成的处理结果列表（通过扫描 output 目录）。"""
        out_dir = Path(self._config.get().get("output_dir", "output"))
        if not out_dir.is_absolute():
            out_dir = PROJECT_ROOT / out_dir
        out_dir = out_dir.resolve()
        results = []
        for png in sorted(out_dir.glob("*_raw(n=*.png")):
            stem = png.stem.split("_raw")[0]
            rot_files = list(out_dir.glob(f"{stem}_rotated*.png"))
            rose_files = list(out_dir.glob(f"{stem}_rose*.png"))
            results.append({
                "outcrop": stem,
                "raw_plot": str(png.resolve()),
                "rotated_plot": str(rot_files[0].resolve()) if rot_files else "",
                "rose_plot": str(rose_files[0].resolve()) if rose_files else "",
            })
        return results

    def get_stats(self, outcrop: str) -> dict[str, Any]:
        return self._stats.get_stats(outcrop, self._config.get())

    def get_comparison(self, outcrops: list[str]) -> list[dict[str, Any]]:
        return self._stats.get_comparison(outcrops, self._config.get())

    # ------------------------------------------------------------------
    # 数据页
    # ------------------------------------------------------------------
    def get_data(self, outcrop: str, section: str, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        return self._data.get_data(outcrop, section, page, page_size)

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------
    def generate_preview(self, style: dict[str, Any]) -> dict[str, Any]:
        return self._preview.generate(style)

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------
    def get_logs(self, tail: int = 100, level: str = "INFO") -> list[str]:
        return self._log.get_logs(tail, level)

    # ------------------------------------------------------------------
    # 毕设功能（开发者选项）
    # ------------------------------------------------------------------
    def generate_report(self, outcrop: str, report_type: str, fmt: str) -> dict[str, Any]:
        self._audit.log("generate_report", params={"outcrop": outcrop, "type": report_type, "fmt": fmt})
        return self._report.generate(outcrop, report_type, fmt, self._config.get())

    def generate_reports_zip(self, targets: list[str], report_type: str, fmt: str) -> dict[str, Any]:
        import zipfile
        from datetime import datetime

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

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        zip_name = f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = REPORT_DIR / zip_name
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, arcname=Path(f).name)

        # 清理中间单文件，仅保留 zip
        for f in files:
            try:
                os.remove(f)
            except Exception:
                pass

        return {"zip_path": str(zip_path.resolve()), "count": len(files), "errors": errors}

    def get_provenance(self, outcrop: str) -> dict[str, Any]:
        """数据溯源：返回 P10/P20/P21 的计算来源链。"""
        stats = self._stats.get_stats(outcrop, self._config.get())
        if "error" in stats:
            return stats
        return {
            "outcrop": outcrop,
            "p10": {"value": stats.get("p10"), "source": "实测测线"},
            "p20": {"value": stats.get("p20"), "source": stats.get("area_source", "unknown")},
            "p21": {"value": stats.get("p21"), "source": stats.get("area_source", "unknown")},
            "area_source": stats.get("area_source"),
            "warning": stats.get("warning"),
        }

    def get_audit_log(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._audit.get(limit)

    # ------------------------------------------------------------------
    # 系统
    # ------------------------------------------------------------------
    def open_directory(self, path: str) -> bool:
        """打开指定目录（支持相对路径）。"""
        target = Path(path)
        if not target.is_absolute():
            target = PROJECT_ROOT / path
        target = target.resolve()
        if not target.exists():
            return False
        try:
            os.startfile(str(target))
            return True
        except Exception as exc:
            logger.warning("打开目录失败: %s", exc)
            return False

    def get_image(self, path: str) -> str:
        """读取图片文件并返回 base64 data URL。"""
        try:
            p = Path(path)
            if not p.exists():
                return ""
            with open(p, "rb") as f:
                data = f.read()
            ext = p.suffix.lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.warning("读取图片失败: %s", exc)
            return ""

    def browse_folder(self) -> str:
        """打开系统文件夹选择对话框，返回选中的路径。"""
        if self._window is None:
            return ""
        try:
            result = self._window.create_folder_dialog()
            if isinstance(result, list) and result:
                return str(result[0])
            if isinstance(result, str):
                return result
            return ""
        except Exception as exc:
            logger.warning("浏览文件夹失败: %s", exc)
            return ""

    def check_webview2(self) -> dict[str, Any]:
        from .webview2_checker import WebView2Checker
        checker = WebView2Checker()
        return {"installed": checker.is_installed(), "url": checker.get_download_url()}
