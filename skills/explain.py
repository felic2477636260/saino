from __future__ import annotations

from typing import Any

from agent.composer import compose_report
from services.llm_client import LLMClient
from skills.base import BaseSkill


class ExplainSkill(BaseSkill):
    skill_id = "report_composer"
    skill_name = "ExplainSkill"
    skill_type = "generic"
    skill_layer = "output"
    skill_category = "output"
    goal = "把结构化分析、评分和证据整合为给人看的最终报告"
    required_inputs = ["analysis_results", "score_dimension_outputs", "risk", "preference_profile"]
    tags = ["report", "output", "delivery"]
    priority = 95
    description = "将分析结果重组为面向人的最终报告，输出执行摘要、核心结论、风险机会、深度分析和调研建议。"
    trigger_condition = "所有分析与验证阶段完成后执行。"
    evaluation_criteria = [
        "是否优先输出面向人的结论与分析",
        "是否将证据作为支撑层而不是主体",
        "是否保留待核验事项与下一步建议",
    ]
    example_use_case = "将检索、分析和验证结果整理成用户可直接阅读和使用的企业调研报告。"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        return compose_report(context=context, llm_client=self.llm_client)
