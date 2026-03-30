from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from services.report_display import build_summary_metrics


registerFont(UnicodeCIDFont("STSong-Light"))

DEFAULT_REPORT_TITLE = "企业体检报告"
DEFAULT_SECTION_TITLE = "报告章节"
PENDING_CHECKS_TITLE = "待核验"


def _normalize_section_content(section: dict[str, Any]) -> tuple[str, list[str]]:
    summary = (section.get("summary") or "").strip()
    body: list[str] = []
    for paragraph in section.get("body", []):
        cleaned = (paragraph or "").strip()
        if not cleaned:
            continue
        if summary and _is_duplicate_text(summary, cleaned):
            continue
        if any(_is_duplicate_text(cleaned, existing) for existing in body):
            continue
        body.append(cleaned)
    return summary, body


def _is_duplicate_text(left: str, right: str) -> bool:
    normalized_left = "".join((left or "").split())
    normalized_right = "".join((right or "").split())
    if not normalized_left or not normalized_right:
        return False
    return normalized_left == normalized_right or normalized_left in normalized_right or normalized_right in normalized_left


class ReportPDFService:
    def __init__(self, export_dir: Path | None = None) -> None:
        self.export_dir = export_dir or Path("data/export")
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def build_pdf(self, report: dict[str, Any]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=report.get("report_title", DEFAULT_REPORT_TITLE),
        )
        styles = self._styles()
        payload = report.get("report_payload") or {}
        cover = payload.get("cover") or {}
        report_layer = payload.get("report_layer") or {}
        sections = payload.get("sections") or report_layer.get("deep_sections") or []
        metrics = build_summary_metrics(report)
        executive_summary = (report_layer.get("executive_summary") or report.get("summary") or "").strip()
        risk_groups = report_layer.get("risk_opportunities") or {}
        action_items = report_layer.get("action_items") or []
        key_evidence = (payload.get("evidence_layer") or {}).get("key_evidence") or []

        story = [
            Paragraph(self._safe(cover.get("title", report.get("report_title", DEFAULT_REPORT_TITLE))), styles["title"]),
            Spacer(1, 8),
            Paragraph(f"公司代码：{self._safe(cover.get('company_code', report.get('company_code', '-')))}", styles["meta"]),
            Paragraph(f"查询：{self._safe(cover.get('query', report.get('query', '-')))}", styles["meta"]),
            *[Paragraph(f"{self._safe(item['label'])}：{self._safe(item['value'])}", styles["meta"]) for item in metrics],
            Spacer(1, 12),
        ]

        if executive_summary:
            story.append(Paragraph("执行摘要", styles["section"]))
            story.append(Paragraph(self._safe(executive_summary), styles["body"]))
            story.append(Spacer(1, 8))

        for section in sections:
            summary, body = _normalize_section_content(section)
            story.append(Paragraph(self._safe(section.get("title", section.get("key", DEFAULT_SECTION_TITLE))), styles["section"]))
            if section.get("expert_role"):
                story.append(Paragraph(self._safe(section["expert_role"]), styles["meta"]))
                story.append(Spacer(1, 2))
            if summary:
                story.append(Paragraph(self._safe(summary), styles["body"]))
                story.append(Spacer(1, 4))
            for paragraph in body:
                story.append(Paragraph(self._safe(paragraph), styles["body"]))
                story.append(Spacer(1, 4))
            pending_checks = section.get("pending_checks") or []
            if pending_checks and section.get("key") != "verification_notes":
                story.append(Paragraph(PENDING_CHECKS_TITLE, styles["subsection"]))
                for item in pending_checks:
                    story.append(Paragraph(self._safe(item), styles["bullet"]))
            story.append(Spacer(1, 8))

        risks = risk_groups.get("risks") or []
        opportunities = risk_groups.get("opportunities") or []
        if risks or opportunities:
            story.append(Paragraph("风险与机会", styles["section"]))
            if risks:
                story.append(Paragraph("主要风险", styles["subsection"]))
                for item in risks:
                    story.append(Paragraph(self._safe(f"{item.get('title', '')}：{item.get('summary', '')}"), styles["body"]))
                    if item.get("basis"):
                        story.append(Paragraph(self._safe(f"依据：{item['basis']}"), styles["bullet"]))
                    if item.get("impact"):
                        story.append(Paragraph(self._safe(f"含义：{item['impact']}"), styles["bullet"]))
            if opportunities:
                story.append(Paragraph("主要机会", styles["subsection"]))
                for item in opportunities:
                    story.append(Paragraph(self._safe(f"{item.get('title', '')}：{item.get('summary', '')}"), styles["body"]))
                    if item.get("basis"):
                        story.append(Paragraph(self._safe(f"依据：{item['basis']}"), styles["bullet"]))
                    if item.get("impact"):
                        story.append(Paragraph(self._safe(f"含义：{item['impact']}"), styles["bullet"]))
            story.append(Spacer(1, 8))

        if key_evidence:
            story.append(Paragraph("关键证据", styles["section"]))
            for item in key_evidence:
                story.append(Paragraph(self._safe(f"{item.get('title', '')}：{item.get('summary', '')}"), styles["body"]))
                if item.get("supports"):
                    story.append(Paragraph(self._safe(f"支持判断：{item['supports']}"), styles["bullet"]))
                if item.get("citation"):
                    story.append(Paragraph(self._safe(item["citation"]), styles["bullet"]))
            story.append(Spacer(1, 8))

        if action_items:
            story.append(Paragraph("建议动作", styles["section"]))
            for index, item in enumerate(action_items, start=1):
                story.append(Paragraph(self._safe(f"{index}. {item.get('action', '')}"), styles["body"]))
                story.append(Paragraph(self._safe(f"对应目的：{item.get('purpose', '')}"), styles["bullet"]))
                story.append(Paragraph(self._safe(f"重点材料/指标：{item.get('focus', '')}"), styles["bullet"]))
                story.append(Paragraph(self._safe(f"为什么重要：{item.get('importance', '')}"), styles["bullet"]))
            story.append(Spacer(1, 8))

        doc.build(story, onFirstPage=self._decorate_page, onLaterPages=self._decorate_page)
        return buffer.getvalue()

    def save_pdf(self, report: dict[str, Any]) -> Path:
        pdf_bytes = self.build_pdf(report)
        filename = f"{report.get('company_code', 'report')}_{report.get('task_id', 'latest')}.pdf"
        path = self.export_dir / filename
        path.write_bytes(pdf_bytes)
        return path

    def _decorate_page(self, canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("STSong-Light", 9)
        canvas.setFillColor(colors.HexColor("#7B6A56"))
        canvas.drawString(doc.leftMargin, 10 * mm, DEFAULT_REPORT_TITLE)
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"第 {canvas.getPageNumber()} 页")
        canvas.restoreState()

    def _styles(self) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title",
                parent=base["Title"],
                fontName="STSong-Light",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1A1612"),
                alignment=TA_LEFT,
            ),
            "meta": ParagraphStyle(
                "meta",
                parent=base["Normal"],
                fontName="STSong-Light",
                fontSize=9.5,
                leading=13,
                textColor=colors.HexColor("#5F564B"),
            ),
            "section": ParagraphStyle(
                "section",
                parent=base["Heading2"],
                fontName="STSong-Light",
                fontSize=14,
                leading=18,
                textColor=colors.HexColor("#1D1A15"),
                spaceAfter=5,
            ),
            "subsection": ParagraphStyle(
                "subsection",
                parent=base["Heading3"],
                fontName="STSong-Light",
                fontSize=11.5,
                leading=15,
                textColor=colors.HexColor("#3E362D"),
                spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "body",
                parent=base["BodyText"],
                fontName="STSong-Light",
                fontSize=10.5,
                leading=16,
                textColor=colors.HexColor("#2A2622"),
            ),
            "bullet": ParagraphStyle(
                "bullet",
                parent=base["BodyText"],
                fontName="STSong-Light",
                fontSize=10,
                leading=15,
                textColor=colors.HexColor("#2A2622"),
                leftIndent=6,
            ),
        }

    @staticmethod
    def _safe(value: str) -> str:
        return (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
