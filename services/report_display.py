from __future__ import annotations

from typing import Any


SUMMARY_METRIC_ORDER = (
    "总分",
    "风险等级",
    "经营基本盘",
    "利润兑现质量",
    "现金回流与财务缓冲",
    "外部环境与竞争位置",
)

SUMMARY_METRIC_LABEL_ALIASES = {
    "健康度评分": "总分",
    "健康度": "总分",
    "风险分": "总分",
    "经营质量": "经营基本盘",
    "盈利质量": "利润兑现质量",
    "现金流健康度": "现金回流与财务缓冲",
    "行业与外部环境适配度": "外部环境与竞争位置",
}


def build_summary_metrics(report: dict[str, Any]) -> list[dict[str, str]]:
    payload = report.get("report_payload") or {}
    raw_cards = payload.get("summary_cards") or []
    metrics_by_label: dict[str, str] = {}

    for item in raw_cards:
        label = _normalize_label(item.get("label"))
        value = _string_value(item.get("value"))
        if label and value and label not in metrics_by_label:
            metrics_by_label[label] = value

    score_breakdown = (payload.get("report_layer") or {}).get("score_breakdown") or {}
    if score_breakdown:
        if "总分" not in metrics_by_label and _string_value(score_breakdown.get("total_score")):
            metrics_by_label["总分"] = _string_value(score_breakdown.get("total_score"))
        if "风险等级" not in metrics_by_label and _string_value(score_breakdown.get("risk_level")):
            metrics_by_label["风险等级"] = _string_value(score_breakdown.get("risk_level"))

    if "总分" not in metrics_by_label and _string_value(report.get("total_score")):
        metrics_by_label["总分"] = _string_value(report.get("total_score"))
    if "风险等级" not in metrics_by_label and _string_value(report.get("risk_level")):
        metrics_by_label["风险等级"] = _string_value(report.get("risk_level"))

    ordered_metrics: list[dict[str, str]] = []
    for label in SUMMARY_METRIC_ORDER:
        if label in metrics_by_label:
            ordered_metrics.append({"label": label, "value": metrics_by_label.pop(label)})

    ordered_metrics.extend({"label": label, "value": value} for label, value in metrics_by_label.items())
    return ordered_metrics


def _normalize_label(value: Any) -> str:
    label = str(value or "").strip()
    if not label:
        return ""
    return SUMMARY_METRIC_LABEL_ALIASES.get(label, label)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
