from __future__ import annotations

import json
import re
from typing import Any

from services.db import Database
from skills.evidence_ranking import classify_evidence_type, evidence_priority_level


class RetrievalService:
    ASPECT_EXPANSIONS: dict[str, list[str]] = {
        "overview": ["公司概况 管理层讨论 风险因素 主营业务", "年报 摘要 核心业务 经营概览"],
        "financial_health": ["营收 利润 毛利 现金流 负债", "经营表现 成本 费用 回款 偿债"],
        "governance_compliance": ["治理 合规 诉讼 内控 监管", "处罚 审计 关联交易 资质 风险"],
        "product_pipeline": ["新品 储备 测试 公测 上线", "产品线 进展 发行 节奏"],
        "operation_performance": ["流水 活跃 留存 运营 老产品 生命周期", "业绩 改善 承压 增长 下滑"],
        "regulation_publishing": ["版号 审批 发行 合规 政策", "上线 节奏 监管 许可"],
        "industry_trend": ["AI 智能体 技术趋势 行业景气度", "GDC OpenAI agent 行业变化"],
        "marketing_efficiency": ["买量 营销 投放 销售费用 获客", "广告 宣发 ROI 推广"],
        "overseas_market": ["海外 出海 境外 国际 区域市场", "海外发行 港澳台 国际化"],
        "ip_dependency": ["IP 授权 续作 内容供给 研发团队", "联动 世界观 储备 精品化"],
    }

    REPORT_TYPE_PRIOR: dict[str, tuple[str, ...]] = {
        "overview": ("annual_report", "research_report", "industry_report"),
        "financial_health": ("annual_report", "research_report"),
        "governance_compliance": ("annual_report",),
        "product_pipeline": ("annual_report", "research_report"),
        "operation_performance": ("annual_report", "research_report"),
        "regulation_publishing": ("research_report", "annual_report"),
        "industry_trend": ("research_report", "industry_report"),
        "marketing_efficiency": ("research_report", "annual_report"),
        "overseas_market": ("annual_report", "research_report"),
        "ip_dependency": ("annual_report", "research_report"),
    }

    STOPWORDS = {"请", "基于", "生成", "企业", "体检", "报告", "分析", "结合", "覆盖", "证据", "公司"}

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    def search(self, query: str, company_code: str | None = None, top_k: int = 8, aspect: str | None = None) -> list[dict[str, Any]]:
        evidence_pack = self.build_evidence_pack(query=query, company_code=company_code, top_k=top_k, aspect=aspect)
        return evidence_pack["items"]

    def build_evidence_pack(
        self,
        query: str,
        company_code: str | None = None,
        top_k: int = 8,
        aspect: str | None = None,
    ) -> dict[str, Any]:
        query_variants = self._expand_query(query=query, aspect=aspect)
        query_terms = self._extract_terms(query)
        candidates: dict[tuple[str, int, str], dict[str, Any]] = {}

        for variant in query_variants:
            terms = self._extract_terms(variant)
            if not terms:
                continue
            for row in self._fetch_candidates(terms=terms, company_code=company_code, limit=max(top_k * 6, 18)):
                key = (row["source"], int(row["page_no"]), row["chunk_text"])
                ranked = self._decorate_candidate(row=row, query_terms=query_terms, aspect=aspect, query_variants=query_variants)
                existing = candidates.get(key)
                if not existing or ranked["relevance_score"] > existing["relevance_score"]:
                    candidates[key] = ranked

        ranked_items = list(candidates.values())
        if not ranked_items:
            ranked_items = [
                self._decorate_candidate(row=row, query_terms=query_terms, aspect=aspect, query_variants=query_variants)
                for row in self.latest_company_evidence(company_code=company_code, top_k=max(top_k, 6))
            ]

        ranked_items.sort(
            key=lambda item: (
                item.get("relevance_score", 0),
                item.get("report_type_priority", 0),
                -int(item.get("page_no") or 0),
                item.get("char_count", 0),
            ),
            reverse=True,
        )
        selected = self._select_diverse(ranked_items, top_k)
        return {
            "query": query,
            "aspect": aspect or "general",
            "query_variants": query_variants,
            "items": selected,
            "coverage_summary": self._coverage_summary(selected),
        }

    def latest_company_evidence(self, company_code: str | None = None, top_k: int = 8) -> list[dict[str, Any]]:
        sql = """
        SELECT
            doc_id,
            company_code,
            report_type,
            page_no,
            chunk_text,
            source,
            COALESCE(chunk_index, 0) AS chunk_index,
            COALESCE(section_title, '') AS section_title,
            COALESCE(section_path, '') AS section_path,
            COALESCE(metadata_json, '{}') AS metadata_json,
            COALESCE(char_count, LENGTH(chunk_text)) AS char_count
        FROM evidence_chunk
        WHERE 1=1
        """
        params: list[Any] = []
        if company_code:
            sql += " AND company_code = ?"
            params.append(company_code)
        sql += " ORDER BY page_no DESC, id DESC LIMIT ?"
        params.append(top_k)
        rows = self.db.fetchall(sql, params)
        return [self._normalize_row(dict(row)) for row in rows]

    def vector_search(self, query: str, company_code: str | None = None, top_k: int = 8) -> list[dict[str, Any]]:
        return self.search(query=query, company_code=company_code, top_k=top_k)

    def _fetch_candidates(self, terms: list[str], company_code: str | None, limit: int) -> list[dict[str, Any]]:
        if not terms:
            return []
        like_group = " OR ".join("(chunk_text LIKE ? OR section_title LIKE ? OR section_path LIKE ?)" for _ in terms)
        sql = f"""
        SELECT
            doc_id,
            company_code,
            report_type,
            page_no,
            chunk_text,
            source,
            COALESCE(chunk_index, 0) AS chunk_index,
            COALESCE(section_title, '') AS section_title,
            COALESCE(section_path, '') AS section_path,
            COALESCE(metadata_json, '{{}}') AS metadata_json,
            COALESCE(char_count, LENGTH(chunk_text)) AS char_count
        FROM evidence_chunk
        WHERE ({like_group})
        """
        params: list[Any] = []
        for term in terms:
            like = f"%{term}%"
            params.extend([like, like, like])
        if company_code:
            sql += " AND company_code = ?"
            params.append(company_code)
        sql += " ORDER BY page_no ASC, id ASC LIMIT ?"
        params.append(limit)
        rows = self.db.fetchall(sql, params)
        return [self._normalize_row(dict(row)) for row in rows]

    def _decorate_candidate(
        self,
        row: dict[str, Any],
        query_terms: list[str],
        aspect: str | None,
        query_variants: list[str],
    ) -> dict[str, Any]:
        metadata = self._load_metadata(row.get("metadata_json"))
        haystack = " ".join(
            part
            for part in (
                row.get("chunk_text", ""),
                row.get("section_title", ""),
                row.get("section_path", ""),
                row.get("source", ""),
            )
            if part
        )
        lowered = haystack.lower()
        aspect_terms = self._extract_terms(" ".join(self.ASPECT_EXPANSIONS.get(aspect or "", [])))
        term_matches = sum(1 for term in query_terms if term.lower() in lowered)
        aspect_matches = sum(1 for term in aspect_terms if term.lower() in lowered)
        variant_matches = max(
            (
                sum(1 for term in self._extract_terms(variant) if term.lower() in lowered)
                for variant in query_variants
            ),
            default=0,
        )
        section_bonus = 2 if row.get("section_path") or row.get("section_title") else 0
        report_type_priority = self._report_type_priority(aspect=aspect, report_type=row.get("report_type", ""))
        year_bonus = 1 if str(metadata.get("year", "")).startswith("20") else 0
        score = term_matches * 10 + aspect_matches * 5 + variant_matches * 2 + section_bonus + report_type_priority + year_bonus

        matched_terms = [term for term in query_terms if term.lower() in lowered][:4]
        reason_parts = []
        if matched_terms:
            reason_parts.append(f"命中关键词：{', '.join(matched_terms)}")
        if row.get("section_path"):
            reason_parts.append(f"章节：{row['section_path']}")
        if row.get("report_type"):
            reason_parts.append(f"材料类型：{row['report_type']}")
        reason = "；".join(reason_parts) or "基于相近主题召回"

        row.update(
            {
                "metadata": metadata,
                "relevance_score": round(float(score), 2),
                "reason": reason,
                "quote": self._build_quote(row.get("chunk_text", ""), query_terms),
                "report_type_priority": report_type_priority,
                "evidence_type": classify_evidence_type(row),
                "priority_level": evidence_priority_level(row),
            }
        )
        return row

    def _select_diverse(self, items: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        per_page: dict[tuple[str, int], int] = {}
        seen_quotes: set[str] = set()

        for item in items:
            page_key = (item.get("source", ""), int(item.get("page_no") or 0))
            compact = self._compact(item.get("quote") or item.get("chunk_text", ""))
            if per_page.get(page_key, 0) >= 2:
                continue
            if compact and compact in seen_quotes:
                continue
            selected.append(item)
            per_page[page_key] = per_page.get(page_key, 0) + 1
            if compact:
                seen_quotes.add(compact)
            if len(selected) >= top_k:
                break

        if len(selected) < top_k:
            for item in items:
                if item in selected:
                    continue
                selected.append(item)
                if len(selected) >= top_k:
                    break
        return selected

    def _coverage_summary(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return "未检索到高相关证据。"
        sources = list(dict.fromkeys(item.get("source", "") for item in items if item.get("source")))
        sections = [
            item.get("section_path") or item.get("section_title")
            for item in items
            if item.get("section_path") or item.get("section_title")
        ]
        section_text = f"，涉及 {len(list(dict.fromkeys(sections)))} 个章节" if sections else ""
        return f"已整理 {len(items)} 条高相关证据，覆盖 {len(sources)} 份材料{section_text}。"

    def _expand_query(self, query: str, aspect: str | None) -> list[str]:
        variants = [query.strip()] if query.strip() else []
        if aspect and aspect in self.ASPECT_EXPANSIONS:
            variants.extend(f"{query} {addition}".strip() for addition in self.ASPECT_EXPANSIONS[aspect])
        if "风险" not in query:
            variants.append(f"{query} 风险 证据 页码".strip())
        return list(dict.fromkeys(item for item in variants if item))[:4]

    def _report_type_priority(self, aspect: str | None, report_type: str) -> int:
        if not aspect:
            return 0
        priorities = self.REPORT_TYPE_PRIOR.get(aspect, ())
        for offset, candidate in enumerate(priorities[::-1], start=1):
            if report_type == candidate:
                return offset * 2
        return 0

    def _normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        row["chunk_text"] = row.get("chunk_text", "") or ""
        row["section_title"] = row.get("section_title", "") or ""
        row["section_path"] = row.get("section_path", "") or ""
        row["char_count"] = int(row.get("char_count") or len(row["chunk_text"]))
        return row

    @staticmethod
    def _load_metadata(raw_value: Any) -> dict[str, Any]:
        if isinstance(raw_value, dict):
            return raw_value
        if not raw_value:
            return {}
        try:
            decoded = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @classmethod
    def _extract_terms(cls, query: str) -> list[str]:
        raw_terms = re.findall(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", query)
        terms: list[str] = []
        for term in raw_terms:
            if term in cls.STOPWORDS:
                continue
            if term not in terms:
                terms.append(term)
        return terms[:8]

    @staticmethod
    def _build_quote(text: str, terms: list[str], max_length: int = 120) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            return ""
        for term in terms:
            index = normalized.lower().find(term.lower())
            if index >= 0:
                start = max(0, index - 24)
                end = min(len(normalized), index + max_length - 24)
                snippet = normalized[start:end]
                return f"...{snippet}..." if start > 0 or end < len(normalized) else snippet
        return normalized[:max_length]

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", "", text or "")[:120]
