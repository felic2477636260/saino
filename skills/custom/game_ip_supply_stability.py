from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameIPSupplyStabilitySkill(BaseSkill):
    skill_id = "game_ip_supply_stability"
    skill_name = "GameIPSupplyStabilitySkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "识别 IP 依赖、续作供给和内容稳定性"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "ip", "content_supply"]
    priority = 68
    description = "分析 IP 依赖、续作供给与内容生产稳定性。"
    trigger_condition = "IP 依赖/内容供给子任务触发。"
    target_aspects = ("ip_dependency", "product_pipeline")
    evaluation_criteria = ["是否识别 IP 依赖度", "是否提示内容供给稳定性", "是否避免无证据外推"]
    example_use_case = "判断公司是否过度依赖单一 IP 或单一内容供给路径。"
    expert_role = "内容供给分析师"
    domain_focus = "IP 依赖度、内容供给连续性和研发组织稳定性。"
    core_questions = ["内容供给是不是过度依赖少数 IP 或项目？", "一旦核心项目波动，后续供给能不能补上？"]
    preferred_terms = ["IP 依赖", "内容供给", "续作储备", "研发稳定性"]
    translation_rule = "把 IP 和供给术语翻译成老板能直接判断的稳定性问题：后面有没有货，是否过度押注单点。"
    reasoning_style = "先看 IP 和储备分布，再判断内容供给的连续性和波动风险。"

    keywords = ["IP", "授权", "续作", "联动", "内容供给", "研发团队", "世界观", "储备", "精品化"]

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
                summary="当前证据不足以判断 IP 依赖与内容供给稳定性。",
                pending_checks=["补充 IP 授权、续作储备或研发组织相关披露。"],
                confidence=0.24,
            )

        return self.build_result(
            summary="内容供给连续性与 IP 依赖度决定产品矩阵的稳定性。",
            findings=[
                "材料涉及 IP、续作或内容供给表述，可用于观察产品矩阵是否依赖单一成功要素。",
                "若内容供给高度依赖少数核心项目，需警惕储备波动带来的业绩弹性风险。",
            ],
            recommendations=["结合新品储备与研发组织披露，评估内容供给的连续性。"],
            evidence=hits[:4],
            confidence=0.67 if len(hits) >= 2 else 0.5,
        )
