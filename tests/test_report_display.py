import fitz

from services.report_display import build_summary_metrics
from services.report_export import ReportExportService
from services.report_pdf import ReportPDFService


def sample_report() -> dict:
    return {
        "company_code": "002555",
        "query": "请生成企业体检报告",
        "report_title": "企业体检报告",
        "total_score": 63,
        "risk_level": "中低风险",
        "risk_score": 63,
        "report_payload": {
            "cover": {
                "title": "企业体检报告",
                "company_code": "002555",
                "query": "请生成企业体检报告",
            },
            "summary_cards": [
                {"label": "总分", "value": "63"},
                {"label": "风险等级", "value": "中低风险"},
                {"label": "经营基本盘", "value": "18 / 30"},
                {"label": "利润兑现质量", "value": "16 / 25"},
                {"label": "现金回流与财务缓冲", "value": "14 / 25"},
                {"label": "外部环境与竞争位置", "value": "15 / 20"},
            ],
            "sections": [
                {
                    "key": "score_breakdown",
                    "title": "综合判断",
                    "summary": "总分 63/100，风险等级 中低风险。",
                    "body": ["公司当前处在经营基本盘稳定、但利润兑现质量仍需验证的阶段。"],
                    "pending_checks": [],
                }
            ],
            "evidence_layer": {
                "key_evidence": [
                    {
                        "title": "年报核心披露",
                        "summary": "主营业务恢复，但利润兑现和现金回流仍需继续核实。",
                        "supports": "支持当前总体判断。",
                        "citation": "年报 P12",
                        "evidence": [],
                    }
                ]
            },
            "report_layer": {
                "executive_summary": "总体判断：公司当前总分为63/100，风险等级为中低风险，整体处于经营基本稳定但仍有观察点。",
                "score_breakdown": {
                    "total_score": 63,
                    "risk_level": "中低风险",
                    "overall_state": "经营基本稳定但仍有观察点",
                },
                "risk_opportunities": {
                    "risks": [{"title": "利润修复的成色还不够", "summary": "利润修复仍需现金流继续印证。", "basis": "年报 P12", "impact": "会影响利润质量与韧性。", "follow_up": "", "tone": "risk", "evidence": []}],
                    "opportunities": [{"title": "经营基本盘仍在托底", "summary": "主营业务恢复提供了基础支撑。", "basis": "年报 P12", "impact": "有助于收入和基本盘稳定。", "follow_up": "", "tone": "good", "evidence": []}],
                },
                "action_items": [
                    {
                        "action": "复核经营现金流净额、回款节奏和应收变化",
                        "purpose": "确认利润修复是否已经落到现金质量上",
                        "focus": "经营现金流净额、应收账款、回款周期",
                        "importance": "这决定利润修复是账面改善还是现金质量也在回稳。",
                    }
                ],
            },
        },
    }


def test_build_summary_metrics_normalizes_and_merges_scores():
    metrics = build_summary_metrics(sample_report())

    assert metrics[:3] == [
        {"label": "总分", "value": "63"},
        {"label": "风险等级", "value": "中低风险"},
        {"label": "经营基本盘", "value": "18 / 30"},
    ]


def test_report_markdown_and_html_include_total_score_and_risk_level():
    service = ReportExportService()
    report = sample_report()

    markdown = service.build_markdown(report)
    assert "- 总分：63" in markdown
    assert "- 风险等级：中低风险" in markdown
    assert "## 执行摘要" in markdown
    assert "## 综合判断" in markdown
    assert "## 风险与机会" in markdown
    assert "## 建议动作" in markdown

    html = service.build_html(report)
    assert "总分" in html
    assert "63" in html
    assert "风险等级" in html
    assert "中低风险" in html
    assert "执行摘要" in html
    assert "建议动作" in html


def test_report_pdf_includes_total_score_and_risk_level(work_tmp_dir):
    service = ReportPDFService(export_dir=work_tmp_dir)
    pdf_bytes = service.build_pdf(sample_report())

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in document)
    compact = "".join(text.split())

    assert "总分：63" in compact
    assert "风险等级：中低风险" in compact
    assert "执行摘要" in compact


def test_report_exports_dedupe_repeated_section_summary_and_body(work_tmp_dir):
    report = sample_report()
    report["report_payload"]["sections"] = [
        {
            "key": "score_breakdown",
            "title": "综合判断",
            "summary": "利润质量仍需继续验证。",
            "body": [
                "利润质量仍需继续验证。",
                "经营现金流仍需继续跟踪。",
                "经营现金流仍需继续跟踪。",
            ],
            "pending_checks": [],
        }
    ]

    markdown = ReportExportService().build_markdown(report)
    assert markdown.count("利润质量仍需继续验证。") == 1
    assert markdown.count("经营现金流仍需继续跟踪。") == 1

    html = ReportExportService().build_html(report)
    assert html.count("利润质量仍需继续验证。") == 1
    assert html.count("经营现金流仍需继续跟踪。") == 1

    pdf_bytes = ReportPDFService(export_dir=work_tmp_dir).build_pdf(report)
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    compact = "".join("".join(page.get_text() for page in document).split())
    assert compact.count("利润质量仍需继续验证。") == 1
    assert compact.count("经营现金流仍需继续跟踪。") == 1
