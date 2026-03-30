from models.schemas import PreferenceProfile
from skills.registry import build_default_registry
from skills.router import SkillRouter


def test_skill_router_prioritizes_finance_preferences():
    registry = build_default_registry()
    router = SkillRouter(registry)
    profile = PreferenceProfile(
        report_style="concise",
        focus_priority="finance_first",
        preferred_topics=["cashflow", "finance"],
        summary_first=True,
        evidence_strictness="strict",
        preferred_output_emphasis=["summary", "score", "finance"],
        user_intent_raw="重点看现金流和偿债能力，先给结论和评分。",
        confidence=0.86,
    )
    context = {
        "query": "请生成企业体检报告",
        "user_query": "请生成企业体检报告",
        "preference_profile": profile.model_dump(),
        "evidence_pack": {
            "items": [
                {"chunk_text": "经营现金流净额改善，但短债压力仍需关注。", "section_title": "现金流", "section_path": "财务分析/现金流"},
                {"chunk_text": "扣非净利润改善，费用率仍承压。", "section_title": "利润", "section_path": "财务分析/利润"},
            ]
        },
    }

    decision = router.build_route(context=context, industry="generic", preference_profile=profile)

    assert "financial_health" in decision["analysis_aspects"]
    assert "cashflow_health" in decision["analysis_aspects"]
    assert "earnings_quality" in decision["analysis_aspects"]
    assert "cashflow_specialist" in decision["enabled_skill_ids"]
    assert "earnings_quality_specialist" in decision["enabled_skill_ids"]


def test_skill_router_adds_game_enhancements_when_signals_detected():
    registry = build_default_registry()
    router = SkillRouter(registry)
    profile = PreferenceProfile(
        report_style="deep",
        focus_priority="growth_first",
        preferred_topics=["product", "overseas"],
        tone_preference="investment_research",
        summary_first=True,
        evidence_strictness="standard",
        preferred_output_emphasis=["summary", "product"],
        domain_hint="game",
        user_intent_raw="重点看游戏产品生命周期和出海能力。",
        confidence=0.88,
    )
    context = {
        "query": "分析游戏公司经营情况",
        "user_query": "分析游戏公司经营情况",
        "preference_profile": profile.model_dump(),
        "evidence_pack": {
            "items": [
                {"chunk_text": "新品测试推进，老产品流水回落，海外发行节奏加快。", "section_title": "产品周期", "section_path": "经营情况/产品周期"},
                {"chunk_text": "版号获批后预计将于下半年上线。", "section_title": "版号", "section_path": "经营情况/版号"},
            ]
        },
    }

    decision = router.build_route(context=context, industry="game", preference_profile=profile)

    assert "product_pipeline" in decision["analysis_aspects"]
    assert "operation_performance" in decision["analysis_aspects"]
    assert "overseas_market" in decision["analysis_aspects"] or "overseas_business" in decision["analysis_aspects"]
    assert "game_product_pipeline" in decision["enabled_skill_ids"]
