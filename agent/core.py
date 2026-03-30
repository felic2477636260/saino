from __future__ import annotations

import logging
import uuid
from typing import Any

from agent.planning import build_analysis_plan
from config.prompt_templates import ASK_PROMPT
from services.db import Database
from services.llm_client import LLMClient
from services.preference_parser import PreferenceParser
from skills.registry import SkillRegistry, build_default_registry
from skills.router import SkillRouter


logger = logging.getLogger(__name__)


class SainoAgent:
    def __init__(
        self,
        registry: SkillRegistry | None = None,
        db: Database | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.registry = registry or build_default_registry()
        self.db = db or Database()
        self.llm_client = llm_client or LLMClient()
        self.preference_parser = PreferenceParser()
        self.router = SkillRouter(self.registry)

    def analyze(
        self,
        company_code: str,
        query: str,
        top_k: int = 8,
        preference_note: str = "",
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        context: dict[str, Any] = {
            "task_id": task_id,
            "company_code": company_code,
            "query": query,
            "user_query": query,
            "preference_note": preference_note,
            "top_k": top_k,
        }
        self.db.upsert_task(task_id, company_code, query, "analyze", "running")

        try:
            retrieve_skill = self.registry.get("RetrieveSkill")
            global_pack = retrieve_skill.run(context)
            context.update(global_pack)
            self.db.log_skill(
                task_id,
                retrieve_skill.skill_name,
                retrieve_skill.skill_type,
                "success",
                global_pack["evidence_pack"].get("coverage_summary", ""),
            )

            company_row = self.db.fetchone("SELECT industry FROM company WHERE company_code = ?", (company_code,))
            industry = company_row["industry"] if company_row and company_row["industry"] else "generic"

            preference_profile = self.preference_parser.parse(
                preference_note=preference_note,
                query=query,
                llm_client=self.llm_client,
            )
            context["preference_profile"] = preference_profile.model_dump()

            routing = self.router.build_route(
                context=context,
                industry=industry,
                preference_profile=preference_profile,
            )
            context["routing"] = routing

            analysis_plan = build_analysis_plan(
                query=query,
                industry=industry,
                selected_aspects=routing["analysis_aspects"],
            )
            context["analysis_plan"] = analysis_plan

            analysis_results: list[dict[str, Any]] = []
            custom_outputs: dict[str, Any] = {}
            skill_runs: list[dict[str, Any]] = [
                self._skill_run_summary(
                    skill_name=retrieve_skill.skill_name,
                    skill_type=retrieve_skill.skill_type,
                    skill_category=retrieve_skill.skill_category,
                    summary=global_pack["evidence_pack"].get("coverage_summary", ""),
                    confidence=1.0,
                    evidence_count=len(global_pack.get("evidence", [])),
                ),
            ]
            activated_generic = [retrieve_skill.skill_name]
            activated_custom: list[str] = []

            for subtask in analysis_plan:
                subtask_context = {
                    **context,
                    "subtask": subtask,
                    "query": subtask["query_focus"],
                    "top_k": max(4, top_k),
                }
                subtask_pack = retrieve_skill.run(subtask_context)
                subtask_context.update(subtask_pack)

                allowed_skill_ids = set(routing["aspect_skill_map"].get(subtask["key"], []))
                outputs: list[dict[str, Any]] = []
                for skill in self.registry.matching(
                    subtask_context,
                    skill_category="analysis",
                    allowed_skill_ids=allowed_skill_ids or None,
                ):
                    try:
                        output = skill.run(subtask_context)
                    except Exception as exc:
                        logger.exception("skill %s failed on subtask %s: %s", skill.skill_name, subtask["key"], exc)
                        self.db.log_skill(task_id, skill.skill_name, skill.skill_type, "failed", str(exc))
                        continue
                    if not self._should_keep_output(output):
                        continue
                    outputs.append(output)
                    self.db.log_skill(
                        task_id,
                        skill.skill_name,
                        skill.skill_type,
                        "success",
                        f"{subtask['key']} | {output.get('summary', '')[:120]}",
                    )
                    skill_runs.append(
                        self._skill_run_summary(
                            skill_name=skill.skill_name,
                            skill_type=skill.skill_type,
                            skill_category=skill.skill_category,
                            summary=output.get("summary", ""),
                            confidence=float(output.get("confidence", 0)),
                            evidence_count=len(output.get("evidence_refs", [])),
                            findings_count=len(output.get("findings", [])),
                            recommendations_count=len(output.get("recommendations", [])),
                        )
                    )
                    if skill.skill_type == "custom":
                        custom_outputs[skill.skill_name] = output
                        if skill.skill_name not in activated_custom:
                            activated_custom.append(skill.skill_name)
                    elif skill.skill_name not in activated_generic:
                        activated_generic.append(skill.skill_name)

                analysis_results.append(
                    {
                        "subtask": subtask,
                        "evidence_pack": subtask_pack["evidence_pack"],
                        "outputs": outputs,
                    }
                )

            context["analysis_results"] = analysis_results
            context["custom_skill_outputs"] = custom_outputs

            validation_outputs: list[dict[str, Any]] = []
            for skill in self.registry.matching(context, skill_category="validation"):
                try:
                    output = skill.run(context)
                except Exception as exc:
                    logger.exception("validation skill %s failed: %s", skill.skill_name, exc)
                    self.db.log_skill(task_id, skill.skill_name, skill.skill_type, "failed", str(exc))
                    continue
                validation_outputs.append(output)
                self.db.log_skill(task_id, skill.skill_name, skill.skill_type, "success", output.get("summary", ""))
                skill_runs.append(
                    self._skill_run_summary(
                        skill_name=skill.skill_name,
                        skill_type=skill.skill_type,
                        skill_category=skill.skill_category,
                        summary=output.get("summary", ""),
                        confidence=float(output.get("confidence", 0)),
                        evidence_count=len(output.get("evidence_refs", [])),
                        findings_count=len(output.get("findings", [])),
                        recommendations_count=len(output.get("recommendations", [])),
                    )
                )
                if skill.skill_name not in activated_generic:
                    activated_generic.append(skill.skill_name)

            context["validation_outputs"] = validation_outputs

            score_dimension_outputs: list[dict[str, Any]] = []
            for skill in self.registry.matching(context, skill_category="score_dimension"):
                try:
                    output = skill.run(context)
                except Exception as exc:
                    logger.exception("score dimension skill %s failed: %s", skill.skill_name, exc)
                    self.db.log_skill(task_id, skill.skill_name, skill.skill_type, "failed", str(exc))
                    continue
                score_dimension_outputs.append(output)
                self.db.log_skill(task_id, skill.skill_name, skill.skill_type, "success", output.get("summary", ""))
                skill_runs.append(
                    self._skill_run_summary(
                        skill_name=skill.skill_name,
                        skill_type=skill.skill_type,
                        skill_category=skill.skill_category,
                        summary=output.get("summary", ""),
                        confidence=float(output.get("confidence", 0)),
                        evidence_count=len(output.get("evidence_refs", [])),
                        findings_count=len(output.get("negative_factors", [])),
                        recommendations_count=len(output.get("positive_factors", [])),
                    )
                )
                if skill.skill_name not in activated_generic:
                    activated_generic.append(skill.skill_name)

            context["score_dimension_outputs"] = score_dimension_outputs

            risk_skill = self.registry.get("RiskScoreSkill")
            risk = risk_skill.run(context)
            context["risk"] = risk
            self.db.log_skill(task_id, risk_skill.skill_name, risk_skill.skill_type, "success", risk.get("rationale", ""))
            self.db.execute(
                "INSERT INTO risk_result(task_id, risk_level, risk_score, matched_signals) VALUES(?, ?, ?, ?)",
                (task_id, risk["risk_level"], risk["risk_score"], ",".join(risk.get("top_deductions", []))),
            )
            skill_runs.append(
                self._skill_run_summary(
                    skill_name=risk_skill.skill_name,
                    skill_type=risk_skill.skill_type,
                    skill_category=risk_skill.skill_category,
                    summary=risk.get("rationale", ""),
                    confidence=0.84,
                    evidence_count=len(risk.get("matched_evidence", [])),
                    findings_count=len(risk.get("top_deductions", [])),
                )
            )
            if risk_skill.skill_name not in activated_generic:
                activated_generic.append(risk_skill.skill_name)

            context["skill_runs"] = skill_runs
            context["activated_skills"] = {
                "generic": activated_generic,
                "custom": activated_custom,
            }

            explain_skill = self.registry.get("ExplainSkill")
            explained = explain_skill.run(context)
            skill_runs.append(
                self._skill_run_summary(
                    skill_name=explain_skill.skill_name,
                    skill_type=explain_skill.skill_type,
                    skill_category=explain_skill.skill_category,
                    summary="已完成报告整合与统一结构输出。",
                    confidence=0.88,
                    evidence_count=len(explained.get("evidence", [])),
                    findings_count=len(explained.get("findings", [])),
                    recommendations_count=len(explained.get("recommendations", [])),
                )
            )
            self.db.log_skill(task_id, explain_skill.skill_name, explain_skill.skill_type, "success", "report_generated")
            if explain_skill.skill_name not in activated_generic:
                activated_generic.append(explain_skill.skill_name)

            result = {
                "task_id": task_id,
                "company_code": company_code,
                "query": query,
                "report_title": explained.get("report_title", "企业体检报告"),
                "summary": explained["summary"],
                "total_score": risk.get("total_score", risk["risk_score"]),
                "risk_score": risk["risk_score"],
                "risk_level": risk["risk_level"],
                "findings": explained["findings"],
                "evidence": explained.get("evidence", [])[: max(8, top_k)],
                "recommendations": explained["recommendations"],
                "activated_skills": {
                    "generic": activated_generic,
                    "custom": activated_custom,
                },
                "custom_skill_outputs": custom_outputs,
                "report_sections": explained["report_sections"],
                "analysis_plan": analysis_plan,
                "verification_notes": explained.get("verification_notes", []),
                "skill_runs": skill_runs,
                "report_payload": explained.get("report_payload", {}),
                "preference_profile": preference_profile.model_dump(),
                "available_exports": ["json", "markdown", "html", "pdf"],
            }
            self.db.upsert_task(task_id, company_code, query, "analyze", "completed", result)
            return result
        except Exception as exc:
            logger.exception("analysis failed for task %s: %s", task_id, exc)
            self.db.upsert_task(
                task_id,
                company_code,
                query,
                "analyze",
                "failed",
                {"error": str(exc)},
            )
            raise

    def ask(self, company_code: str | None, question: str, task_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
        retrieve_skill = self.registry.get("RetrieveSkill")
        context = {"company_code": company_code, "query": question, "user_query": question, "top_k": top_k}
        retrieved = retrieve_skill.run(context)
        evidence = retrieved.get("evidence", [])[:top_k]
        answer = self.llm_client.answer_question(f"{ASK_PROMPT}\n问题：{question}", evidence=evidence)
        return {
            "task_id": task_id,
            "answer": answer,
            "evidence": [
                {
                    "page_no": item.get("page_no", 0),
                    "text": item.get("chunk_text") or item.get("text", ""),
                    "source": item.get("source", ""),
                    "section_title": item.get("section_title", ""),
                    "section_path": item.get("section_path", ""),
                    "relevance_score": item.get("relevance_score", 0),
                    "reason": item.get("reason", ""),
                    "quote": item.get("quote", ""),
                    "evidence_type": item.get("evidence_type", ""),
                    "priority_level": int(item.get("priority_level", 0)),
                }
                for item in evidence
            ],
        }

    @staticmethod
    def _should_keep_output(output: dict[str, Any]) -> bool:
        return bool(
            output.get("summary")
            or output.get("findings")
            or output.get("recommendations")
            or output.get("evidence_refs")
            or output.get("pending_checks")
        )

    @staticmethod
    def _skill_run_summary(
        *,
        skill_name: str,
        skill_type: str,
        skill_category: str,
        summary: str,
        confidence: float,
        evidence_count: int,
        findings_count: int = 0,
        recommendations_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "name": skill_name,
            "skill_type": skill_type,
            "skill_category": skill_category,
            "summary": summary,
            "confidence": round(confidence, 2),
            "evidence_count": evidence_count,
            "findings_count": findings_count,
            "recommendations_count": recommendations_count,
        }
