from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameOverseasMarketSkill(BaseSkill):
    skill_id = "game_overseas_market"
    skill_name = "GameOverseasMarketSkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "分析游戏海外发行与区域市场兑现能力"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "overseas", "regional"]
    priority = 69
    description = "分析海外发行、区域市场和境外经营风险线索。"
    trigger_condition = "海外市场子任务触发。"
    target_aspects = ("overseas_market", "regulation_publishing")
    evaluation_criteria = ["是否识别海外收入/发行线索", "是否提示区域政策或执行差异", "是否绑定来源"]
    example_use_case = "判断海外发行是否构成新增增长点或风险暴露。"
    expert_role = "海外业务分析师"
    domain_focus = "海外发行、区域市场差异、本地化和境外兑现能力。"
    core_questions = ["海外市场是真增量还是概念布局？", "不同区域的政策和渠道差异会不会放大执行波动？"]
    preferred_terms = ["区域市场", "本地化", "海外发行", "境外兑现"]
    translation_rule = "把区域和出海术语翻译成老板最关心的结果：这块业务能不能复制，风险在哪。"
    reasoning_style = "先找海外收入和发行线索，再判断区域差异对兑现和风险的影响。"

    keywords = ["海外", "境外", "出海", "国际", "区域市场", "港澳台", "海外发行"]

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
                summary="当前材料未提供明确海外市场证据。",
                pending_checks=["补充海外发行、境外收入或区域市场策略披露。"],
                confidence=0.22,
            )

        return self.build_result(
            summary="海外市场可能提供新增增长点，但执行波动和区域差异也会同步放大。",
            findings=[
                "材料中存在海外/境外市场表述，可作为增长来源或区域风险观察点。",
                "海外扩张需要额外关注本地化、渠道与政策差异带来的执行波动。",
            ],
            recommendations=["将海外发行进度与区域市场政策变化纳入持续跟踪。"],
            evidence=hits[:4],
            confidence=0.64 if len(hits) >= 2 else 0.48,
        )
