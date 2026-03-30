from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from services.llm_client import LLMClient


PROCESS_PATTERNS = (
    "skill",
    "技能",
    "多阶段",
    "流程",
    "系统当前",
    "已激活",
    "证据条数",
    "命中",
    "模块",
    "协作生成",
    "研究过程",
    "调试信息",
)

FUTURE_TRACKING_PATTERNS = (
    "建议后续跟踪",
    "建议持续观察",
    "值得继续关注",
    "后续重点核实",
    "未来仍需",
    "可作为下一步研究重点",
)


@dataclass
class EvaluationMetric:
    name: str
    score: float
    notes: str


@dataclass
class EvaluationTemplate:
    user_value_focus: str = ""
    analysis_depth: str = ""
    evidence_support: str = ""
    decision_support: str = ""
    process_suppression: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def load_report(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    return {"summary": raw, "findings": [], "recommendations": [], "evidence": [], "report_sections": {}}


def evaluate_report(report: dict[str, Any]) -> list[EvaluationMetric]:
    payload = report.get("report_payload") or {}
    report_layer = payload.get("report_layer") or {}
    evidence_layer = payload.get("evidence_layer") or {}

    executive_summary = report_layer.get("executive_summary") or report.get("summary", "")
    key_judgments = report_layer.get("key_judgments") or report.get("findings", [])
    risk_groups = report_layer.get("risk_opportunities") or {}
    deep_sections = payload.get("sections") or report_layer.get("deep_sections") or []
    next_steps = report_layer.get("next_steps") or report.get("recommendations", [])
    key_evidence = evidence_layer.get("key_evidence") or report.get("evidence", [])
    verification_notes = evidence_layer.get("verification_focus") or report.get("verification_notes", [])

    section_evidence_count = sum(len(section.get("evidence", [])) for section in deep_sections)
    avg_section_paragraphs = (
        sum(len(section.get("body", [])) for section in deep_sections) / len(deep_sections) if deep_sections else 0
    )
    risks = risk_groups.get("risks") or []
    opportunities = risk_groups.get("opportunities") or []
    user_facing_text = _collect_user_facing_text(
        executive_summary=executive_summary,
        key_judgments=key_judgments,
        risks=risks,
        opportunities=opportunities,
        deep_sections=deep_sections,
        next_steps=next_steps,
        key_evidence=key_evidence,
        verification_notes=verification_notes,
    )
    process_mentions = _count_process_mentions(user_facing_text)
    future_tracking_mentions = _count_future_tracking_mentions(user_facing_text)
    repeated_ratio = _repetition_ratio(user_facing_text)

    metrics = [
        EvaluationMetric(
            name="user_value_focus",
            score=round(
                min(
                    100.0,
                    (20 if executive_summary else 0)
                    + (20 if key_judgments else 0)
                    + (16 if risks else 0)
                    + (16 if opportunities else 0)
                    + (14 if next_steps else 0)
                    + min(14, len(verification_notes) * 3),
                ),
                2,
            ),
            notes="是否先给出结论、风险机会、最终判断和少量待验证事项。",
        ),
        EvaluationMetric(
            name="analysis_depth",
            score=round(min(100.0, len(deep_sections) * 18 + avg_section_paragraphs * 12), 2),
            notes="深度分析正文越完整、每节解释越充分，得分越高。",
        ),
        EvaluationMetric(
            name="evidence_support",
            score=round(min(100.0, len(key_evidence) * 14 + section_evidence_count * 5), 2),
            notes="关键证据摘要与正文证据绑定越充分，得分越高。",
        ),
        EvaluationMetric(
            name="decision_support",
            score=round(
                min(
                    100.0,
                    len(next_steps) * 14
                    + (16 if key_judgments else 0)
                    + (14 if risks else 0)
                    + (14 if opportunities else 0)
                    + min(12, len(verification_notes) * 4),
                ),
                2,
            ),
            notes="是否帮助用户直接形成经营判断，而不是把主体内容推迟到后续跟踪。",
        ),
        EvaluationMetric(
            name="process_suppression",
            score=round(max(0.0, 100 - process_mentions * 12 - future_tracking_mentions * 10 - repeated_ratio * 40), 2),
            notes="用户可见文本越少出现流程化、机器化和泛化跟踪表述，得分越高。",
        ),
    ]
    return metrics


def compare_reports(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    candidate_metrics = {metric.name: metric for metric in evaluate_report(candidate)}
    baseline_metrics = {metric.name: metric for metric in evaluate_report(baseline)}
    delta = {
        name: round(candidate_metrics[name].score - baseline_metrics.get(name, EvaluationMetric(name, 0, "")).score, 2)
        for name in candidate_metrics
    }
    return {
        "candidate": {name: asdict(metric) for name, metric in candidate_metrics.items()},
        "baseline": {name: asdict(metric) for name, metric in baseline_metrics.items()},
        "delta": delta,
    }


def optional_llm_judge(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    llm_client: LLMClient | None = None,
) -> dict[str, Any]:
    client = llm_client or LLMClient()
    prompt = "\n".join(
        [
            "请比较两份企业调研报告，判断哪一份更像可直接交付给用户的研究报告，并说明原因。",
            "重点比较：",
            "1. 是否先给出可用结论，而不是流程说明。",
            "2. 是否解释了风险、机会和为什么这样判断。",
            "3. 是否把少量待验证事项控制在补充位置，而不是把正文写成后续计划。",
            "4. 是否避免技能数量、证据条数、模块流程以及“建议持续跟踪”等机器化表述。",
            "只能依据给定内容进行比较，不要补造事实。",
            f"候选摘要：{candidate.get('summary', '')}",
            f"候选核心发现：{'；'.join(candidate.get('findings', [])[:5])}",
            f"基线摘要：{baseline.get('summary', '')}",
            f"基线核心发现：{'；'.join(baseline.get('findings', [])[:5])}",
        ]
    )
    try:
        result = client.generate_report(prompt=prompt, evidence=candidate.get("evidence", [])[:6])
    except RuntimeError as exc:
        return {"status": "failed", "reason": str(exc)}
    return {"status": "completed", "result": result}


def _collect_user_facing_text(
    *,
    executive_summary: str,
    key_judgments: list[Any],
    risks: list[dict[str, Any]],
    opportunities: list[dict[str, Any]],
    deep_sections: list[dict[str, Any]],
    next_steps: list[str],
    key_evidence: list[Any],
    verification_notes: list[dict[str, Any]],
) -> list[str]:
    texts: list[str] = [executive_summary]
    for item in key_judgments:
        if isinstance(item, dict):
            texts.extend([item.get("title", ""), item.get("verdict", ""), item.get("explanation", "")])
        else:
            texts.append(str(item))
    for item in [*risks, *opportunities]:
        texts.extend([item.get("title", ""), item.get("summary", ""), item.get("impact", ""), item.get("follow_up", "")])
    for section in deep_sections:
        texts.append(section.get("title", ""))
        texts.append(section.get("summary", ""))
        texts.extend(section.get("body", []))
        texts.extend(section.get("pending_checks", []))
    for item in key_evidence:
        if isinstance(item, dict):
            texts.extend([item.get("title", ""), item.get("summary", ""), item.get("supports", "")])
        else:
            texts.append(str(item))
    texts.extend(next_steps)
    texts.extend(note.get("detail", "") for note in verification_notes)
    return [text for text in texts if text]


def _count_process_mentions(values: list[str]) -> int:
    joined = " ".join(values).lower()
    return sum(joined.count(pattern.lower()) for pattern in PROCESS_PATTERNS)


def _count_future_tracking_mentions(values: list[str]) -> int:
    joined = " ".join(values)
    return sum(joined.count(pattern) for pattern in FUTURE_TRACKING_PATTERNS)


def _repetition_ratio(values: list[str]) -> float:
    cleaned = [_normalize(value) for value in values if value and value.strip()]
    if not cleaned:
        return 0.0
    unique = len(set(cleaned))
    return 1 - (unique / len(cleaned))


def _normalize(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()
