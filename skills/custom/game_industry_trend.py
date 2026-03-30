from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameIndustryTrendSkill(BaseSkill):
    skill_id = "game_industry_trend"
    skill_name = "GameIndustryTrendSkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "识别游戏行业趋势和技术变量对经营的影响"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "industry", "trend"]
    priority = 71
    description = "分析 AI、智能体、GDC、行业景气度与外部技术趋势对游戏公司的影响。"
    trigger_condition = "行业趋势子任务触发。"
    target_aspects = ("industry_trend",)
    evaluation_criteria = ["是否识别外部趋势变量", "是否避免将行业噪音直接等同公司利好", "是否输出趋势跟踪建议"]
    example_use_case = "识别技术趋势与行业会议对研发效率和发行策略的影响。"
    expert_role = "行业研究员"
    domain_focus = "行业景气、技术趋势、工具链变化和外部催化。"
    core_questions = ["行业变化会不会改变公司的兑现难度？", "技术趋势是真正红利，还是短期叙事？"]
    preferred_terms = ["景气度", "技术催化", "工具链", "兑现难度"]
    translation_rule = "不用空泛讲行业，只解释这些外部变化怎么影响公司的研发、发行和兑现。"
    reasoning_style = "先判断外部趋势是否真实存在，再看它如何传导到公司经营。"

    keywords = ["AI", "智能体", "GDC", "大会", "行业趋势", "技术", "OpenAI", "agent", "景气度", "产业"]

    def match(self, context: dict[str, Any]) -> bool:
        if not self.supports_aspect(context):
            return False
        target = f"{context.get('user_query', '')} {context.get('query', '')} " + " ".join(
            self.evidence_text(item) for item in self.evidence_items(context)
        )
        lowered = target.lower()
        return any(word.lower() in lowered for word in self.keywords)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="当前样本未检出显著行业趋势证据。",
                pending_checks=["补充行业研究报告或技术会议材料。"],
                confidence=0.24,
            )

        findings = [
            "外部材料显示 AI 与智能体等技术趋势可能影响研发、发行和运营效率。",
            "行业趋势对单家公司业绩的传导路径仍需结合产品和组织能力核验。",
        ]
        return self.build_result(
            summary="外部技术与行业趋势提供中长期变量，但对短期业绩的传导仍需核验。",
            findings=findings,
            recommendations=["持续跟踪行业会议、技术工具链落地与竞争格局变化。"],
            evidence=hits[:4],
            confidence=0.7 if len(hits) >= 2 else 0.52,
        )
