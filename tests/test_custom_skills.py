from skills.custom.game_industry_trend import GameIndustryTrendSkill
from skills.custom.game_operation_performance import GameOperationPerformanceSkill
from skills.custom.game_product_pipeline import GameProductPipelineSkill


def test_custom_skills_return_structured_results():
    context = {
        "query": "请分析新品进展、经营表现和 AI 趋势",
        "evidence": [
            {"chunk_text": "新品测试上线节奏良好，储备产品丰富", "page_no": 1, "source": "a.pdf"},
            {"chunk_text": "核心产品流水改善，业绩回升", "page_no": 2, "source": "b.pdf"},
            {"chunk_text": "OpenAI 智能体与 GDC 会议推动游戏行业技术变化", "page_no": 3, "source": "c.pdf"},
        ],
    }
    for skill in (GameProductPipelineSkill(), GameOperationPerformanceSkill(), GameIndustryTrendSkill()):
        assert skill.match(context) is True
        result = skill.run(context)
        assert "summary" in result
