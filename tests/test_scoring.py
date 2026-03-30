from agent.composer import compose_report, redundancy_merger
from skills.evidence_ranking import select_ranked_evidence
from skills.risk_score import RiskScoreSkill
from skills.score_dimensions import (
    BusinessQualityScoreSkill,
    CashflowHealthScoreSkill,
    EarningsQualityScoreSkill,
    IndustryEnvironmentScoreSkill,
)


def sample_context() -> dict:
    evidence_items = [
        {
            "source": "年报",
            "page_no": 12,
            "chunk_text": "公司收入同比增长12%，主营业务收入恢复，核心产品流水回升。",
            "section_title": "经营情况",
            "section_path": "经营情况/主营业务",
            "relevance_score": 28,
        },
        {
            "source": "年报",
            "page_no": 18,
            "chunk_text": "扣非净利润改善，但费用率仍然承压，利润持续性仍需验证。",
            "section_title": "财务分析",
            "section_path": "财务分析/利润",
            "relevance_score": 26,
        },
        {
            "source": "年报",
            "page_no": 20,
            "chunk_text": "经营现金流净额回升，但投资活动现金流波动较大，短期偿债压力可控。",
            "section_title": "现金流",
            "section_path": "财务分析/现金流",
            "relevance_score": 25,
        },
        {
            "source": "研报",
            "page_no": 3,
            "chunk_text": "新品上线节奏改善，版号获批带来新的收入承接机会，但竞争仍然激烈。",
            "section_title": "产品周期",
            "section_path": "行业分析/产品周期",
            "relevance_score": 24,
        },
        {
            "source": "研报",
            "page_no": 5,
            "chunk_text": "行业需求恢复，外部政策环境稳定，海外市场存在扩张机会。",
            "section_title": "行业趋势",
            "section_path": "行业分析/需求环境",
            "relevance_score": 22,
        },
    ]
    return {
        "query": "请生成企业体检报告",
        "user_query": "请生成企业体检报告",
        "company_code": "002555",
        "evidence_pack": {"items": evidence_items},
        "analysis_results": [
            {
                "subtask": {"key": "financial_health", "title": "财务与经营健康度"},
                "evidence_pack": {"items": evidence_items[:3]},
                "outputs": [
                    {
                        "summary": "利润改善已经出现，但费用率和现金流仍决定修复质量。",
                        "findings": ["利润修复出现，但兑现质量仍需验证。"],
                        "recommendations": ["继续跟踪费用率与经营现金流。"],
                        "pending_checks": [],
                    }
                ],
            },
            {
                "subtask": {"key": "product_pipeline", "title": "产品生命周期与储备"},
                "evidence_pack": {"items": evidence_items[3:4]},
                "outputs": [
                    {
                        "summary": "新品储备改善，为后续收入承接提供支撑。",
                        "findings": ["新版号获批是当前最直接的上行变量。"],
                        "recommendations": ["关注新品上线后的流水兑现。"],
                        "pending_checks": [],
                    }
                ],
            },
        ],
        "validation_outputs": [
            {
                "skill_name": "EvidenceGapSkill",
                "pending_checks": ["部分利润持续性仍缺少季度口径验证。"],
            }
        ],
        "analysis_plan": [],
        "skill_runs": [],
        "activated_skills": {"generic": [], "custom": []},
    }


def test_rule_based_scoring_and_aggregation():
    context = sample_context()
    dimensions = [
        BusinessQualityScoreSkill().run(context),
        EarningsQualityScoreSkill().run(context),
        CashflowHealthScoreSkill().run(context),
        IndustryEnvironmentScoreSkill().run(context),
    ]
    assert len(dimensions) == 4
    assert sum(item["score"] for item in dimensions) > 0
    assert all(item["sub_scores"] for item in dimensions)

    context["score_dimension_outputs"] = dimensions
    aggregate = RiskScoreSkill().run(context)

    assert aggregate["total_score"] == sum(item["score"] for item in dimensions)
    assert aggregate["risk_level"] in {"低风险", "中低风险", "中风险", "中高风险", "高风险"}
    assert aggregate["top_deductions"]


def test_compose_report_keeps_executive_summary_unique():
    context = sample_context()
    dimensions = [
        BusinessQualityScoreSkill().run(context),
        EarningsQualityScoreSkill().run(context),
        CashflowHealthScoreSkill().run(context),
        IndustryEnvironmentScoreSkill().run(context),
    ]
    context["score_dimension_outputs"] = dimensions
    context["risk"] = RiskScoreSkill().run(context)

    report = compose_report(context, llm_client=None)
    payload = report["report_payload"]

    assert payload["report_layer"]["executive_summary"]
    assert all(section["title"] != "执行摘要" for section in payload["sections"])
    assert payload["report_layer"]["score_breakdown"]["dimensions"]
    assert any(section["title"] == "综合判断" for section in payload["sections"])
    assert report["evidence"][0]["text"]
    assert payload["evidence_layer"]["evidence_index"][0]["text"]
    assert any(section["body"] for section in payload["sections"])


def test_compose_report_does_not_repeat_section_summary_in_body():
    context = sample_context()
    dimensions = [
        BusinessQualityScoreSkill().run(context),
        EarningsQualityScoreSkill().run(context),
        CashflowHealthScoreSkill().run(context),
        IndustryEnvironmentScoreSkill().run(context),
    ]
    context["score_dimension_outputs"] = dimensions
    context["risk"] = RiskScoreSkill().run(context)

    report = compose_report(context, llm_client=None)

    for section in report["report_payload"]["sections"]:
        summary = (section.get("summary") or "").strip()
        body = [paragraph.strip() for paragraph in section.get("body", []) if paragraph.strip()]
        if summary:
            assert all(paragraph != summary for paragraph in body)


def test_redundancy_merger_drops_repeated_summary_and_body():
    sections = [
        {
            "key": "overall",
            "title": "综合判断",
            "summary": "利润改善仍需继续验证。",
            "body": ["利润改善仍需继续验证。", "经营现金流仍需继续跟踪。"],
            "pending_checks": [],
        },
        {
            "key": "finance",
            "title": "财务质量",
            "summary": "经营现金流仍需继续跟踪。",
            "body": ["经营现金流仍需继续跟踪。", "新品兑现节奏需要持续观察。"],
            "pending_checks": [],
        },
    ]

    merged = redundancy_merger("结论先行：利润改善仍需继续验证。", sections)

    assert merged[0]["summary"] == ""
    assert merged[0]["body"] == ["经营现金流仍需继续跟踪。"]
    assert merged[1]["summary"] == ""
    assert merged[1]["body"] == ["新品兑现节奏需要持续观察。"]


def test_ranked_evidence_prefers_quantitative_and_operating_fact():
    items = [
        {
            "source": "行业综述",
            "page_no": 2,
            "chunk_text": "行业政策环境稳定，市场景气度有望回暖。",
            "section_title": "行业概览",
            "section_path": "行业概览",
            "relevance_score": 95,
        },
        {
            "source": "公司年报",
            "page_no": 12,
            "chunk_text": "收入同比增长12%，净利润同比增长5%，经营现金流回升。",
            "section_title": "经营情况",
            "section_path": "经营情况/主营业务",
            "relevance_score": 42,
        },
        {
            "source": "公司公告",
            "page_no": 4,
            "chunk_text": "新品上线并获得版号，带来新的收入承接机会。",
            "section_title": "产品进展",
            "section_path": "产品进展",
            "relevance_score": 38,
        },
    ]

    ranked = select_ranked_evidence(items, keywords=("收入", "增长", "新品"), limit=2)

    assert ranked[0]["source"] == "公司年报"
    assert ranked[1]["source"] == "公司公告"
