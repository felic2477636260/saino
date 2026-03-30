from __future__ import annotations

from typing import Any

from models.schemas import PreferenceProfile
from skills.base import BaseSkill
from skills.registry import SkillRegistry


BASE_ASPECTS = ("overview", "financial_health", "governance_compliance")
GAME_STANDARD_ASPECTS = ("product_pipeline", "operation_performance", "industry_trend")

TOPIC_TO_ASPECTS: dict[str, tuple[str, ...]] = {
    "finance": ("earnings_quality", "cashflow_health"),
    "cashflow": ("cashflow_health",),
    "risk": ("industry_competition", "governance_compliance"),
    "growth": ("growth_continuity", "product_business_structure"),
    "product": ("product_lifecycle", "product_business_structure"),
    "competition": ("industry_competition",),
    "management": ("management_execution",),
    "overseas": ("overseas_business", "overseas_market"),
    "marketing": ("marketing_efficiency",),
    "industry": ("industry_competition", "industry_trend"),
}

SUPPRESSED_TO_ASPECTS: dict[str, tuple[str, ...]] = {
    "macro": ("industry_trend", "industry_competition"),
    "industry": ("industry_trend", "industry_competition"),
    "governance": ("governance_compliance",),
    "marketing": ("marketing_efficiency",),
}


class SkillRouter:
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def build_route(
        self,
        *,
        context: dict[str, Any],
        industry: str,
        preference_profile: PreferenceProfile,
    ) -> dict[str, Any]:
        aspects: list[str] = []
        route_reasons: list[dict[str, str]] = []
        document_signals = self._detect_document_signals(context)
        suppressed_aspects = self._suppressed_aspects(preference_profile)

        for aspect in BASE_ASPECTS:
            self._push_aspect(aspects, route_reasons, aspect, "基础主干能力默认开启")

        normalized_industry = (industry or preference_profile.domain_hint or "generic").strip().lower()
        if normalized_industry == "game" or "game" in document_signals:
            for aspect in GAME_STANDARD_ASPECTS:
                self._push_aspect(aspects, route_reasons, aspect, "游戏行业标准增强分析")

        focus_aspects = self._focus_aspects(preference_profile.focus_priority, normalized_industry)
        for aspect in focus_aspects:
            self._push_aspect(aspects, route_reasons, aspect, f"围绕 {preference_profile.focus_priority} 调整分析重心")

        for topic in preference_profile.preferred_topics:
            for aspect in TOPIC_TO_ASPECTS.get(topic, ()):
                self._push_aspect(aspects, route_reasons, aspect, f"响应用户关注主题：{topic}")

        for signal in document_signals:
            for aspect in TOPIC_TO_ASPECTS.get(signal, ()):
                self._push_aspect(aspects, route_reasons, aspect, f"材料中识别到相关业务信号：{signal}")

        aspects = [aspect for aspect in aspects if aspect not in suppressed_aspects]
        aspect_skill_map: dict[str, list[str]] = {}
        dropped_aspects: list[str] = []

        for aspect in aspects:
            candidates = self._skills_for_aspect(aspect=aspect)
            if not candidates:
                dropped_aspects.append(aspect)
                continue
            aspect_skill_map[aspect] = candidates

        enabled_skill_ids = sorted({skill_id for skill_ids in aspect_skill_map.values() for skill_id in skill_ids})
        return {
            "analysis_aspects": [aspect for aspect in aspects if aspect in aspect_skill_map],
            "aspect_skill_map": aspect_skill_map,
            "enabled_skill_ids": enabled_skill_ids,
            "suppressed_aspects": sorted(suppressed_aspects),
            "document_signals": sorted(document_signals),
            "route_reasons": route_reasons,
            "dropped_aspects": dropped_aspects,
        }

    def _skills_for_aspect(self, *, aspect: str) -> list[str]:
        matches: list[BaseSkill] = []
        for skill in self.registry.all():
            if skill.skill_category != "analysis":
                continue
            if skill.target_aspects and aspect not in skill.target_aspects:
                continue
            matches.append(skill)
        matches.sort(key=lambda item: (getattr(item, "priority", 50), item.skill_name), reverse=True)
        return [skill.id for skill in matches]

    def _detect_document_signals(self, context: dict[str, Any]) -> set[str]:
        text_chunks: list[str] = [str(context.get("query", "")), str(context.get("user_query", ""))]
        profile = context.get("preference_profile") or {}
        text_chunks.append(str(profile.get("user_intent_raw", "")))
        evidence_pack = context.get("evidence_pack") or {}
        for item in evidence_pack.get("items") or []:
            text_chunks.append(
                " ".join(
                    [
                        str(item.get("chunk_text", "")),
                        str(item.get("section_title", "")),
                        str(item.get("section_path", "")),
                    ]
                )
            )
        text = " ".join(text_chunks).lower()
        signals: set[str] = set()

        if any(token in text for token in ("游戏", "版号", "流水", "买量", "公测")):
            signals.add("game")
        if any(token in text for token in ("现金流", "偿债", "回款", "融资", "债务")):
            signals.add("cashflow")
        if any(token in text for token in ("利润", "扣非", "毛利率", "费用率", "盈利")):
            signals.add("finance")
        if any(token in text for token in ("产品", "新品", "生命周期", "产品线", "业务结构")):
            signals.add("product")
        if any(token in text for token in ("增长", "成长", "承接", "修复")):
            signals.add("growth")
        if any(token in text for token in ("竞争", "份额", "格局", "替代")):
            signals.add("competition")
        if any(token in text for token in ("管理层", "组织", "执行", "战略")):
            signals.add("management")
        if any(token in text for token in ("海外", "出海", "国际", "区域")):
            signals.add("overseas")
        if any(token in text for token in ("营销", "投放", "买量", "获客", "roi")):
            signals.add("marketing")
        if any(token in text for token in ("行业", "景气", "政策", "监管")):
            signals.add("industry")
        return signals

    @staticmethod
    def _focus_aspects(focus_priority: str, industry: str) -> tuple[str, ...]:
        if focus_priority == "finance_first":
            return ("earnings_quality", "cashflow_health")
        if focus_priority == "risk_first":
            return ("cashflow_health", "industry_competition") if industry != "game" else ("cashflow_health", "regulation_publishing")
        if focus_priority == "growth_first":
            return ("growth_continuity", "product_business_structure") if industry != "game" else ("product_lifecycle", "product_pipeline")
        return ()

    @staticmethod
    def _suppressed_aspects(profile: PreferenceProfile) -> set[str]:
        suppressed: set[str] = set()
        for topic in profile.suppressed_topics:
            suppressed.update(SUPPRESSED_TO_ASPECTS.get(topic, ()))
        return suppressed

    @staticmethod
    def _push_aspect(aspects: list[str], reasons: list[dict[str, str]], aspect: str, reason: str) -> None:
        if aspect in aspects:
            return
        aspects.append(aspect)
        reasons.append({"aspect": aspect, "reason": reason})
