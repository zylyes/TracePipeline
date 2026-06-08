"""报告导出服务（毕设功能）。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from trace_pipeline.config import PROJECT_ROOT
from trace_pipeline.geology.statistics import TraceStatisticsConfig, compute_trace_statistics
from trace_pipeline.pipeline import load_trace_data
from backend.utils.path_utils import validate_outcrop_name

logger = logging.getLogger(__name__)

REPORT_DIR = PROJECT_ROOT / "output" / "reports"


def _find_system_font() -> tuple[str, str]:
    """跨平台字体探测：返回 (font_path, font_name)。"""
    import platform
    system = platform.system()

    if system == "Windows":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        fonts_dir = os.path.join(windir, "Fonts")
        windows_candidates = [
            (os.path.join(fonts_dir, "simsun.ttc"), "SimSun"),
            (os.path.join(fonts_dir, "SimSun.ttf"), "SimSun"),
            (os.path.join(fonts_dir, "msyh.ttc"), "MicrosoftYaHei"),
            (os.path.join(fonts_dir, "msyhbd.ttc"), "MicrosoftYaHei"),
            (os.path.join(fonts_dir, "simhei.ttf"), "SimHei"),
        ]
        candidates = windows_candidates
    else:
        unix_candidates = [
            ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYiZenHei"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
            ("/usr/local/share/fonts/truetype/wqy/wqy-zenhei.ttc", "WenQuanYiZenHei"),
            ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
            ("/System/Library/Fonts/STHeiti Light.ttc", "STHeiti"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "LiberationSans"),
        ]
        user_fonts = os.path.expanduser("~/.fonts")
        for name, label in [("wqy-zenhei.ttc", "WenQuanYiZenHei"), ("NotoSansCJK-Regular.ttc", "NotoSansCJK")]:
            unix_candidates.append((os.path.join(user_fonts, name), label))
        candidates = unix_candidates

    for fp, fname in candidates:
        if os.path.exists(fp):
            return fp, fname

    # 回退：尝试从 matplotlib 字体管理器查找 CJK 字体
    try:
        import matplotlib.font_manager as fm
        cjk_keywords = ["noto", "cjk", "wqy", "sourcehansans", "sourcehanserifs",
                      "microsoftyahei", "simsun", "simhei", "pingfang", "heiti",
                      "meiryo", "malgun", "yugothic", "nanum"]
        for font in fm.fontManager.ttflist:
            name_lower = font.name.lower()
            if any(k in name_lower for k in cjk_keywords):
                return font.fname, font.name
        # 回退到系统默认 sans-serif 字体（通常能渲染拉丁字符）
        default_font = fm.findfont(fm.FontProperties(family="sans-serif"))
        if default_font and os.path.exists(default_font):
            return default_font, "sans-serif"
    except Exception:
        pass

    return "", ""


class ReportService:
    """生成 Word / PDF 报告。"""

    def generate(self, outcrop: str, report_type: str, fmt: str, config: dict[str, Any]) -> dict[str, Any]:
        """生成报告并返回文件路径。"""
        try:
            validate_outcrop_name(outcrop)
        except ValueError as exc:
            return {"error": str(exc)}
        import time
        start = time.perf_counter()

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        results = {}

        input_dir = config.get("input_dir", "input")
        table_stem = f"{outcrop}_process"
        logger.info(
            "报告生成开始 [%s]: type=%s, fmt=%s", outcrop, report_type, fmt,
            extra={"stage": "report_start", "outcrop": outcrop, "report_type": report_type, "fmt": fmt},
        )
        try:
            trace = load_trace_data(input_dir, table_stem, outcrop)
            stats_config = TraceStatisticsConfig(
                window_strategy=config.get("window_strategy", "auto"),
                min_intersections=config.get("min_intersections", 5),
            )
            statistics = compute_trace_statistics(trace, stats_config)
        except Exception as exc:
            logger.warning("报告 [%s] 数据加载失败: %s", outcrop, exc, extra={"stage": "report_error", "outcrop": outcrop, "error": str(exc)})
            return {"error": str(exc)}

        if fmt in ("docx", "both"):
            docx_path = self._gen_docx(outcrop, trace, statistics, report_type, config)
            results["docx"] = docx_path
            if docx_path:
                logger.info("DOCX 报告生成: %s", docx_path, extra={"stage": "report_docx", "outcrop": outcrop, "path": docx_path})
        if fmt in ("pdf", "both"):
            pdf_path = self._gen_pdf(outcrop, trace, statistics, report_type, config)
            results["pdf"] = pdf_path
            if pdf_path:
                logger.info("PDF 报告生成: %s", pdf_path, extra={"stage": "report_pdf", "outcrop": outcrop, "path": pdf_path})

        duration = (time.perf_counter() - start) * 1000
        logger.info(
            "报告生成完成 [%s]: docx=%s, pdf=%s (%.3f ms)",
            outcrop, bool(results.get("docx")), bool(results.get("pdf")), duration,
            extra={
                "stage": "report_complete",
                "outcrop": outcrop,
                "report_type": report_type,
                "fmt": fmt,
                "has_docx": bool(results.get("docx")),
                "has_pdf": bool(results.get("pdf")),
                "duration_ms": round(duration, 3),
            },
        )
        return results

    # ------------------------------------------------------------------
    # 共享：提取报告数据上下文（消除 docx/pdf 之间的重复）
    # ------------------------------------------------------------------
    def _build_report_context(
        self, outcrop: str, trace, statistics, report_type: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """返回报告所需的统计文本行和图片路径，供各格式渲染器共用。"""
        stat_lines: list[str] = []
        if report_type in ("full", "stats"):
            stat_lines = [
                f"露头标识: {outcrop}",
                f"测线走向: {trace.scanline_azimuth:.2f}°",
                f"迹线条数: {trace.count}",
                f"平均迹长: {statistics.mean_trace_length:.4f} m",
                f"线密度 P10: {statistics.p10:.4f} m⁻¹",
                f"面密度 P20: {statistics.p20:.4f} m⁻²",
                f"长度密度 P21: {statistics.p21:.4f} m⁻¹",
                f"测线长度: {statistics.scanline_length:.4f} m",
                f"露头面积: {statistics.outcrop_area:.4f} m² (来源: {statistics.outcrop_area_source or 'unknown'})",
                f"圆窗策略: {statistics.window_strategy or 'auto'}",
                f"I 型迹线数: {statistics.type_i_count}",
                f"II 型迹线数: {statistics.type_ii_count}",
                f"III 型迹线数: {statistics.type_iii_count}",
            ]
            if statistics.window_validation_warning:
                stat_lines.append(f"警告: {statistics.window_validation_warning}")

        img_names: list[str] = []
        if report_type in ("full", "plots"):
            out_dir = Path(config.get("output_dir", "output"))
            if not out_dir.is_absolute():
                out_dir = PROJECT_ROOT / out_dir
            out_dir = out_dir.resolve()
            for img_name in [
                f"{outcrop}_raw(n={trace.count}).png",
                f"{outcrop}_rotated(strike={trace.scanline_azimuth:.1f}).png",
                f"{outcrop}_rose(bin={config.get('rose_bin_width', 10.0)}).png",
            ]:
                img_path = out_dir / img_name
                if img_path.exists():
                    img_names.append(str(img_path))

        return {"title": f"{outcrop} 迹线分析报告", "stat_lines": stat_lines, "img_paths": img_names}

    # ------------------------------------------------------------------
    # Word
    # ------------------------------------------------------------------
    def _gen_docx(self, outcrop: str, trace, statistics, report_type: str, config: dict[str, Any]) -> str:
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml.ns import qn
            from docx.shared import Inches, Pt
        except ImportError:
            logger.warning("python-docx 未安装")
            return ""

        ctx = self._build_report_context(outcrop, trace, statistics, report_type, config)
        try:
            doc = Document()

            def _set_style_font(style, western="Times New Roman", east_asia="SimSun", size=None, bold=False):
                style.font.name = western
                if size is None:
                    size = Pt(12)
                style.font.size = size
                style.font.bold = bold
                if style.element.rPr is not None:
                    style.element.rPr.rFonts.set(qn('w:eastAsia'), east_asia)

            _set_style_font(doc.styles['Normal'])
            for lvl in [0, 1, 2, 3]:
                try:
                    name = 'Title' if lvl == 0 else f'Heading {lvl}'
                    _set_style_font(doc.styles[name], size=Pt([20, 16, 14, 12][lvl]), bold=True, east_asia="SimHei")
                except KeyError:
                    pass

            def _add_para(text, style=None):
                p = doc.add_paragraph(text, style=style)
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    if run.element.rPr is not None:
                        run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
                return p

            title = doc.add_heading(ctx["title"], level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in title.runs:
                run.font.name = 'Times New Roman'
                if run.element.rPr is not None:
                    run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

            for line in ctx["stat_lines"]:
                _add_para(line)
            for img_path in ctx["img_paths"]:
                doc.add_picture(img_path, width=Inches(5.5))

            path = REPORT_DIR / f"{outcrop}_report.docx"
            doc.save(str(path))
            return str(path.resolve())
        except Exception as exc:
            logger.exception("DOCX 生成失败: %s", exc)
            return ""

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def _gen_pdf(self, outcrop: str, trace, statistics, report_type: str, config: dict[str, Any]) -> str:
        try:
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.platypus import Image as RLImage
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        except ImportError:
            logger.warning("reportlab 未安装")
            return ""

        ctx = self._build_report_context(outcrop, trace, statistics, report_type, config)
        try:
            font_path, font_name = _find_system_font()
            if font_path and font_name:
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                except Exception as exc:
                    logger.warning("注册字体 %s 失败: %s", font_name, exc)
                    font_name = "Times-Roman"
            else:
                font_name = "Times-Roman"

            doc = SimpleDocTemplate(str(REPORT_DIR / f"{outcrop}_report.pdf"), pagesize=A4)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontName=font_name, fontSize=18, alignment=TA_CENTER, spaceAfter=20)
            body_style = ParagraphStyle("CustomBody", parent=styles["BodyText"], fontName=font_name, fontSize=11, spaceAfter=8)

            story = [Paragraph(ctx["title"], title_style), Spacer(1, 12)]
            for line in ctx["stat_lines"]:
                story.append(Paragraph(line, body_style))
            if ctx["stat_lines"]:
                story.append(Spacer(1, 12))
            for img_path in ctx["img_paths"]:
                story.append(RLImage(img_path, width=400, height=300))
                story.append(Spacer(1, 12))

            doc.build(story)
            return str((REPORT_DIR / f"{outcrop}_report.pdf").resolve())
        except Exception as exc:
            logger.exception("PDF 生成失败: %s", exc)
            return ""
