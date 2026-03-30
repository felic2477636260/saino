from __future__ import annotations

import uuid
from typing import Any

from config.prompt_templates import ANALYZE_PROMPT
from services.db import Database
from services.llm_client import LLMClient
from skills.registry import SkillRegistry, build_default_registry


class LegacySainoAgent:
    def __init__(self, registry: SkillRegistry | None = None, db: Database | None = None, llm_client: LLMClient | None = None) -> None:
        self.registry = registry or build_default_registry()
        self.db = db or Database()
        self.llm_client = llm_client or LLMClient()

    def analyze(self, company_code: str, query: str, top_k: int = 8) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        context: dict[str, Any] = {"task_id": task_id, "company_code": company_code, "query": query, "user_query": query, "top_k": top_k}

        retrieve_skill = self.registry.get("RetrieveSkill")
        retrieved = retrieve_skill.run(context)
        context.update(retrieved)

        risk_skill = self.registry.get("RiskScoreSkill")
        risk = risk_skill.run(context)
        context["risk"] = risk

        custom_outputs: dict[str, Any] = {}
        activated_custom: list[str] = []
        for skill in self.registry.matching(context, skill_type="custom", skill_category="analysis"):
            output = skill.run(context)
            if not output.get("findings") and not output.get("evidence_refs"):
                continue
            custom_outputs[skill.skill_name] = output
            activated_custom.append(skill.skill_name)

        findings = self._build_findings(context.get("evidence", []), custom_outputs, risk)
        recommendations = self._build_recommendations(risk, custom_outputs)
        prompt = f"{ANALYZE_PROMPT}\n查询：{query}\n风险：{risk}\n定制分析：{custom_outputs}"
        llm_summary = self.llm_client.generate_report(prompt=prompt, evidence=context.get("evidence", []))
        report_sections = {
            "conclusion": f"综合判断，公司当前风险等级为{risk.get('risk_level', '未知')}，风险分为 {risk.get('risk_score', 0)}。",
            "major_findings": "；".join(findings) if findings else "当前证据不足。",
            "risk_diagnosis": f"命中信号：{', '.join(risk.get('matched_signals', [])) or '暂无明确风险信号'}。",
            "key_evidence": "；".join(
                f"{item.get('source')} P{item.get('page_no')}" for item in context.get("evidence", [])[:5]
            )
            or "当前证据不足。",
            "action_suggestions": "；".join(recommendations),
            "industry_custom_analysis": "；".join(
                value.get("summary") or "当前材料支持不足" for value in custom_outputs.values()
            )
            or "未触发定制分析。",
        }
        return {
            "task_id": task_id,
            "company_code": company_code,
            "query": query,
            "report_title": "企业体检报告",
            "summary": llm_summary,
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "findings": findings,
            "evidence": [
                {
                    "page_no": item["page_no"],
                    "text": item["chunk_text"],
                    "source": item["source"],
                    "section_title": item.get("section_title", ""),
                    "section_path": item.get("section_path", ""),
                    "relevance_score": item.get("relevance_score", 0),
                    "reason": item.get("reason", ""),
                    "quote": item.get("quote", ""),
                }
                for item in context.get("evidence", [])[:8]
            ],
            "recommendations": recommendations,
            "activated_skills": {
                "generic": ["RetrieveSkill", "RiskScoreSkill", "LegacyExplainFlow"],
                "custom": activated_custom,
            },
            "custom_skill_outputs": custom_outputs,
            "report_sections": report_sections,
            "analysis_plan": [],
            "verification_notes": [],
            "skill_runs": [],
            "report_payload": {},
            "available_exports": ["json"],
        }

    @staticmethod
    def _build_findings(evidence: list[dict[str, Any]], custom_outputs: dict[str, Any], risk: dict[str, Any]) -> list[str]:
        findings: list[str] = []
        if risk.get("matched_signals"):
            findings.append(f"风险信号共命中 {len(risk['matched_signals'])} 次。")
        for value in custom_outputs.values():
            findings.extend(value.get("findings", []))
        if not findings and evidence:
            findings.append("已检索到相关材料，但尚未形成强结论，建议补充更多定向查询。")
        return findings[:6]

    @staticmethod
    def _build_recommendations(risk: dict[str, Any], custom_outputs: dict[str, Any]) -> list[str]:
        recs = []
        if risk.get("risk_level") == "高":
            recs.append("优先复核经营承压与产品兑现节奏，安排专项跟踪。")
        else:
            recs.append("持续跟踪核心产品和新品上线表现。")
        for value in custom_outputs.values():
            recs.extend(value.get("recommendations", []))
        return recs[:6] or ["当前证据不足，建议补充材料后再次分析。"]
