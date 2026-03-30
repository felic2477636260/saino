from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class CustomSkillTemplate(BaseSkill):
    skill_name = "CustomSkillTemplate"
    skill_type = "custom"
    skill_category = "analysis"
    description = "用于复制扩展的新领域 Skill 模板。"
    trigger_condition = "当子任务 aspect 与目标领域匹配且证据中出现相关关键词时触发。"
    target_aspects = ("replace_me",)
    input_schema = {
        "user_query": "原始用户问题",
        "subtask": "规划后的子任务",
        "evidence_pack": "检索生成的结构化证据包",
        "evidence": "兼容旧链路的证据列表",
    }
    output_schema = {
        "summary": "该技能的核心结论",
        "findings": "结构化发现列表",
        "recommendations": "行动建议列表",
        "evidence_refs": "证据引用列表",
        "pending_checks": "待核验事项",
        "confidence": "0~1 置信度",
    }
    evidence_requirements = "结论必须绑定 evidence_pack 中的证据；无证据时返回证据不足。"
    evaluation_criteria = ["是否绑定页码与来源", "是否避免空泛结论", "是否输出待核验事项"]
    dependencies = ["RetrieveSkill"]
    failure_handling = "若命中证据不足，返回低置信结论与待核验项。"
    example_use_case = "为新行业新增可组合的专题分析模块。"

    keywords = ["请替换为领域关键词"]

    def match(self, context: dict[str, Any]) -> bool:
        if not self.supports_aspect(context):
            return False
        evidence_text = " ".join(self.evidence_text(item) for item in self.evidence_items(context))
        target = f"{context.get('user_query', '')} {context.get('query', '')} {evidence_text}"
        return any(keyword.lower() in target.lower() for keyword in self.keywords)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="当前材料支持不足。",
                pending_checks=["补充该领域的定向证据后再运行本技能。"],
                confidence=0.2,
            )

        return self.build_result(
            summary="请基于当前领域规则补充实现。",
            findings=["这里返回结构化发现。"],
            recommendations=["这里返回建议动作。"],
            evidence=hits[:4],
            confidence=0.6,
        )
