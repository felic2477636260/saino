from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameRegulationAndPublishingSkill(BaseSkill):
    skill_id = "game_regulation_publishing"
    skill_name = "GameRegulationAndPublishingSkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "识别版号、监管和发行节奏对兑现的影响"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "regulation", "publishing"]
    priority = 72
    description = "识别版号、政策环境、发行节奏和监管约束线索。"
    trigger_condition = "版号/发行/监管子任务触发。"
    target_aspects = ("regulation_publishing",)
    evaluation_criteria = ["是否识别版号或监管依赖", "是否提示发行节奏不确定性", "是否标记证据不足"]
    example_use_case = "判断游戏公司新品兑现是否受版号与监管节奏制约。"
    expert_role = "治理与合规分析师"
    domain_focus = "版号、审批节奏、发行准备度和监管约束。"
    core_questions = ["新品上线最容易被什么外部环节卡住？", "监管和发行节奏会不会推迟收入兑现？"]
    preferred_terms = ["版号节奏", "发行窗口", "监管约束", "上线兑现"]
    translation_rule = "把监管术语翻译成老板能理解的时间问题：能不能按计划上、会不会影响收入确认。"
    reasoning_style = "先看版号和监管线索，再判断这些约束会不会推迟商业化兑现。"

    keywords = ["版号", "政策", "发行", "监管", "审批", "合规", "上线", "许可证"]

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
                summary="当前材料未提供足够的版号或发行监管证据。",
                pending_checks=["补充版号、审批或发行安排披露。"],
                confidence=0.26,
            )

        findings = [
            "已识别到版号、发行或监管相关线索，相关节奏变化可能影响新品兑现时间。",
            "若监管与发行披露集中于少量表述，应避免过度外推为确定性风险。 ",
        ]
        return self.build_result(
            summary="版号与发行节奏仍是新品兑现最关键的外部约束之一。",
            findings=findings,
            recommendations=["持续跟踪版号、发行准备度与上线窗口的匹配情况。"],
            evidence=hits[:4],
            confidence=0.72 if len(hits) >= 2 else 0.55,
        )
