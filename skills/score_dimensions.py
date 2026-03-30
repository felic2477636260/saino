from __future__ import annotations

from typing import Any

from skills.base import BaseSkill
from skills.evidence_ranking import dedupe_evidence, evidence_text, select_ranked_evidence, to_evidence_ref


POSITIVE_WORDS = ("增长", "改善", "提升", "回升", "稳健", "修复", "优化", "充足", "恢复", "承接")
NEGATIVE_WORDS = ("下滑", "承压", "不足", "波动", "减值", "亏损", "拖累", "放缓", "依赖", "失真")
SEVERE_NEGATIVE_WORDS = ("减值", "亏损", "恶化", "大幅下滑", "持续承压", "无法", "缺失")


def collect_context_evidence(context: dict[str, Any]) -> list[dict[str, Any]]:
    buckets: list[dict[str, Any]] = []
    global_pack = context.get("evidence_pack") or {}
    buckets.extend(global_pack.get("items") or [])
    for result in context.get("analysis_results", []):
        buckets.extend((result.get("evidence_pack") or {}).get("items") or [])
    return dedupe_evidence(buckets)


class ScoreDimensionSkill(BaseSkill):
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "score_dimension"
    goal = "按照规则对子项评分并生成可追溯的维度分数"
    required_inputs = ["evidence_pack", "analysis_results"]
    tags = ["score", "foundation", "rule_based"]
    priority = 82
    max_score = 0
    dimension_key = ""
    dimension_label = ""
    subitems: list[dict[str, Any]] = []

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        evidence = collect_context_evidence(context)
        sub_scores: list[dict[str, Any]] = []
        positive_factors: list[str] = []
        negative_factors: list[str] = []
        uncertainty_flags: list[str] = []

        for spec in self.subitems:
            entry = self._score_subitem(evidence=evidence, spec=spec)
            sub_scores.append(entry)
            if entry["polarity"] == "positive":
                positive_factors.append(entry["reason"])
            elif entry["polarity"] == "negative":
                negative_factors.append(entry["reason"])
            if entry["uncertainty"]:
                uncertainty_flags.append(f"{entry['label']}：材料仍偏薄，按保守口径评分。")

        total_score = sum(item["score"] for item in sub_scores)
        selected_evidence = []
        for item in sorted(sub_scores, key=lambda sub: (sub["score"] / max(sub["max_score"], 1), sub["max_score"])):
            selected_evidence.extend(item["evidence_refs"][:1])
        evidence_refs = dedupe_evidence(selected_evidence, limit=4)

        summary = self._build_summary(total_score=total_score, positive_factors=positive_factors, negative_factors=negative_factors)
        return {
            "skill_name": self.skill_name,
            "skill_type": self.skill_type,
            "skill_category": self.skill_category,
            "dimension_key": self.dimension_key,
            "dimension_label": self.dimension_label,
            "score": total_score,
            "max_score": self.max_score,
            "summary": summary,
            "positive_factors": positive_factors[:3],
            "negative_factors": negative_factors[:3],
            "uncertainty_flags": uncertainty_flags[:3],
            "sub_scores": sub_scores,
            "evidence_refs": evidence_refs,
            "confidence": self._confidence(sub_scores),
        }

    def _score_subitem(self, *, evidence: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
        ranked = select_ranked_evidence(evidence, keywords=spec["keywords"], limit=2)
        refs = [to_evidence_ref(item) for item in ranked]
        if not ranked:
            fallback = max(1, round(spec["max_score"] * 0.4))
            return {
                "key": spec["key"],
                "label": spec["label"],
                "score": fallback,
                "max_score": spec["max_score"],
                "reason": f"{spec['label']}缺少直接证据，本次按保守口径处理。",
                "summary": f"{spec['label']}当前证据不足，结论强度受限。",
                "polarity": "neutral",
                "uncertainty": True,
                "evidence_refs": [],
                "follow_up": spec.get("follow_up", spec["label"]),
            }

        positive_hits = 0
        negative_hits = 0
        severe_hits = 0
        for item in ranked:
            text = evidence_text(item)
            positive_hits += sum(1 for token in spec.get("positive_words", POSITIVE_WORDS) if token in text)
            negative_hits += sum(1 for token in spec.get("negative_words", NEGATIVE_WORDS) if token in text)
            severe_hits += sum(1 for token in spec.get("severe_words", SEVERE_NEGATIVE_WORDS) if token in text)

        evidence_strength = max((ref.get("priority_level", 1) for ref in refs), default=1)
        score, polarity = self._score_band(
            max_score=spec["max_score"],
            positive_hits=positive_hits,
            negative_hits=negative_hits,
            severe_hits=severe_hits,
            evidence_strength=evidence_strength,
        )
        reason = self._build_reason(spec=spec, polarity=polarity, positive_hits=positive_hits, negative_hits=negative_hits, uncertainty=False)
        summary = self._build_subitem_summary(spec=spec, polarity=polarity, score=score, max_score=spec["max_score"])
        return {
            "key": spec["key"],
            "label": spec["label"],
            "score": score,
            "max_score": spec["max_score"],
            "reason": reason,
            "summary": summary,
            "polarity": polarity,
            "uncertainty": False,
            "evidence_refs": refs,
            "follow_up": spec.get("follow_up", spec["label"]),
        }

    @staticmethod
    def _score_band(
        *,
        max_score: int,
        positive_hits: int,
        negative_hits: int,
        severe_hits: int,
        evidence_strength: int,
    ) -> tuple[int, str]:
        if severe_hits or negative_hits >= positive_hits + 2:
            return (max(0, max_score - 7), "negative") if max_score >= 8 else (max(0, max_score - 5), "negative")
        if negative_hits > positive_hits:
            return max(1, round(max_score * 0.4)), "negative"
        if positive_hits and not negative_hits:
            bonus = 1 if evidence_strength >= 3 else 0
            return min(max_score, round(max_score * 0.8) + bonus), "positive"
        if positive_hits and negative_hits:
            return round(max_score * 0.6), "neutral"
        if evidence_strength >= 3:
            return round(max_score * 0.65), "neutral"
        return round(max_score * 0.55), "neutral"

    @staticmethod
    def _build_reason(
        *,
        spec: dict[str, Any],
        polarity: str,
        positive_hits: int,
        negative_hits: int,
        uncertainty: bool,
    ) -> str:
        if uncertainty:
            return f"{spec['label']}缺少直接支撑，只能保守判断。"
        if polarity == "positive":
            return f"{spec['label']}出现了更明确的正向支撑，当前加分主要来自公开材料中的改善信号。"
        if polarity == "negative":
            return f"{spec['label']}的扣分来自更强的承压证据，负向信号数量高于改善信号。"
        if positive_hits or negative_hits:
            return f"{spec['label']}同时存在改善与承压信息，因此按中性偏保守口径处理。"
        return f"{spec['label']}已有基础证据，但结论仍需后续数据继续验证。"

    @staticmethod
    def _build_subitem_summary(*, spec: dict[str, Any], polarity: str, score: int, max_score: int) -> str:
        if polarity == "positive":
            return f"{spec['label']}当前偏稳，得分 {score}/{max_score}。"
        if polarity == "negative":
            return f"{spec['label']}当前承压，得分 {score}/{max_score}。"
        return f"{spec['label']}当前处于观察区间，得分 {score}/{max_score}。"

    def _build_summary(self, *, total_score: int, positive_factors: list[str], negative_factors: list[str]) -> str:
        positives = positive_factors[:1]
        negatives = negative_factors[:1]
        if negatives:
            return f"{self.dimension_label}得分 {total_score}/{self.max_score}。当前最主要的拖累来自：{negatives[0]}"
        if positives:
            return f"{self.dimension_label}得分 {total_score}/{self.max_score}。当前最主要的支撑来自：{positives[0]}"
        return f"{self.dimension_label}得分 {total_score}/{self.max_score}。当前证据能够形成基础判断，但仍需继续补强。"

    @staticmethod
    def _confidence(sub_scores: list[dict[str, Any]]) -> float:
        if not sub_scores:
            return 0.3
        evidence_backed = sum(1 for item in sub_scores if item["evidence_refs"])
        return round(min(0.92, 0.42 + evidence_backed * 0.14), 2)


class BusinessQualityScoreSkill(ScoreDimensionSkill):
    skill_name = "BusinessQualityScoreSkill"
    description = "按规则评估经营质量，拆解收入增长质量、核心业务支撑度和经营稳定性。"
    trigger_condition = "分析结果汇总后执行。"
    dimension_key = "business_quality"
    dimension_label = "经营质量"
    max_score = 30
    subitems = [
        {
            "key": "revenue_growth_quality",
            "label": "收入增长质量",
            "max_score": 10,
            "keywords": ("收入", "营收", "增长", "恢复", "主营业务"),
            "follow_up": "收入同比、主营业务增速",
        },
        {
            "key": "core_business_support",
            "label": "核心产品/业务支撑度",
            "max_score": 10,
            "keywords": ("产品", "新品", "业务线", "版号", "流水", "用户"),
            "follow_up": "核心产品流水、新品上线节奏",
        },
        {
            "key": "operating_stability",
            "label": "经营稳定性",
            "max_score": 10,
            "keywords": ("费用", "组织调整", "波动", "稳定", "修复"),
            "follow_up": "费用率、组织调整、经营波动",
        },
    ]


class EarningsQualityScoreSkill(ScoreDimensionSkill):
    skill_name = "EarningsQualityScoreSkill"
    description = "按规则评估盈利质量，拆解利润兑现度、利润结构健康度和利润持续性。"
    trigger_condition = "分析结果汇总后执行。"
    dimension_key = "earnings_quality"
    dimension_label = "盈利质量"
    max_score = 25
    subitems = [
        {
            "key": "profit_realization",
            "label": "利润兑现度",
            "max_score": 10,
            "keywords": ("净利润", "扣非", "利润", "毛利率", "净利率"),
            "follow_up": "净利润、扣非净利润、毛利率",
        },
        {
            "key": "profit_structure",
            "label": "利润结构健康度",
            "max_score": 8,
            "keywords": ("非经常性", "减值", "投资收益", "主营利润", "费用率"),
            "follow_up": "非经常性损益、投资收益、费用率",
        },
        {
            "key": "profit_sustainability",
            "label": "利润持续性",
            "max_score": 7,
            "keywords": ("持续", "修复", "新品", "投放", "后续"),
            "follow_up": "后续产品表现、利润持续性",
        },
    ]


class CashflowHealthScoreSkill(ScoreDimensionSkill):
    skill_name = "CashflowHealthScoreSkill"
    description = "按规则评估现金流健康度，拆解现金流匹配度、波动风险和财务安全边际。"
    trigger_condition = "分析结果汇总后执行。"
    dimension_key = "cashflow_health"
    dimension_label = "现金流健康度"
    max_score = 25
    subitems = [
        {
            "key": "cashflow_match",
            "label": "经营现金流匹配度",
            "max_score": 10,
            "keywords": ("经营现金流", "现金流", "回款", "利润", "转化"),
            "follow_up": "经营现金流净额、回款能力",
        },
        {
            "key": "cashflow_volatility",
            "label": "现金流波动风险",
            "max_score": 8,
            "keywords": ("投资活动现金流", "筹资活动现金流", "波动", "资金消耗"),
            "follow_up": "投资/筹资现金流波动",
        },
        {
            "key": "financial_safety",
            "label": "财务安全边际",
            "max_score": 7,
            "keywords": ("货币资金", "负债", "偿债", "融资", "资金"),
            "follow_up": "货币资金、短期债务、融资依赖",
        },
    ]


class IndustryEnvironmentScoreSkill(ScoreDimensionSkill):
    skill_name = "IndustryEnvironmentScoreSkill"
    description = "按规则评估行业与外部环境适配度，拆解需求环境、竞争格局和外部催化/约束。"
    trigger_condition = "分析结果汇总后执行。"
    dimension_key = "industry_environment"
    dimension_label = "行业与外部环境适配度"
    max_score = 20
    subitems = [
        {
            "key": "demand_environment",
            "label": "行业景气与需求环境",
            "max_score": 7,
            "keywords": ("行业", "需求", "景气", "恢复", "市场空间"),
            "follow_up": "行业景气度、需求恢复节奏",
        },
        {
            "key": "competition_environment",
            "label": "竞争与产品环境",
            "max_score": 7,
            "keywords": ("竞争", "新品", "替代", "渠道", "产品"),
            "follow_up": "竞争格局、产品承接能力",
        },
        {
            "key": "external_catalyst_constraint",
            "label": "外部催化与约束",
            "max_score": 6,
            "keywords": ("政策", "技术", "海外", "监管", "版号"),
            "follow_up": "政策变化、技术趋势、外部监管",
        },
    ]
