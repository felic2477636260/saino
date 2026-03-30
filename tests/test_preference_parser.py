from services.preference_parser import PreferenceParser


def test_preference_parser_extracts_structured_preferences():
    parser = PreferenceParser()
    profile = parser.parse(
        preference_note="更关心财务风险，重点看现金流和偿债能力，先给结论和评分，报告简洁一点，偏投资研究风格。",
        query="请生成企业体检报告",
        llm_client=None,
    )

    assert profile.report_style == "concise"
    assert profile.focus_priority in {"finance_first", "risk_first"}
    assert "cashflow" in profile.preferred_topics
    assert profile.summary_first is True
    assert profile.tone_preference == "investment_research"
    assert "score" in profile.preferred_output_emphasis
    assert profile.confidence > 0.5


def test_preference_parser_defaults_when_empty():
    parser = PreferenceParser()
    profile = parser.parse(preference_note="", query="请生成企业体检报告", llm_client=None)

    assert profile.report_style == "standard"
    assert profile.focus_priority == "balanced"
    assert profile.user_intent_raw == ""
    assert profile.confidence == 0.0
