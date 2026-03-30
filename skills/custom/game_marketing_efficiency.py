from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameMarketingEfficiencySkill(BaseSkill):
    skill_id = "game_marketing_efficiency"
    skill_name = "GameMarketingEfficiencySkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "分析游戏投放效率、销售费用和营销回收"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "marketing", "roi"]
    priority = 70
    description = "分析买量依赖、销售费用投放和营销效率线索。"
    trigger_condition = "营销效率/买量子任务触发。"
    target_aspects = ("marketing_efficiency", "operation_performance")
    evaluation_criteria = ["是否识别投放和获客线索", "是否提示营销效率不确定性", "是否输出跟踪建议"]
    example_use_case = "评估新品买量强度和营销费用回报的可持续性。"
    expert_role = "营销效率顾问"
    domain_focus = "买量依赖、销售费用、获客成本和投放回收。"
    core_questions = ["增长是产品自然拉动，还是投放推起来的？", "投放回收效率能不能支持持续增长？"]
    preferred_terms = ["获客成本", "投放回收", "买量依赖", "ROI"]
    translation_rule = "营销术语只保留必要部分，重点讲清楚增长是不是花钱买来的、回不回得来。"
    reasoning_style = "先看投放和费用，再判断增长质量和投放回收的持续性。"

    keywords = ["买量", "营销", "投放", "销售费用", "推广", "获客", "ROI", "广告", "宣发"]

    def match(self, context: dict[str, Any]) -> bool:
        if not self.supports_aspect(context):
            return False
        target = f"{context.get('user_query', '')} {context.get('query', '')} " + " ".join(
            self.evidence_text(item) for item in self.evidence_items(context)
        )
        return any(word.lower() in target.lower() for word in self.keywords)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="当前证据不足以判断营销效率或买量依赖。",
                pending_checks=["补充销售费用、推广投放或获客效率材料。"],
                confidence=0.24,
            )

        return self.build_result(
            summary="投放与营销效率决定增长质量，不能只看收入改善本身。",
            findings=[
                "材料存在营销投放或销售费用相关披露，可用于判断增长获取方式是否依赖买量。",
                "若收入改善伴随投放拉升，需要进一步核查投放回收效率和可持续性。",
            ],
            recommendations=["结合销售费用率和新品表现评估投放驱动增长的质量。"],
            evidence=hits[:4],
            confidence=0.66 if len(hits) >= 2 else 0.5,
        )
