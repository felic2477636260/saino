from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseSkill(ABC):
    skill_id = ""
    skill_name = "BaseSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "analysis"
    description = ""
    goal = ""
    version = "0.1.0"
    trigger_condition = ""
    applicable_when: list[str] = []
    not_applicable_when: list[str] = []
    target_aspects: tuple[str, ...] = ()
    required_inputs: list[str] = []
    optional_inputs: list[str] = []
    dependencies: list[str] = []
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}
    evidence_requirements = "结论应优先绑定强证据；证据不足时必须明确降级或列入待核验。"
    evaluation_criteria: list[str] = []
    failure_handling = "当输入不足或证据不足时，输出保守判断、待核验事项和限制说明。"
    priority = 50
    tags: list[str] = []
    example_use_case = ""
    expert_role = ""
    domain_focus = ""
    core_questions: list[str] = []
    preferred_terms: list[str] = []
    translation_rule = ""
    reasoning_style = ""

    def info(self) -> dict[str, Any]:
        return {
            "skill_id": self.id,
            "name": self.skill_name,
            "skill_type": self.skill_type,
            "skill_layer": self.skill_layer,
            "skill_category": self.skill_category,
            "description": self.description,
            "goal": self.goal,
            "version": self.version,
            "trigger_condition": self.trigger_condition,
            "applicable_when": list(self.applicable_when),
            "not_applicable_when": list(self.not_applicable_when),
            "required_inputs": self.required_inputs or sorted(self.input_schema.keys()),
            "optional_inputs": list(self.optional_inputs),
            "input_schema": dict(self.input_schema),
            "output_schema": dict(self.output_schema),
            "evidence_requirements": self.evidence_requirements,
            "evaluation_criteria": list(self.evaluation_criteria),
            "dependencies": list(self.dependencies),
            "failure_handling": self.failure_handling,
            "priority": self.priority,
            "tags": list(self.tags),
            "example_use_case": self.example_use_case,
            "target_aspects": list(self.target_aspects),
            "expert_role": self.expert_role,
            "domain_focus": self.domain_focus,
            "core_questions": list(self.core_questions),
            "preferred_terms": list(self.preferred_terms),
            "translation_rule": self.translation_rule,
            "reasoning_style": self.reasoning_style,
        }

    @property
    def id(self) -> str:
        return self.skill_id or self.skill_name

    def match(self, context: dict[str, Any]) -> bool:
        return self.supports_aspect(context)

    def supports_aspect(self, context: dict[str, Any]) -> bool:
        if not self.target_aspects:
            return True
        subtask = context.get("subtask") or {}
        aspect = subtask.get("aspect") or subtask.get("key")
        if not aspect:
            return True
        return aspect in self.target_aspects

    def evidence_items(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        evidence_pack = context.get("evidence_pack") or {}
        items = evidence_pack.get("items") or context.get("evidence") or []
        return [dict(item) for item in items]

    def hits_by_keywords(self, context: dict[str, Any], keywords: Iterable[str]) -> list[dict[str, Any]]:
        evidence = self.evidence_items(context)
        lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
        return [
            item
            for item in evidence
            if any(keyword in self.evidence_text(item).lower() for keyword in lowered_keywords)
        ]

    def evidence_text(self, item: dict[str, Any]) -> str:
        return " ".join(
            part
            for part in (
                item.get("chunk_text") or item.get("text") or "",
                item.get("section_title") or "",
                item.get("section_path") or "",
                item.get("source") or "",
            )
            if part
        )

    def to_evidence_ref(self, item: dict[str, Any]) -> dict[str, Any]:
        text = item.get("chunk_text") or item.get("text") or ""
        quote = text[:200].strip()
        return {
            "source": item.get("source", ""),
            "page_no": int(item.get("page_no") or 0),
            "text": text,
            "section_title": item.get("section_title", ""),
            "section_path": item.get("section_path", ""),
            "relevance_score": float(item.get("relevance_score") or 0),
            "reason": item.get("reason", ""),
            "quote": quote,
            "evidence_type": item.get("evidence_type", ""),
            "priority_level": int(item.get("priority_level") or 0),
        }

    def build_result(
        self,
        *,
        summary: str,
        findings: list[str] | None = None,
        recommendations: list[str] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        confidence: float = 0.5,
        pending_checks: list[str] | None = None,
        risk_flags: list[str] | None = None,
        limitations: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence_refs = [self.to_evidence_ref(item) for item in (evidence or [])]
        return {
            "skill_id": self.id,
            "skill_name": self.skill_name,
            "skill_type": self.skill_type,
            "skill_layer": self.skill_layer,
            "skill_category": self.skill_category,
            "summary": summary,
            "findings": findings or [],
            "recommendations": recommendations or [],
            "confidence": round(max(0.0, min(confidence, 1.0)), 2),
            "pending_checks": pending_checks or [],
            "risk_flags": risk_flags or [],
            "limitations": limitations or [],
            "evidence_refs": evidence_refs,
            "citation_count": len(evidence_refs),
            "expert_profile": self.expert_profile(),
            "metadata": metadata or {},
        }

    def expert_profile(self) -> dict[str, Any]:
        return {
            "expert_role": self.expert_role,
            "domain_focus": self.domain_focus,
            "core_questions": list(self.core_questions),
            "preferred_terms": list(self.preferred_terms),
            "translation_rule": self.translation_rule,
            "reasoning_style": self.reasoning_style,
        }

    @abstractmethod
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
