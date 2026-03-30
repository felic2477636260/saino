from __future__ import annotations

import re
from typing import Any, Iterable


QUANTITATIVE_KEYWORDS = (
    "收入",
    "营收",
    "利润",
    "净利",
    "毛利",
    "毛利率",
    "净利率",
    "现金流",
    "同比",
    "环比",
    "费用率",
    "应收",
    "存货",
    "资产负债",
    "付费率",
    "留存率",
    "流水",
    "%",
)

OPERATING_FACT_KEYWORDS = (
    "上线",
    "发布",
    "获批",
    "版号",
    "新品",
    "海外",
    "出海",
    "组织调整",
    "扩张",
    "收缩",
    "产品",
    "用户",
    "运营",
    "策略",
    "技术应用",
)

MANAGEMENT_KEYWORDS = (
    "董事会",
    "管理层",
    "表示",
    "认为",
    "展望",
    "计划",
    "预计",
    "将",
)

CONTEXT_KEYWORDS = (
    "审计",
    "政策",
    "行业",
    "市场环境",
    "宏观",
    "风险提示",
)


def evidence_identity(item: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(item.get("source", "")),
        int(item.get("page_no") or 0),
        compact_text(item.get("chunk_text") or item.get("text") or ""),
    )


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")[:240]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def evidence_text(item: dict[str, Any]) -> str:
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


def evidence_quote(item: dict[str, Any], max_length: int = 120) -> str:
    text = normalize_text(item.get("quote") or item.get("chunk_text") or item.get("text") or "")
    return text[:max_length]


def evidence_citation(item: dict[str, Any]) -> str:
    source = item.get("source", "未标注来源")
    page_no = int(item.get("page_no") or 0)
    return f"{source} P{page_no}" if page_no else source


def classify_evidence_type(item: dict[str, Any]) -> str:
    text = evidence_text(item)
    lowered = text.lower()
    if _contains_metric(text) or any(keyword in text for keyword in QUANTITATIVE_KEYWORDS):
        return "quantitative"
    if any(keyword.lower() in lowered for keyword in OPERATING_FACT_KEYWORDS):
        return "operating_fact"
    if any(keyword.lower() in lowered for keyword in MANAGEMENT_KEYWORDS):
        return "management_statement"
    if any(keyword.lower() in lowered for keyword in CONTEXT_KEYWORDS):
        return "context"
    return "context"


def evidence_priority_level(item: dict[str, Any]) -> int:
    return {
        "quantitative": 4,
        "operating_fact": 3,
        "management_statement": 2,
        "context": 1,
    }[classify_evidence_type(item)]


def dedupe_evidence(items: Iterable[dict[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for item in items:
        key = evidence_identity(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(item))
        if limit is not None and len(deduped) >= limit:
            break
    return deduped


def select_ranked_evidence(
    items: Iterable[dict[str, Any]],
    *,
    keywords: Iterable[str] = (),
    limit: int = 2,
) -> list[dict[str, Any]]:
    keyword_list = [keyword.strip().lower() for keyword in keywords if keyword and keyword.strip()]
    ranked = sorted(
        dedupe_evidence(items),
        key=lambda item: _rank_sort_key(item, keyword_list),
        reverse=True,
    )
    ranked = _prefer_priority_bands(ranked, limit=limit)
    return ranked[:limit]


def to_evidence_ref(item: dict[str, Any]) -> dict[str, Any]:
    text = item.get("chunk_text") or item.get("text") or ""
    return {
        "source": item.get("source", ""),
        "page_no": int(item.get("page_no") or 0),
        "text": text,
        "section_title": item.get("section_title", ""),
        "section_path": item.get("section_path", ""),
        "relevance_score": float(item.get("relevance_score") or 0),
        "reason": item.get("reason", ""),
        "quote": evidence_quote(item, max_length=200),
        "evidence_type": classify_evidence_type(item),
        "priority_level": evidence_priority_level(item),
    }


def summarize_evidence(item: dict[str, Any], max_length: int = 88) -> str:
    quote = evidence_quote(item, max_length=max_length)
    return quote or evidence_citation(item)


def _rank_sort_key(item: dict[str, Any], keywords: list[str]) -> tuple[int, int, int, float, int, int]:
    text = evidence_text(item).lower()
    keyword_hits = sum(1 for keyword in keywords if keyword in text)
    explicit_metric_bonus = 2 if _contains_metric(text) else 0
    return (
        evidence_priority_level(item),
        keyword_hits + explicit_metric_bonus,
        _metric_signal_count(text),
        float(item.get("relevance_score") or 0),
        int(item.get("page_no") or 0),
        len(compact_text(item.get("chunk_text") or item.get("text") or "")),
    )


def _contains_metric(text: str) -> bool:
    return bool(re.search(r"\d", text or "")) and any(token in (text or "") for token in ("%","亿元","万元","同比","环比"))


def _metric_signal_count(text: str) -> int:
    metric_tokens = ("%", "同比", "环比", "亿元", "万元", "收入", "营收", "利润", "净利", "毛利", "现金流", "费用率", "流水")
    return sum(1 for token in metric_tokens if token in (text or ""))


def _prefer_priority_bands(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    if not items:
        return items

    strong_items = [item for item in items if evidence_priority_level(item) >= 3]
    if len(strong_items) >= limit:
        return strong_items
    if strong_items:
        medium_items = [item for item in items if evidence_priority_level(item) == 2]
        context_items = [item for item in items if evidence_priority_level(item) == 1]
        return strong_items + medium_items + context_items
    return items
