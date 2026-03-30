from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


RISK_LEVEL_BANDS = (
    (80, "低风险"),
    (60, "中低风险"),
    (40, "中风险"),
    (20, "中高风险"),
    (0, "高风险"),
)


class RiskScoreSkill(BaseSkill):
    skill_id = "risk_score_aggregate"
    skill_name = "RiskScoreSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "score_aggregate"
    goal = "聚合四维规则评分，输出总分、风险等级和主要扣分原因"
    required_inputs = ["score_dimension_outputs"]
    tags = ["score", "aggregate", "transparent"]
    priority = 88
    description = "汇总四维规则化评分，生成总分、风险等级和主要扣分原因。"
    trigger_condition = "四个评分维度完成后执行。"
    evaluation_criteria = ["总分是否来自固定维度汇总", "风险等级映射是否清晰", "扣分原因是否可追溯"]
    example_use_case = "为首页、评分拆解和导出统一提供总分与风险等级。"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        dimensions = context.get("score_dimension_outputs") or []
        if not dimensions:
            return {
                "total_score": 40,
                "risk_score": 40,
                "risk_level": "中风险",
                "top_deductions": ["评分维度尚未完成，当前只保留保守基线分。"],
                "score_note": "本次评分基于当前披露材料，若材料缺失则按保守口径处理。",
                "matched_evidence": [],
                "rationale": "四个评分维度尚未形成完整结果，暂按中性偏保守口径给出基线判断。",
            }

        total_score = int(sum(int(item.get("score", 0)) for item in dimensions))
        weakest = sorted(
            (
                (sub, dimension)
                for dimension in dimensions
                for sub in dimension.get("sub_scores", [])
            ),
            key=lambda pair: (
                pair[0].get("score", 0) / max(pair[0].get("max_score", 1), 1),
                pair[0].get("max_score", 0),
            ),
        )

        top_deductions: list[str] = []
        matched_evidence: list[dict[str, Any]] = []
        for sub_score, dimension in weakest:
            reason = sub_score.get("reason")
            if reason and reason not in top_deductions:
                top_deductions.append(f"{dimension.get('dimension_label', '')} - {sub_score.get('label', '')}：{reason}")
            matched_evidence.extend(sub_score.get("evidence_refs", [])[:1])
            if len(top_deductions) >= 3:
                break

        total_score = max(0, min(100, total_score))
        risk_level = self._risk_level(total_score)
        rationale = "；".join(top_deductions) or "四个维度已完成结构化评分。"

        return {
            "total_score": total_score,
            "risk_score": total_score,
            "risk_level": risk_level,
            "top_deductions": top_deductions or ["当前未识别出明确的集中扣分项。"],
            "score_note": "本次评分并非对企业长期价值的最终定论，而是基于当前已披露材料对经营健康度的阶段性体检。",
            "matched_evidence": matched_evidence[:5],
            "rationale": rationale,
        }

    @staticmethod
    def _risk_level(total_score: int) -> str:
        for threshold, label in RISK_LEVEL_BANDS:
            if total_score >= threshold:
                return label
        return "中风险"
