"""暴露给 JS 的 API 类。"""
from __future__ import annotations

import base64
import contextlib
import json
import logging
import os
import sys
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

logger = logging.getLogger(__name__)
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GuiApi:
    """pywebview JS API 入口。所有 public 方法均可被前端调用。"""

    def __init__(self) -> None:
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
        self._sync_services_from_config(self._config.get())

    def set_window(self, window: Any) -> None:
        self._window = window

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _safe_path(self, path: str, base: Path | None = None) -> Path | None:
        """解析并校验路径在项目根目录内，防止路径遍历攻击。"""
        p = Path(path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p = p.resolve()
        base = (base or PROJECT_ROOT).resolve()
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

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        return self._config.get()

    def set_config(self, config: dict[str, Any]) -> dict[str, Any]:
        self._audit.log("set_config")
        merged = self._config.set(config)
        self._sync_services_from_config(merged)
        return merged

    def reset_config(self) -> dict[str, Any]:
        self._audit.log("reset_config")
        default = self._config.reset()
        self._sync_services_from_config(default)
        return default

    def reset_processing_config(self) -> dict[str, Any]:
        self._audit.log("reset_processing_config")
        cfg = self._config.reset_processing()
        self._sync_services_from_config(cfg)
        return cfg

    def reset_style_config(self) -> dict[str, Any]:
        self._audit.log("reset_style_config")
        cfg = self._config.reset_style()
        self._sync_services_from_config(cfg)
        return cfg

    # ------------------------------------------------------------------
    # 文件
    # ------------------------------------------------------------------
    def scan_files(self) -> list[dict[str, Any]]:
        return self._file.scan()

    # ------------------------------------------------------------------
    # 流水线
    # ------------------------------------------------------------------
    def run_pipeline(self, targets: list[str], config: dict[str, Any]) -> dict[str, Any]:
        self._audit.log("run_pipeline", params={"targets": targets, "input_dir": config.get("input_dir", "")})
        try:
            merged = {**self._config.get(), **config}
            saved = self._config.set(merged)
            self._sync_services_from_config(saved)
            return self._pipeline.run(targets, saved)
        except ValueError as exc:
            logger.warning("流水线配置校验失败: %s", exc)
            return {"status": "error", "message": str(exc)}

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
        for png in sorted(out_dir.glob("*_raw(n=*).png")):
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
    def get_data(self, outcrop: str, section: str, page: int = 1, page_size: int = 20, source: str = "output") -> dict[str, Any]:
        return self._data.get_data(outcrop, section, page, page_size, source)

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------
    def generate_preview(self, config: dict[str, Any]) -> dict[str, Any]:
        # 合并当前统一配置与前端传入的配置（样式等）
        merged = {**self._config.get(), **config}
        return self._preview.generate(merged)

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
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, arcname=Path(f).name)
        except Exception as exc:
            logger.warning("ZIP 创建失败: %s", exc)
            return {"error": f"ZIP 创建失败: {exc}"}

        # ZIP 创建成功后才清理中间单文件
        for f in files:
            with contextlib.suppress(Exception):
                os.remove(f)

        return {"zip_path": str(zip_path.resolve()), "count": len(files), "errors": errors}

    def get_provenance(self, outcrop: str) -> dict[str, Any]:
        """数据溯源：返回 P10/P20/P21 的计算来源链。"""
        stats = self._stats.get_stats(outcrop, self._config.get())
        if "error" in stats:
            return stats
        ns = stats.get("nodes_summary", {})
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
        return self._audit.get(limit)

    # ------------------------------------------------------------------
    # 系统
    # ------------------------------------------------------------------
    def open_directory(self, path: str) -> bool:
        """打开指定目录（支持相对路径，限制在项目根目录内）。"""
        target = self._safe_path(path)
        if target is None or not target.exists():
            return False
        try:
            os.startfile(str(target))
            return True
        except Exception as exc:
            logger.warning("打开目录失败: %s", exc)
            return False

    def get_image(self, path: str) -> str:
        """读取图片文件并返回 base64 data URL。限制在输出目录内。"""
        try:
            out_dir = Path(self._config.get().get("output_dir", "output"))
            if not out_dir.is_absolute():
                out_dir = PROJECT_ROOT / out_dir
            out_dir = out_dir.resolve()
            p = self._safe_path(path, base=out_dir)
            if p is None or not p.exists():
                return ""
            with open(p, "rb") as f:
                data = f.read()
            ext = p.suffix.lower()
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(ext, "image/png")
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
            result = self._window.create_file_dialog(
                webview.FileDialog.FOLDER, allow_multiple=False
            )
            if isinstance(result, list) and result:
                return str(result[0])
            if isinstance(result, str):
                return result
            return ""
        except Exception as exc:
            logger.warning("浏览文件夹失败: %s", exc)
            return ""

    def export_config_json(self, folder: str, content: str) -> bool:
        """将 JSON 内容写入指定文件夹的 config.json 文件。限制在项目根目录内。"""
        try:
            folder_path = self._safe_path(folder)
            if folder_path is None:
                return False
            path = folder_path / "config.json"
            parsed = json.loads(content)
            path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            self._audit.log("export_config_json", params={"path": str(path)})
            return True
        except Exception as exc:
            logger.warning("导出配置失败: %s", exc)
            return False

    def check_webview2(self) -> dict[str, Any]:
        from backend.webview2_checker import WebView2Checker
        checker = WebView2Checker()
        return {"installed": checker.is_installed(), "url": checker.get_download_url()}
