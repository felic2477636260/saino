from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class GameProductPipelineSkill(BaseSkill):
    skill_id = "game_product_pipeline"
    skill_name = "GameProductPipelineSkill"
    skill_type = "custom"
    skill_layer = "enhancement"
    skill_category = "analysis"
    goal = "分析游戏新品储备、测试进展与上线节奏"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["game", "product", "pipeline"]
    priority = 74
    description = "分析新品、储备产品、测试节点与商业化节奏。"
    trigger_condition = "产品储备/新品节奏子任务触发。"
    target_aspects = ("product_pipeline",)
    evaluation_criteria = ["是否识别新品储备和测试节点", "是否绑定对应来源页码", "是否提示兑现节奏风险"]
    example_use_case = "判断游戏公司新品是否足以承接老产品衰退。"
    expert_role = "产品与业务分析师"
    domain_focus = "新品储备、测试节点、上线节奏和商业化接续。"
    core_questions = ["新品储备够不够支撑后续增长？", "测试到上线之间有没有明显的节奏风险？"]
    preferred_terms = ["产品管线", "商业化节奏", "新品承接", "上线窗口"]
    translation_rule = "把管线术语翻译成老板最关心的接续问题：什么时候能上线，能不能接上收入。"
    reasoning_style = "先看储备和测试节点，再判断上线节奏与收入承接是否匹配。"

    keywords = ["新品", "储备", "测试", "公测", "上线", "产品线", "pipeline", "进展", "预约", "发行"]

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
                summary="当前材料未提供足够的新品储备与上线节奏证据。",
                pending_checks=["补充新品储备、测试进度和版号披露章节。"],
                confidence=0.26,
            )

        findings = [
            "材料中存在关于新品储备、测试或上线节奏的直接披露，可作为未来收入承接观察点。",
            "若新品披露集中在单一产品或单一时间窗口，应警惕节奏波动带来的兑现风险。",
        ]
        return self.build_result(
            summary="新品储备与上线节奏将决定未来收入能否顺利承接。",
            findings=findings,
            recommendations=["跟踪新品测试、公测、版号与正式上线之间的兑现节奏。"],
            evidence=hits[:4],
            confidence=0.76 if len(hits) >= 3 else 0.6,
        )
