from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class CompanyOverviewSkill(BaseSkill):
    skill_id = "company_overview"
    skill_name = "CompanyOverviewSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "analysis"
    goal = "提炼材料覆盖范围、公司画像和研究边界"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["overview", "foundation"]
    priority = 78
    description = "提炼当前样本覆盖范围、核心章节与企业概览锚点。"
    trigger_condition = "在概览子任务中执行。"
    target_aspects = ("overview",)
    input_schema = {"evidence_pack": "检索证据包", "subtask": "概览子任务"}
    output_schema = {"summary": "概览摘要", "findings": "覆盖范围与材料分布", "evidence_refs": "概览证据"}
    evaluation_criteria = ["是否交代材料覆盖范围", "是否说明核心章节/来源", "是否避免无证据公司画像"]
    example_use_case = "在企业体检报告开头建立材料范围与分析边界。"
    expert_role = "企业研究总览分析师"
    domain_focus = "材料覆盖范围、业务轮廓和当前判断边界。"
    core_questions = ["现有材料到底覆盖了哪些经营议题？", "哪些判断可以下结论，哪些只能保守表述？"]
    preferred_terms = ["披露口径", "业务轮廓", "研究边界"]
    translation_rule = "先说明材料覆盖到哪里，再把研究边界翻译成老板能理解的判断强弱。"
    reasoning_style = "先确认材料覆盖，再决定结论强度，避免把证据空白写成确定性判断。"

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        evidence = self.evidence_items(context)
        if not evidence:
            return self.build_result(
                summary="现有披露仍不足以建立清晰的公司画像。",
                pending_checks=["补充公司年报或研究报告后再提炼概览。"],
                confidence=0.2,
            )

        unique_sources = list(dict.fromkeys(item.get("source", "") for item in evidence if item.get("source")))
        unique_sections = list(
            dict.fromkeys(
                item.get("section_path") or item.get("section_title")
                for item in evidence
                if item.get("section_path") or item.get("section_title")
            )
        )
        findings = [f"现有材料主要覆盖 {', '.join(unique_sources[:3])} 等公开披露，足以建立业务结构和研究边界的基础判断。"]
        if unique_sections:
            findings.append(f"当前判断重点落在 {', '.join(unique_sections[:3])} 等章节，说明结论更依赖公司披露口径而非短期交易性信息。")

        return self.build_result(
            summary="现有材料足以建立业务结构、重点议题和研究边界的基础判断。",
            findings=findings,
            recommendations=["继续沿管理层讨论、风险因素和重点产品章节深挖，确认核心业务与管理层关注点是否出现变化。"],
            evidence=evidence[:3],
            confidence=0.68 if len(evidence) >= 3 else 0.52,
        )


class FinancialHealthSkill(BaseSkill):
    skill_id = "financial_health"
    skill_name = "FinancialHealthSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "analysis"
    goal = "围绕收入、利润、现金流和负债压力做基础财务经营分析"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["finance", "foundation"]
    priority = 79
    description = "围绕收入、利润、现金流、负债和成本压力做证据绑定分析。"
    trigger_condition = "财务/经营健康子任务触发。"
    target_aspects = ("financial_health",)
    evaluation_criteria = ["是否覆盖经营表现与现金流", "是否对负面信号保持谨慎措辞", "是否给出待核验项"]
    example_use_case = "识别公司经营承压或改善信号，并说明证据边界。"
    expert_role = "财务分析师"
    domain_focus = "收入质量、利润兑现、费用结构、现金流和负债压力。"
    core_questions = ["利润改善是不是主营经营带来的？", "利润、现金流和费用投放能不能互相印证？"]
    preferred_terms = ["扣非利润", "经营现金流", "费用率", "利润兑现质量"]
    translation_rule = "用必要的财务术语，但要顺手解释成经营上有没有真正赚到钱、回到现金。"
    reasoning_style = "从报表和披露里先找利润、现金流和费用三者是否一致，再判断修复成色。"

    keywords = ["营收", "收入", "利润", "净利", "毛利", "现金流", "负债", "偿债", "费用", "经营", "业绩"]
    negative_words = ["下降", "亏损", "承压", "波动", "减值", "下滑", "不及预期"]
    positive_words = ["增长", "改善", "提升", "回升", "稳健", "修复", "充足"]

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="现有披露仍不足以支撑对财务与经营健康度的强判断。",
                pending_checks=["补充收入、利润、现金流或负债章节的定向证据。"],
                confidence=0.28,
            )

        negative_hits = 0
        positive_hits = 0
        matched_flags: list[str] = []
        for item in hits:
            text = self.evidence_text(item)
            for word in self.negative_words:
                if word in text:
                    negative_hits += 1
                    matched_flags.append(word)
            for word in self.positive_words:
                if word in text:
                    positive_hits += 1

        findings = []
        if negative_hits > positive_hits:
            findings.append("盈利质量与现金流相关表述偏承压，当前更需要确认压力是阶段性波动还是结构性走弱。")
        elif positive_hits:
            findings.append("财务披露中同时存在改善与承压线索，短期修复是否可持续仍需结合现金流和费用投放判断。")
        else:
            findings.append("现有财务表述仍偏定性，尚不足以支持更强的盈利趋势判断。")

        pending_checks: list[str] = []
        if len(hits) < 2:
            pending_checks.append("财务结论样本较少，需补充更多章节或研报交叉验证。")
        if negative_hits and positive_hits:
            pending_checks.append("同一维度同时出现改善与承压表述，需要核对时间口径与分部差异。")

        return self.build_result(
            summary="财务与经营健康度是当前风险判断的核心，需要同时看盈利、费用与现金流是否匹配。",
            findings=findings,
            recommendations=["复核利润波动是否受一次性因素影响，并检查现金流与费用投放匹配度。"],
            evidence=hits[:4],
            confidence=0.74 if len(hits) >= 3 else 0.58,
            pending_checks=pending_checks,
            risk_flags=list(dict.fromkeys(matched_flags))[:5],
        )


class GovernanceComplianceSkill(BaseSkill):
    skill_id = "governance_compliance"
    skill_name = "GovernanceComplianceSkill"
    skill_type = "generic"
    skill_layer = "foundation"
    skill_category = "analysis"
    goal = "识别治理、内控、监管和重大合规约束"
    required_inputs = ["evidence_pack", "subtask"]
    tags = ["governance", "foundation"]
    priority = 76
    description = "识别治理、合规、监管、诉讼与内控相关风险线索。"
    trigger_condition = "治理与合规子任务触发。"
    target_aspects = ("governance_compliance",)
    evaluation_criteria = ["是否识别治理/监管风险", "是否避免将常规披露夸大为重大风险", "是否绑定来源页码"]
    example_use_case = "在企业体检中单列治理与合规观察。"
    expert_role = "治理与合规分析师"
    domain_focus = "内控质量、监管约束、治理稳定性和重大合规暴露。"
    core_questions = ["这是常规披露，还是会影响经营确定性的真实约束？", "治理和监管问题会不会传导到执行或融资层面？"]
    preferred_terms = ["内控", "监管约束", "治理稳定性", "合规暴露"]
    translation_rule = "不堆法规术语，重点解释这些事项会不会打断经营节奏或抬高不确定性。"
    reasoning_style = "先区分常规合规披露和异常事项，再判断是否足以影响经营判断。"

    keywords = ["治理", "合规", "监管", "处罚", "诉讼", "内控", "审计", "关联交易", "版号", "许可", "资质"]

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary="治理与合规层面暂未出现明确高压信号，但结论仍依赖公开披露完整性。",
                findings=["现有材料未显示治理或合规层面的明显高压信号，但这并不等于完全没有后续约束。"],
                pending_checks=["如需合规判断，仍应补充年报风险因素与监管公告。"],
                confidence=0.44,
            )

        findings = ["治理、合规或监管线索已经出现，但现阶段更像潜在约束而非已确认的重大冲击。"]
        recommendations = ["针对治理与监管线索，核查其是否构成持续性或实质性经营约束。"]

        return self.build_result(
            summary="治理与合规线索目前更像需要留意的约束条件，而不是已经落地的重大冲击。",
            findings=findings,
            recommendations=recommendations,
            evidence=hits[:4],
            confidence=0.65 if len(hits) >= 2 else 0.5,
        )
