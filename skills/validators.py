from __future__ import annotations

import re
from typing import Any

from skills.base import BaseSkill


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


class EvidenceGapSkill(BaseSkill):
    skill_id = "evidence_gap_check"
    skill_name = "EvidenceGapSkill"
    skill_type = "generic"
    skill_layer = "governance"
    skill_category = "validation"
    goal = "识别证据覆盖不足、低置信度和需要保守降级的部分"
    required_inputs = ["analysis_results"]
    tags = ["governance", "evidence", "quality"]
    priority = 85
    description = "检查各子任务是否存在证据覆盖不足与低置信度问题。"
    trigger_condition = "分析阶段完成后执行。"
    evaluation_criteria = ["是否标记低证据覆盖任务", "是否输出可执行的待核验项"]
    example_use_case = "在最终报告中显式标记证据不足区。"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        analysis_results = context.get("analysis_results", [])
        findings: list[str] = []
        pending_checks: list[str] = []

        for item in analysis_results:
            subtask = item.get("subtask", {})
            outputs = item.get("outputs", [])
            evidence_count = sum(len(output.get("evidence_refs", [])) for output in outputs)
            confidence_values = [float(output.get("confidence", 0)) for output in outputs]
            confidence = max(confidence_values) if confidence_values else 0
            if evidence_count < 2:
                pending_checks.append(f"{subtask.get('title', subtask.get('key', '未命名任务'))}：证据覆盖不足，建议补充定向检索。")
            if confidence < 0.45:
                findings.append(f"{subtask.get('title', subtask.get('key', '未命名任务'))}：当前结论置信度偏低，应谨慎使用。")

        if not findings and not pending_checks:
            findings.append("主要子任务均已获得至少基础级证据支撑。")

        return self.build_result(
            summary="已完成证据缺口扫描。",
            findings=findings,
            pending_checks=pending_checks,
            confidence=0.72,
        )


class ConsistencyCheckSkill(BaseSkill):
    skill_id = "consistency_check"
    skill_name = "ConsistencyCheckSkill"
    skill_type = "generic"
    skill_layer = "governance"
    skill_category = "validation"
    goal = "检查重复结论、冲突表述和口径不一致问题"
    required_inputs = ["analysis_results"]
    tags = ["governance", "consistency", "dedupe"]
    priority = 84
    description = "检查多技能输出中的重复结论与潜在冲突。"
    trigger_condition = "分析阶段完成后执行。"
    evaluation_criteria = ["是否提示重复/冲突结论", "是否避免误报普通差异为冲突"]
    example_use_case = "在报告合成前减少重复段落并暴露矛盾点。"

    positive_words = ("增长", "改善", "回升", "稳健", "提升")
    negative_words = ("下滑", "承压", "亏损", "风险", "减值")

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        analysis_results = context.get("analysis_results", [])
        findings: list[str] = []
        all_findings: list[str] = []
        duplicate_count = 0
        normalized_seen: set[str] = set()
        positive_hits = 0
        negative_hits = 0

        for item in analysis_results:
            for output in item.get("outputs", []):
                for finding in output.get("findings", []):
                    normalized = _normalize(finding)
                    if normalized in normalized_seen:
                        duplicate_count += 1
                    else:
                        normalized_seen.add(normalized)
                    all_findings.append(finding)
                    if any(word in finding for word in self.positive_words):
                        positive_hits += 1
                    if any(word in finding for word in self.negative_words):
                        negative_hits += 1

        if duplicate_count:
            findings.append(f"检测到 {duplicate_count} 处近似重复结论，合成报告时应去重压缩。")
        if positive_hits and negative_hits:
            findings.append("不同子任务同时出现改善与承压信号，需在报告中明确时间口径与适用范围。")
        if not findings:
            findings.append("当前多技能输出未发现明显重复或强冲突。")

        return self.build_result(
            summary="已完成一致性与重复检查。",
            findings=findings,
            confidence=0.69,
            metadata={"raw_findings_count": len(all_findings)},
        )
