from __future__ import annotations

from typing import Any

from services.retrieval_service import RetrievalService
from skills.base import BaseSkill


class RetrieveSkill(BaseSkill):
    skill_id = "retrieve"
    skill_name = "RetrieveSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "retrieval"
    goal = "文档检索、证据标准化与证据包组装"
    required_inputs = ["query", "company_code", "top_k"]
    tags = ["retrieval", "evidence", "foundation"]
    priority = 100
    description = "执行查询扩展、证据检索、去重与证据包组装。"
    trigger_condition = "所有分析任务都先执行检索。"
    output_schema = {"evidence_pack": "结构化证据包", "evidence": "兼容旧链路的证据列表"}
    evaluation_criteria = ["是否返回高相关证据", "是否保留页码与章节路径", "是否避免相同页重复堆积"]
    example_use_case = "为每个子任务构造独立证据包。"

    def __init__(self, service: RetrievalService | None = None) -> None:
        self.service = service or RetrievalService()

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        query = context.get("query", "")
        company_code = context.get("company_code")
        top_k = int(context.get("top_k", 8))
        subtask = context.get("subtask") or {}
        aspect = context.get("aspect") or subtask.get("aspect")
        evidence_pack = self.service.build_evidence_pack(query=query, company_code=company_code, top_k=top_k, aspect=aspect)
        return {"evidence_pack": evidence_pack, "evidence": evidence_pack["items"]}
