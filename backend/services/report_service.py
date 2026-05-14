"""报告导出服务（毕设功能）。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from trace_pipeline.pipeline import load_trace_data
from trace_pipeline.geology.statistics import TraceStatisticsConfig, compute_trace_statistics

logger = logging.getLogger(__name__)

REPORT_DIR = Path("output/reports")


class ReportService:
    """生成 Word / PDF 报告。"""

    def generate(self, outcrop: str, report_type: str, fmt: str, config: dict[str, Any]) -> dict[str, Any]:
        """生成报告并返回文件路径。"""
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        results = {}

        input_dir = config.get("input_dir", "input")
        table_stem = f"{outcrop}_process"
        try:
            trace = load_trace_data(input_dir, table_stem, outcrop)
            stats_config = TraceStatisticsConfig(
                window_strategy=config.get("window_strategy", "auto"),
            )
            statistics = compute_trace_statistics(trace, stats_config)
        except Exception as exc:
            return {"error": str(exc)}

        if fmt in ("docx", "both"):
            results["docx"] = self._gen_docx(outcrop, trace, statistics, report_type)
        if fmt in ("pdf", "both"):
            results["pdf"] = self._gen_pdf(outcrop, trace, statistics, report_type)

        return results

    # ------------------------------------------------------------------
    # Word
    # ------------------------------------------------------------------
    def _gen_docx(self, outcrop: str, trace, statistics, report_type: str) -> str:
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.oxml.ns import qn
        except ImportError:
            logger.warning("python-docx 未安装")
            return ""

        doc = Document()

        # 设置默认字体（英文 TNR，中文宋体；标题黑体）
        def _set_style_font(style, western="Times New Roman", east_asia="SimSun", size=Pt(12), bold=False):
            style.font.name = western
            style.font.size = size
            style.font.bold = bold
            if style.element.rPr is not None:
                style.element.rPr.rFonts.set(qn('w:eastAsia'), east_asia)

        _set_style_font(doc.styles['Normal'])
        for lvl in [0, 1, 2, 3]:
            try:
                name = 'Title' if lvl == 0 else f'Heading {lvl}'
                _set_style_font(
                    doc.styles[name],
                    size=Pt([20, 16, 14, 12][lvl]),
                    bold=True,
                    east_asia="SimHei"
                )
            except KeyError:
                pass

        def _add_para(text, style=None):
            p = doc.add_paragraph(text, style=style)
            for run in p.runs:
                run.font.name = 'Times New Roman'
                if run.element.rPr is not None:
                    run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
            return p

        title = doc.add_heading(f"{outcrop} 迹线分析报告", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in title.runs:
            run.font.name = 'Times New Roman'
            if run.element.rPr is not None:
                run.element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

        if report_type in ("full", "stats"):
            _add_para(f"露头标识: {outcrop}")
            _add_para(f"测线走向: {trace.scanline_azimuth:.2f}°")
            _add_para(f"迹线条数: {trace.count}")
            _add_para(f"平均迹长: {statistics.mean_trace_length:.4f} m")
            _add_para(f"线密度 P10: {statistics.p10:.4f} m⁻¹")
            _add_para(f"面密度 P20: {statistics.p20:.4f} m⁻²")
            _add_para(f"长度密度 P21: {statistics.p21:.4f} m⁻¹")

        if report_type in ("full", "plots"):
            out_dir = Path("output")
            for img_name in [
                f"{outcrop}_raw(n={trace.count}).png",
                f"{outcrop}_rose(bin=10.0).png",
            ]:
                img_path = out_dir / img_name
                if img_path.exists():
                    doc.add_picture(str(img_path), width=Inches(5.5))

        path = REPORT_DIR / f"{outcrop}_report.docx"
        doc.save(str(path))
        return str(path.resolve())

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def _gen_pdf(self, outcrop: str, trace, statistics, report_type: str) -> str:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.lib.enums import TA_CENTER
        except ImportError:
            logger.warning("reportlab 未安装")
            return ""

        # 注册中文字体（优先 SimSun，其次微软雅黑）
        font_name = "Times-Roman"
        fallback_fonts = [
            (r"C:\Windows\Fonts\simsun.ttc", "SimSun"),
            (r"C:\Windows\Fonts\SimSun.ttf", "SimSun"),
            (r"C:\Windows\Fonts\msyh.ttc", "MicrosoftYaHei"),
            (r"C:\Windows\Fonts\msyhbd.ttc", "MicrosoftYaHei"),
        ]
        for fp, fname in fallback_fonts:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont(fname, fp))
                    font_name = fname
                    break
                except Exception:
                    continue

        path = REPORT_DIR / f"{outcrop}_report.pdf"
        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=11,
            spaceAfter=8,
        )

        story = []
        story.append(Paragraph(f"{outcrop} 迹线分析报告", title_style))
        story.append(Spacer(1, 12))

        if report_type in ("full", "stats"):
            story.append(Paragraph(f"露头标识: {outcrop}", body_style))
            story.append(Paragraph(f"测线走向: {trace.scanline_azimuth:.2f}°", body_style))
            story.append(Paragraph(f"迹线条数: {trace.count}", body_style))
            story.append(Paragraph(f"平均迹长: {statistics.mean_trace_length:.4f} m", body_style))
            story.append(Paragraph(f"线密度 P10: {statistics.p10:.4f} m⁻¹", body_style))
            story.append(Paragraph(f"面密度 P20: {statistics.p20:.4f} m⁻²", body_style))
            story.append(Paragraph(f"长度密度 P21: {statistics.p21:.4f} m⁻¹", body_style))
            story.append(Spacer(1, 12))

        if report_type in ("full", "plots"):
            out_dir = Path("output")
            for img_name in [
                f"{outcrop}_raw(n={trace.count}).png",
                f"{outcrop}_rose(bin=10.0).png",
            ]:
                img_path = out_dir / img_name
                if img_path.exists():
                    story.append(RLImage(str(img_path), width=400, height=300))
                    story.append(Spacer(1, 12))

        doc.build(story)
        return str(path.resolve())
