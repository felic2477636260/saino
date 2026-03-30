from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameOperationPerformanceSkill(BaseSkill):
    skill_id = "game_operation_performance"
    skill_name = "GameOperationPerformanceSkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "分析游戏老产品表现、用户活跃与经营承压/改善线索"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "operation", "product_lifecycle"]
    priority = 73
    description = "分析核心产品表现、流水趋势、用户活跃与经营改善/承压线索。"
    trigger_condition = "运营表现子任务触发。"
    target_aspects = ("operation_performance", "financial_health")
    evaluation_criteria = ["是否识别流水/活跃/老产品趋势", "是否区分改善与承压", "是否输出经营跟踪建议"]
    example_use_case = "判断老产品基本盘是否仍能支撑业绩。"
    expert_role = "产品运营分析师"
    domain_focus = "核心产品流水、用户活跃、留存和老产品基本盘。"
    core_questions = ["老产品基本盘是不是还稳得住？", "运营改善是短期活动拉动，还是产品生命力仍在？"]
    preferred_terms = ["流水", "活跃", "留存", "长线运营"]
    translation_rule = "把运营术语翻译成老板能直接理解的两个问题：用户还在不在，钱还能不能持续赚。"
    reasoning_style = "先看流水和活跃，再判断改善是运营动作拉动还是产品基本盘修复。"

    keywords = ["流水", "活跃", "留存", "运营", "业绩", "改善", "承压", "增长", "下滑", "老产品", "生命周期"]

    def match(self, context: dict[str, Any]) -> bool:
        if not self.supports_aspect(context):
            return False
        target = f"{context.get('user_query', '')} {context.get('query', '')} " + " ".join(
            self.evidence_text(item) for item in self.evidence_items(context)
        )
        return any(word in target for word in self.keywords)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="当前材料未提供足够的运营表现证据。",
                pending_checks=["补充核心产品流水、活跃或经营承压相关章节。"],
                confidence=0.28,
            )

        findings = [
            "已识别到经营表现与产品运营质量相关证据，可用于判断基本盘稳定性。",
            "若改善信号主要来自短期运营活动，需要额外核查可持续性。",
        ]
        return self.build_result(
            summary="核心产品基本盘是否稳住，是当前经营判断的关键。",
            findings=findings,
            recommendations=["重点复核核心产品流水趋势、老产品衰退速度和新品承接关系。"],
            evidence=hits[:4],
            confidence=0.74 if len(hits) >= 3 else 0.58,
        )
