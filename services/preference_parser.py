from __future__ import annotations

import json
import logging
import re
from typing import Any

from config.prompt_templates import USER_PREFERENCE_PARSE_PROMPT
from models.schemas import PreferenceProfile
from services.llm_client import LLMClient


logger = logging.getLogger(__name__)


TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "finance": ("财务", "盈利", "利润", "利润率", "偿债", "负债", "资产负债", "财务质量"),
    "cashflow": ("现金流", "回款", "现金转换", "资金", "流动性"),
    "risk": ("风险", "保守", "下行", "脆弱", "压力", "风险控制"),
    "growth": ("增长", "成长", "扩张", "增量", "持续性", "成长性"),
    "product": ("产品", "产品线", "生命周期", "新品", "老产品", "pipeline"),
    "competition": ("竞争", "格局", "份额", "护城河", "替代"),
    "management": ("管理层", "执行力", "组织", "治理", "管理诊断"),
    "overseas": ("出海", "海外", "国际", "区域", "境外"),
    "marketing": ("买量", "营销", "投放", "获客", "roi"),
    "industry": ("行业", "景气", "政策", "监管", "版号"),
    "score": ("评分", "打分", "总分", "维度分"),
    "summary": ("结论", "摘要", "先给结论", "先看结论"),
    "evidence": ("证据", "出处", "页码", "可追溯", "强证据"),
}

SUPPRESSION_PATTERNS: dict[str, tuple[str, ...]] = {
    "macro": ("少讲宏观", "不要宏观", "弱化宏观"),
    "governance": ("少讲治理", "不要治理", "弱化治理"),
    "industry": ("少讲行业", "不要行业背景"),
    "marketing": ("少讲营销", "不要投放细节"),
}

DOMAIN_PATTERNS: dict[str, tuple[str, ...]] = {
    "game": ("游戏", "版号", "流水", "买量", "出海", "新品上线"),
    "consumer": ("消费", "品牌", "渠道", "门店"),
    "manufacturing": ("制造", "产能", "订单", "设备"),
    "software": ("软件", "saas", "订阅", "云"),
}


class PreferenceParser:
    def parse(
        self,
        *,
        preference_note: str,
        query: str,
        llm_client: LLMClient | None = None,
    ) -> PreferenceProfile:
        raw = (preference_note or "").strip()
        if not raw:
            return PreferenceProfile(user_intent_raw="", confidence=0.0)

        heuristic_profile = self._heuristic_parse(preference_note=raw, query=query)
        if not llm_client or not llm_client.is_ready:
            return heuristic_profile

        try:
            prompt = USER_PREFERENCE_PARSE_PROMPT.format(query=query.strip(), preference_note=raw)
            payload = llm_client.generate_json(prompt)
            merged = self._merge_profiles(primary=payload, fallback=heuristic_profile.model_dump())
            return PreferenceProfile.model_validate(merged)
        except Exception as exc:
            logger.warning("preference parsing fell back to heuristic mode: %s", exc)
            return heuristic_profile

    def _heuristic_parse(self, *, preference_note: str, query: str) -> PreferenceProfile:
        raw = preference_note.strip()
        combined = f"{query} {raw}".strip()

        report_style = "standard"
        if any(token in raw for token in ("简洁", "简短", "浓缩", "直接一点")):
            report_style = "concise"
        elif any(token in raw for token in ("详细", "深度", "展开", "深入", "尽量全面")):
            report_style = "deep"

        summary_first = bool(re.search(r"(先给.*结论|先给.*评分|先看.*结论|先看.*评分|结论先行|摘要先行)", raw))

        tone_preference = "readable_briefing"
        if any(token in raw for token in ("投资研究", "研究风格", "研报风格", "投资视角")):
            tone_preference = "investment_research"
        elif any(token in raw for token in ("管理诊断", "管理视角", "经营诊断", "组织执行")):
            tone_preference = "management_diagnosis"

        evidence_strictness = "standard"
        if any(token in raw for token in ("强证据", "证据严格", "证据优先", "保守判断", "宁缺毋滥", "页码")):
            evidence_strictness = "strict"
        elif any(token in raw for token in ("大胆一点", "可适度推断", "允许展开")):
            evidence_strictness = "flexible"

        preferred_topics = self._collect_topics(combined)
        suppressed_topics = self._collect_suppressed_topics(raw)
        preferred_output_emphasis = self._collect_output_emphasis(raw)
        domain_hint = self._detect_domain(combined)
        focus_priority = self._focus_priority(raw)
        confidence = self._estimate_confidence(raw=raw, topics=preferred_topics)

        return PreferenceProfile(
            report_style=report_style,
            focus_priority=focus_priority,
            preferred_topics=preferred_topics,
            suppressed_topics=suppressed_topics,
            tone_preference=tone_preference,
            summary_first=summary_first or report_style == "concise",
            evidence_strictness=evidence_strictness,
            preferred_output_emphasis=preferred_output_emphasis,
            domain_hint=domain_hint,
            user_intent_raw=raw,
            confidence=confidence,
        )

    @staticmethod
    def _merge_profiles(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        merged = dict(fallback)
        merged.update({key: value for key, value in primary.items() if value not in (None, "", [])})
        for key in ("preferred_topics", "suppressed_topics", "preferred_output_emphasis"):
            primary_items = primary.get(key)
            if isinstance(primary_items, list) and primary_items:
                merged[key] = PreferenceParser._dedupe_strings(primary_items)
            else:
                merged[key] = PreferenceParser._dedupe_strings(fallback.get(key, []))
        merged["user_intent_raw"] = str(primary.get("user_intent_raw") or fallback.get("user_intent_raw") or "").strip()
        merged["confidence"] = PreferenceParser._normalize_confidence(primary.get("confidence", fallback.get("confidence", 0.0)))
        return merged

    @staticmethod
    def _collect_topics(text: str) -> list[str]:
        topics: list[str] = []
        lowered = text.lower()
        for topic, keywords in TOPIC_PATTERNS.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                topics.append(topic)
        return PreferenceParser._dedupe_strings(topics)

    @staticmethod
    def _collect_suppressed_topics(text: str) -> list[str]:
        suppressed: list[str] = []
        for topic, keywords in SUPPRESSION_PATTERNS.items():
            if any(keyword in text for keyword in keywords):
                suppressed.append(topic)
        return PreferenceParser._dedupe_strings(suppressed)

    @staticmethod
    def _collect_output_emphasis(text: str) -> list[str]:
        emphasis: list[str] = []
        if re.search(r"(先给.*结论|先看.*结论|摘要先行)", text):
            emphasis.append("summary")
        if re.search(r"(先给.*评分|先看.*评分|评分优先)", text):
            emphasis.append("score")
        if "风险" in text:
            emphasis.append("risk")
        if any(token in text for token in ("财务", "盈利", "现金流", "偿债")):
            emphasis.append("finance")
        if any(token in text for token in ("产品", "生命周期", "新品", "老产品")):
            emphasis.append("product")
        if any(token in text for token in ("证据", "出处", "页码", "可追溯")):
            emphasis.append("evidence")
        if any(token in text for token in ("建议", "动作", "下一步")):
            emphasis.append("actions")
        return PreferenceParser._dedupe_strings(emphasis)

    @staticmethod
    def _detect_domain(text: str) -> str:
        lowered = text.lower()
        for domain, keywords in DOMAIN_PATTERNS.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                return domain
        return ""

    @staticmethod
    def _focus_priority(text: str) -> str:
        scores = {
            "finance_first": 0,
            "risk_first": 0,
            "growth_first": 0,
            "balanced": 0.2,
        }
        finance_terms = ("财务", "盈利", "利润", "现金流", "偿债", "负债", "资产负债")
        risk_terms = ("风险", "保守", "下行", "先看风险", "谨慎", "拦截")
        growth_terms = ("增长", "成长", "产品", "生命周期", "新品", "出海", "竞争")
        scores["finance_first"] += sum(1 for term in finance_terms if term in text)
        scores["risk_first"] += sum(1 for term in risk_terms if term in text)
        scores["growth_first"] += sum(1 for term in growth_terms if term in text)
        return max(scores, key=scores.get)

    @staticmethod
    def _estimate_confidence(*, raw: str, topics: list[str]) -> float:
        if not raw:
            return 0.0
        signal_count = len(topics)
        if re.search(r"(先给|重点看|偏|更关心|更想看)", raw):
            signal_count += 1
        if len(raw) >= 16:
            signal_count += 1
        return PreferenceParser._normalize_confidence(min(0.92, 0.32 + signal_count * 0.14))

    @staticmethod
    def _dedupe_strings(items: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in items:
            value = re.sub(r"\s+", " ", str(item or "")).strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(value)
        return cleaned

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        try:
            return round(max(0.0, min(float(value), 1.0)), 2)
        except (TypeError, ValueError):
            return 0.0


def parse_preference_note(
    *,
    preference_note: str,
    query: str,
    llm_client: LLMClient | None = None,
) -> PreferenceProfile:
    return PreferenceParser().parse(preference_note=preference_note, query=query, llm_client=llm_client)
