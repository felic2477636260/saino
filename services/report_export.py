from __future__ import annotations

from html import escape
from typing import Any

from services.report_display import build_summary_metrics


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


class ReportExportService:
    def build_markdown(self, report: dict[str, Any]) -> str:
        payload = report.get("report_payload") or {}
        cover = payload.get("cover") or {}
        report_layer = payload.get("report_layer") or {}
        sections = payload.get("sections") or report_layer.get("deep_sections") or []
        metrics = build_summary_metrics(report)
        executive_summary = (report_layer.get("executive_summary") or report.get("summary") or "").strip()
        risk_groups = report_layer.get("risk_opportunities") or {}
        action_items = report_layer.get("action_items") or []
        key_evidence = (payload.get("evidence_layer") or {}).get("key_evidence") or []

        lines = [
            f"# {cover.get('title', report.get('report_title', '企业体检报告'))}",
            "",
            f"- 公司代码：{cover.get('company_code', report.get('company_code', '-'))}",
            f"- 查询：{cover.get('query', report.get('query', '-'))}",
            *[f"- {item['label']}：{item['value']}" for item in metrics],
            "",
        ]

        if executive_summary:
            lines.extend(["## 执行摘要", "", executive_summary, ""])

        if sections:
            lines.extend(["## 报告正文", ""])
        for section in sections:
            summary, body = _normalize_section_content(section)
            lines.append(f"## {section.get('title', section.get('key', '报告章节'))}")
            if section.get("expert_role"):
                lines.append(f"_{section['expert_role']}_")
                lines.append("")
            if summary:
                lines.append(summary)
                lines.append("")
            for paragraph in body:
                lines.append(paragraph)
                lines.append("")
            pending_checks = section.get("pending_checks") or []
            if pending_checks and section.get("key") != "verification_notes":
                lines.append("待核验：")
                lines.extend(f"- {item}" for item in pending_checks)
                lines.append("")

        risks = risk_groups.get("risks") or []
        opportunities = risk_groups.get("opportunities") or []
        if risks or opportunities:
            lines.extend(["## 风险与机会", ""])
            if risks:
                lines.append("### 主要风险")
                lines.append("")
                for item in risks:
                    lines.append(f"- {item.get('title', '')}：{item.get('summary', '')}")
                    if item.get("basis"):
                        lines.append(f"  依据：{item['basis']}")
                    if item.get("impact"):
                        lines.append(f"  含义：{item['impact']}")
                lines.append("")
            if opportunities:
                lines.append("### 主要机会")
                lines.append("")
                for item in opportunities:
                    lines.append(f"- {item.get('title', '')}：{item.get('summary', '')}")
                    if item.get("basis"):
                        lines.append(f"  依据：{item['basis']}")
                    if item.get("impact"):
                        lines.append(f"  含义：{item['impact']}")
                lines.append("")

        if key_evidence:
            lines.extend(["## 关键证据", ""])
            for item in key_evidence:
                lines.append(f"- {item.get('title', '')}：{item.get('summary', '')}")
                if item.get("supports"):
                    lines.append(f"  支持判断：{item['supports']}")
                if item.get("citation"):
                    lines.append(f"  引用：{item['citation']}")
            lines.append("")

        if action_items:
            lines.extend(["## 建议动作", ""])
            for index, item in enumerate(action_items, start=1):
                lines.append(f"{index}. 建议动作：{item.get('action', '')}")
                lines.append(f"   对应目的：{item.get('purpose', '')}")
                lines.append(f"   重点材料/指标：{item.get('focus', '')}")
                lines.append(f"   为什么重要：{item.get('importance', '')}")
                lines.append("")

        return "\n".join(lines).strip() + "\n"

    def build_html(self, report: dict[str, Any]) -> str:
        payload = report.get("report_payload") or {}
        cover = payload.get("cover") or {}
        report_layer = payload.get("report_layer") or {}
        sections = payload.get("sections") or report_layer.get("deep_sections") or []
        metrics = build_summary_metrics(report)
        executive_summary = (report_layer.get("executive_summary") or report.get("summary") or "").strip()
        risk_groups = report_layer.get("risk_opportunities") or {}
        action_items = report_layer.get("action_items") or []
        key_evidence = (payload.get("evidence_layer") or {}).get("key_evidence") or []

        section_html: list[str] = []
        for section in sections:
            summary, body = _normalize_section_content(section)
            body_html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in body)
            pending_checks = section.get("pending_checks") or []
            pending_html = "".join(f"<li>{escape(item)}</li>" for item in pending_checks)
            section_html.append(
                f"""
                <section class="report-section">
                  <h2>{escape(section.get('title', section.get('key', '报告章节')))}</h2>
                  {f"<p class='eyebrow'>{escape(section.get('expert_role', ''))}</p>" if section.get('expert_role') else ''}
                  {f"<p class='summary'>{escape(summary)}</p>" if summary else ''}
                  {body_html}
                  {f"<h3>待核验</h3><ul>{pending_html}</ul>" if pending_html and section.get('key') != 'verification_notes' else ''}
                </section>
                """
            )

        risk_html = "".join(
            f"<article class='mini-card'><strong>{escape(item.get('title', ''))}</strong><p>{escape(item.get('summary', ''))}</p><small>{escape(item.get('basis', ''))}</small><small>{escape(item.get('impact', ''))}</small></article>"
            for item in (risk_groups.get("risks") or [])
        )
        opportunity_html = "".join(
            f"<article class='mini-card'><strong>{escape(item.get('title', ''))}</strong><p>{escape(item.get('summary', ''))}</p><small>{escape(item.get('basis', ''))}</small><small>{escape(item.get('impact', ''))}</small></article>"
            for item in (risk_groups.get("opportunities") or [])
        )
        evidence_html = "".join(
            f"<article class='mini-card'><strong>{escape(item.get('title', ''))}</strong><p>{escape(item.get('summary', ''))}</p><small>{escape(item.get('supports', ''))}</small><small>{escape(item.get('citation', ''))}</small></article>"
            for item in key_evidence
        )
        action_html = "".join(
            f"<article class='mini-card'><strong>{escape(item.get('action', ''))}</strong><p>对应目的：{escape(item.get('purpose', ''))}</p><p>重点材料/指标：{escape(item.get('focus', ''))}</p><small>{escape(item.get('importance', ''))}</small></article>"
            for item in action_items
        )

        metrics_html = "".join(
            f"<div><strong>{escape(item['label'])}</strong><div>{escape(item['value'])}</div></div>"
            for item in metrics
        )

        executive_summary_html = (
            f"""
            <section class="report-section">
              <h2>执行摘要</h2>
              <p class="summary">{escape(executive_summary)}</p>
            </section>
            """
            if executive_summary
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <title>{escape(cover.get('title', report.get('report_title', '企业体检报告')))}</title>
    <style>
      body {{
        font-family: 'Noto Serif CJK SC', 'Source Han Serif SC', serif;
        margin: 40px auto;
        max-width: 940px;
        line-height: 1.85;
        color: #1f1c18;
        background:
          radial-gradient(circle at top left, rgba(239, 226, 196, 0.56), transparent 28%),
          linear-gradient(180deg, #faf7f1 0%, #f3ede1 100%);
        padding: 0 24px 56px;
      }}
      header {{
        background: linear-gradient(135deg, #f5e9cf, #fcfaf4);
        border: 1px solid #dcc9ab;
        border-radius: 22px;
        padding: 30px;
        margin-bottom: 24px;
      }}
      .meta {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
      }}
      .report-section {{
        background: rgba(255, 253, 248, 0.9);
        border: 1px solid #e6d8c0;
        border-radius: 18px;
        padding: 22px 24px;
        margin-bottom: 18px;
      }}
      .eyebrow {{
        color: #8b6b43;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 12px;
      }}
      .summary {{
        color: #5b5042;
      }}
      .insight-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
      }}
      .mini-card {{
        background: rgba(255,255,255,0.72);
        border: 1px solid #e7d7bd;
        border-radius: 14px;
        padding: 16px;
      }}
      .mini-card small {{
        display: block;
        color: #5b5042;
        margin-top: 6px;
      }}
    </style>
  </head>
  <body>
    <header>
      <p>企业体检报告</p>
      <h1>{escape(cover.get('title', report.get('report_title', '企业体检报告')))}</h1>
      <div class="meta">
        <div><strong>公司代码</strong><div>{escape(cover.get('company_code', report.get('company_code', '-')))}</div></div>
        <div><strong>查询</strong><div>{escape(cover.get('query', report.get('query', '-')))}</div></div>
        {metrics_html}
      </div>
    </header>
    {executive_summary_html}
    {''.join(section_html)}
    {f"<section class='report-section'><h2>风险与机会</h2><h3>主要风险</h3><div class='insight-grid'>{risk_html}</div><h3>主要机会</h3><div class='insight-grid'>{opportunity_html}</div></section>" if risk_html or opportunity_html else ""}
    {f"<section class='report-section'><h2>关键证据</h2><div class='insight-grid'>{evidence_html}</div></section>" if evidence_html else ""}
    {f"<section class='report-section'><h2>建议动作</h2><div class='insight-grid'>{action_html}</div></section>" if action_html else ""}
  </body>
</html>
"""
