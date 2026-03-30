from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class KeywordEnhancementSkill(BaseSkill):
    skill_type = "generic"
    skill_layer = "enhancement"
    skill_category = "analysis"
    priority = 70
    keywords: tuple[str, ...] = ()
    preferred_finding = ""
    preferred_recommendation = ""

    def match(self, context: dict[str, Any]) -> bool:
        if not self.supports_aspect(context):
            return False
        text = " ".join(
            [
                str(context.get("user_query", "")),
                str(context.get("query", "")),
                str(context.get("preference_profile", {}).get("user_intent_raw", "")),
                " ".join(self.evidence_text(item) for item in self.evidence_items(context)),
            ]
        ).lower()
        return any(keyword.lower() in text for keyword in self.keywords)

    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        hits = self.hits_by_keywords(context, self.keywords)
        if not hits:
            return self.build_result(
                summary=f"当前材料不足以支撑对“{self.goal or self.skill_name}”形成强结论。",
                pending_checks=[f"补充与“{self.goal or self.skill_name}”直接相关的章节或证据后再展开专项分析。"],
                confidence=0.24,
            )

        findings = [self.preferred_finding] if self.preferred_finding else [f"{self.goal or self.skill_name}已出现可供专项判断的直接线索。"]
        recommendations = (
            [self.preferred_recommendation]
            if self.preferred_recommendation
            else [f"继续沿着“{self.goal or self.skill_name}”补强后续跟踪指标和验证节点。"]
        )
        return self.build_result(
            summary=f"{self.goal or self.skill_name}是这次经营判断里需要单独看清的一环。",
            findings=findings,
            recommendations=recommendations,
            evidence=hits[:4],
            confidence=0.74 if len(hits) >= 3 else 0.58,
            pending_checks=[] if len(hits) >= 2 else [f"{self.goal or self.skill_name}当前证据仍偏薄，建议交叉验证。"],
        )


class CashflowSpecialistSkill(KeywordEnhancementSkill):
    skill_id = "cashflow_specialist"
    skill_name = "CashflowSpecialistSkill"
    description = "聚焦经营现金流、资金安全边际和偿债压力，补足财务专项判断。"
    goal = "现金流健康度专项"
    trigger_condition = "当用户强调现金流、偿债能力、资金安全边际，或系统识别到明显现金流信号时触发。"
    applicable_when = ["用户更关心现金流或偿债能力", "材料中出现经营现金流、债务、融资、回款等信号"]
    not_applicable_when = ["缺少财务或现金流相关材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "专项结论", "findings": "现金流相关判断", "recommendations": "后续跟踪指标", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否解释现金流与利润是否匹配", "是否识别偿债与流动性压力", "是否保留证据不足的降级表达"]
    tags = ["finance", "cashflow", "debt", "liquidity"]
    target_aspects = ("cashflow_health",)
    keywords = ("现金流", "经营现金流", "回款", "负债", "偿债", "融资", "资金")
    preferred_finding = "现金流与利润是否同步改善，决定本轮修复质量能否站稳。"
    preferred_recommendation = "优先复核经营现金流净额、短债覆盖和融资依赖的同步变化。"
    expert_role = "现金流与偿债顾问"
    domain_focus = "现金回流、短债覆盖、融资依赖和财务安全边际。"
    core_questions = ["利润有没有真正回到现金？", "公司遇到波动时，账上现金和融资能力够不够用？"]
    preferred_terms = ["经营现金流匹配", "短债压力", "现金流错配", "安全边际"]
    translation_rule = "先用现金流术语判断风险，再翻译成老板听得懂的资金安全感和抗波动能力。"
    reasoning_style = "优先看现金回流能否覆盖利润和债务压力，再判断修复能不能站稳。"


class EarningsQualitySpecialistSkill(KeywordEnhancementSkill):
    skill_id = "earnings_quality_specialist"
    skill_name = "EarningsQualitySpecialistSkill"
    description = "聚焦利润兑现质量、非经常性因素和盈利持续性。"
    goal = "盈利质量专项"
    trigger_condition = "当用户强调盈利质量、利润兑现或利润结构时触发。"
    applicable_when = ["用户更关心利润质量", "材料中出现净利润、扣非、毛利率、费用率等信号"]
    not_applicable_when = ["缺少利润相关材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "专项结论", "findings": "利润结构判断", "recommendations": "验证项", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否识别利润改善是否可持续", "是否提示利润与现金流、费用率的关系", "是否避免把短期改善写成长期趋势"]
    tags = ["finance", "earnings", "profit", "margin"]
    target_aspects = ("earnings_quality",)
    keywords = ("利润", "净利润", "扣非", "毛利率", "费用率", "盈利", "利润率")
    preferred_finding = "利润改善是否来自主营修复还是阶段性因素，是盈利质量专项最核心的判断。"
    preferred_recommendation = "继续核对扣非利润、毛利率、费用率和现金流是否相互印证。"
    expert_role = "财务分析师"
    domain_focus = "利润成色、非经常性因素、费用结构和盈利持续性。"
    core_questions = ["利润修复是不是主营修复？", "利润结构里有没有一次性项目或费用变化在抬高表观表现？"]
    preferred_terms = ["扣非利润", "毛利率", "费用率", "利润兑现质量"]
    translation_rule = "专业术语只服务于一个目的：解释公司现在赚的钱到底稳不稳、真不真。"
    reasoning_style = "先拆利润来源，再看费用和现金流是否跟上，最后判断持续性。"


class GrowthContinuitySkill(KeywordEnhancementSkill):
    skill_id = "growth_continuity"
    skill_name = "GrowthContinuitySkill"
    description = "聚焦增长来源、承接逻辑和持续性验证。"
    goal = "成长持续性分析"
    trigger_condition = "当用户更关心增长、成长性或中期承接能力时触发。"
    applicable_when = ["用户明确希望重点看增长或成长性", "材料中出现增量产品、新市场或承接逻辑"]
    not_applicable_when = ["缺少增长来源相关材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "成长持续性结论", "findings": "增长承接判断", "recommendations": "跟踪指标", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否解释增长由什么驱动", "是否说明增长能否延续", "是否提示增长兑现的前置条件"]
    tags = ["growth", "continuity", "pipeline"]
    target_aspects = ("growth_continuity",)
    keywords = ("增长", "成长", "持续", "承接", "新品", "增量", "恢复")
    preferred_finding = "增长本身不是结论，增长的来源、可复制性和承接节奏才是。"
    preferred_recommendation = "继续跟踪增量来源是否从预期转化为可验证的经营结果。"
    expert_role = "成长性分析师"
    domain_focus = "增长来源、兑现节奏和增长可持续性。"
    core_questions = ["增长来自哪里？", "这部分增长是一次性脉冲，还是可以持续接续？"]
    preferred_terms = ["增长承接", "兑现节奏", "可复制性", "持续性"]
    translation_rule = "把成长术语翻译成老板更关心的两个问题：增长能不能接上，能不能持续。"
    reasoning_style = "先识别增量来源，再看承接路径和兑现条件，最后判断持续性。"


class ProductBusinessStructureSkill(KeywordEnhancementSkill):
    skill_id = "product_business_structure"
    skill_name = "ProductBusinessStructureSkill"
    description = "聚焦产品结构、业务组合和收入支撑结构。"
    goal = "产品与业务结构分析"
    trigger_condition = "当用户明确关心产品结构、业务线或收入支撑结构时触发。"
    applicable_when = ["用户强调产品、业务线或结构性分析", "材料中出现产品线、业务分部、收入结构信息"]
    not_applicable_when = ["缺少业务结构或产品结构材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "产品与业务结构结论", "findings": "结构判断", "recommendations": "后续验证项", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否识别核心支撑业务", "是否指出结构集中度或接续问题", "是否保留业务结构不清的限制"]
    tags = ["product", "business_structure", "mix"]
    target_aspects = ("product_business_structure",)
    keywords = ("产品线", "业务线", "分部", "核心产品", "业务结构", "收入结构", "组合")
    preferred_finding = "产品与业务结构决定了增长质量、波动弹性和后续承接难度。"
    preferred_recommendation = "继续拆解核心业务贡献度和替代性，避免把单点改善误判为全面修复。"
    expert_role = "产品与业务分析师"
    domain_focus = "产品组合、业务结构、支撑来源和替代关系。"
    core_questions = ["现在到底是哪条业务在支撑基本盘？", "如果核心产品放缓，后面有没有接得上的替代项？"]
    preferred_terms = ["业务结构", "产品组合", "支撑来源", "替代性"]
    translation_rule = "把结构性术语翻译成老板能直接理解的收入支柱、接班梯队和波动来源。"
    reasoning_style = "先找支撑收入的主力，再看集中度和替代性，最后判断结构稳不稳。"


class IndustryCompetitionSkill(KeywordEnhancementSkill):
    skill_id = "industry_competition"
    skill_name = "IndustryCompetitionSkill"
    description = "聚焦行业竞争格局、需求环境和外部压力。"
    goal = "行业竞争分析"
    trigger_condition = "当用户强调行业竞争、外部环境或护城河判断时触发。"
    applicable_when = ["用户希望重点看竞争格局或行业压力", "材料中出现竞争、份额、需求、政策等线索"]
    not_applicable_when = ["缺少行业或竞争信息"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "行业竞争结论", "findings": "竞争判断", "recommendations": "后续指标", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否解释行业变化如何影响公司", "是否区分外部改善与公司自身改善", "是否控制泛行业空话"]
    tags = ["industry", "competition", "external"]
    target_aspects = ("industry_competition",)
    keywords = ("竞争", "格局", "份额", "行业", "需求", "景气", "政策", "监管")
    preferred_finding = "外部环境只能解释背景，真正重要的是外部变化如何改变公司的兑现难度。"
    preferred_recommendation = "继续拆分行业改善与公司自身执行改善各自贡献。"
    expert_role = "行业研究员"
    domain_focus = "行业景气、竞争格局、需求环境和外部变量。"
    core_questions = ["行业变化是在帮公司，还是在加大兑现难度？", "外部改善有多少能真正传导到公司报表？"]
    preferred_terms = ["景气度", "竞争强度", "市场份额", "兑现难度"]
    translation_rule = "行业术语要落到公司层面，讲清楚外部变化如何影响收入兑现和竞争位置。"
    reasoning_style = "先交代行业变化，再判断它对公司兑现难度和竞争位置的传导。"


class ManagementExecutionSkill(KeywordEnhancementSkill):
    skill_id = "management_execution"
    skill_name = "ManagementExecutionSkill"
    description = "聚焦管理层执行力、组织调整和经营抓手落地。"
    goal = "管理层执行力分析"
    trigger_condition = "当用户明确希望看管理诊断、执行力或组织抓手时触发。"
    applicable_when = ["用户偏管理诊断风格", "材料中出现管理层表述、组织调整、执行节奏等线索"]
    not_applicable_when = ["缺少管理层表述或组织信息"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "执行力结论", "findings": "经营抓手判断", "recommendations": "后续验证项", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否将管理层表述与经营结果分开", "是否识别组织动作的验证路径", "是否避免空泛评价执行力"]
    tags = ["management", "execution", "organization"]
    target_aspects = ("management_execution",)
    keywords = ("管理层", "执行", "组织", "调整", "战略", "董事会", "经营抓手")
    preferred_finding = "管理层表述本身不是证据，关键是是否存在可以跟踪的兑现抓手。"
    preferred_recommendation = "把管理层表述拆成可验证动作，并持续跟踪兑现结果。"
    expert_role = "经营管理顾问"
    domain_focus = "执行抓手、组织调整、管理层兑现能力和经营节奏。"
    core_questions = ["管理层说的事有没有落到可执行动作上？", "这些组织动作能不能传导到经营结果？"]
    preferred_terms = ["经营抓手", "执行节奏", "组织协同", "兑现能力"]
    translation_rule = "不评价管理层口号，直接翻译成有没有动作、动作能不能见效。"
    reasoning_style = "先把管理层表述拆成动作，再判断动作是否能验证、是否会影响经营。"


class OverseasBusinessSkill(KeywordEnhancementSkill):
    skill_id = "overseas_business"
    skill_name = "OverseasBusinessSkill"
    description = "聚焦海外业务、区域扩张和跨区域兑现能力。"
    goal = "海外业务分析"
    trigger_condition = "当用户明确提到出海、海外或区域市场时触发。"
    applicable_when = ["用户强调出海或区域市场", "材料中出现海外收入、区域发行或国际化信息"]
    not_applicable_when = ["缺少区域或海外业务材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "海外业务结论", "findings": "区域判断", "recommendations": "跟踪指标", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否解释海外业务是增量还是噪音", "是否指出区域兑现条件", "是否提示区域风险差异"]
    tags = ["overseas", "regional", "international"]
    target_aspects = ("overseas_business",)
    keywords = ("出海", "海外", "国际", "区域", "境外", "海外收入")
    preferred_finding = "海外业务的核心不只是有无布局，而是是否已形成可复制的兑现路径。"
    preferred_recommendation = "继续跟踪区域市场的收入占比、产品适配和发行效率。"
    expert_role = "海外业务分析师"
    domain_focus = "区域市场、海外收入、发行适配和跨区域兑现能力。"
    core_questions = ["海外业务是概念布局，还是已经形成实际增量？", "区域扩张能不能复制，风险点在哪里？"]
    preferred_terms = ["区域兑现", "产品适配", "发行效率", "海外增量"]
    translation_rule = "把出海术语翻译成老板最关心的三件事：能不能赚到钱、能不能复制、风险在哪。"
    reasoning_style = "先判断海外收入和区域动作是否真实，再看产品适配和复制能力。"


class ProductLifecycleSkill(KeywordEnhancementSkill):
    skill_id = "product_lifecycle"
    skill_name = "ProductLifecycleSkill"
    description = "聚焦老产品衰退、新品承接和产品生命周期节奏。"
    goal = "产品生命周期分析"
    trigger_condition = "当用户强调产品生命周期、老产品衰退或新品承接时触发。"
    applicable_when = ["用户重点关注产品周期", "材料中出现老产品、新产品、承接节奏等信号"]
    not_applicable_when = ["缺少产品周期材料"]
    required_inputs = ["evidence_pack", "preference_profile", "subtask"]
    optional_inputs = ["analysis_results"]
    output_schema = {"summary": "生命周期结论", "findings": "承接判断", "recommendations": "跟踪指标", "evidence_refs": "证据锚点"}
    evaluation_criteria = ["是否把老产品与新品承接关系说清楚", "是否说明周期切换风险", "是否避免把储备直接等同于兑现"]
    tags = ["product", "lifecycle", "transition"]
    target_aspects = ("product_lifecycle",)
    keywords = ("生命周期", "老产品", "新品", "承接", "衰退", "上线", "储备")
    preferred_finding = "产品周期切换的关键不在储备多少，而在老产品下滑与新品兑现是否能平滑衔接。"
    preferred_recommendation = "继续跟踪老产品衰退速度、新品上线节奏和流水承接强度。"
    expert_role = "产品生命周期分析师"
    domain_focus = "老产品衰退、新品接续和产品节奏切换。"
    core_questions = ["老产品下滑有多快？", "新品能不能在合适的时间接上收入和流水？"]
    preferred_terms = ["生命周期切换", "新品承接", "流水接续", "节奏错配"]
    translation_rule = "把生命周期术语翻译成老板能直接理解的接棒问题：老的掉多快，新的接多快。"
    reasoning_style = "先看老产品衰退，再看新品兑现节奏，最后判断切换是否平滑。"
