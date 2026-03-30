from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from services.llm_client import LLMClient
from skills.evidence_ranking import dedupe_evidence, evidence_citation, select_ranked_evidence, summarize_evidence, to_evidence_ref


REPORT_TITLE = "企业体检报告"
SUMMARY_SIMILARITY_THRESHOLD = 0.82
MAX_BODY_SECTIONS = 4

BANNED_TEXT_FRAGMENTS = (
    "看到的事实：",
    "这说明什么：",
    "后续应跟踪：",
    "后续应跟踪",
    "专项会直接影响本次报告判断强度",
    "负向信号数量高于改善信号",
    "当前更适合作为约束项持续跟踪",
    "按中性偏保守口径处理",
    "skill",
    "评分子项",
    "路由",
)

DIMENSION_DISPLAY_LABELS = {
    "business_quality": "经营基本盘",
    "earnings_quality": "利润兑现质量",
    "cashflow_health": "现金回流与财务缓冲",
    "industry_environment": "外部环境与竞争位置",
}

SUBITEM_GUIDES: dict[str, dict[str, str]] = {
    "revenue_growth_quality": {
        "label": "收入修复质量",
        "risk_title": "收入修复的质量还不够扎实",
        "opportunity_title": "收入修复开始具备更稳的基础",
        "negative": "收入改善已经出现，但增量来源和延续性还没有完全坐实。",
        "positive": "收入修复不只停留在单点改善，已有更稳的业务支撑。",
        "neutral": "收入端既有改善也有波动，短期更适合看成验证中的修复。",
        "importance": "这类信号重要，因为它决定后续增长是不是有真实承接。",
        "impact": "收入延续性和经营基本盘稳定度",
        "action": "复核分业务收入、核心产品流水和增量来源的连续性",
        "purpose": "确认收入修复是不是可持续的经营改善",
        "focus": "分业务收入、核心产品/渠道表现、增量来源",
        "why_important": "这直接决定增长是不是短期修复，还是已经有稳定承接。",
    },
    "core_business_support": {
        "label": "核心业务支撑",
        "risk_title": "核心业务对增长的支撑还不够稳",
        "opportunity_title": "核心业务仍在托住基本盘",
        "negative": "当前核心业务的支撑力度还不够强，增长接力仍有不确定性。",
        "positive": "核心业务仍在托住经营基本盘，短期没有明显失速迹象。",
        "neutral": "核心业务有支撑，但接续强度还需要更多披露确认。",
        "importance": "它决定公司是不是还有稳定的赚钱主轴，而不是只能依赖单点波动。",
        "impact": "收入基本盘和增长承接能力",
        "action": "拆解核心业务贡献度和替代性",
        "purpose": "确认经营基本盘是否足够稳固",
        "focus": "核心业务收入占比、头部产品表现、替代来源",
        "why_important": "如果核心支撑走弱而替代项接不上，增长和利润都会更容易失速。",
    },
    "operating_stability": {
        "label": "经营稳定性",
        "risk_title": "经营波动尚未明显收敛",
        "opportunity_title": "经营波动开始收敛",
        "negative": "经营层面的波动仍然存在，改善还没有稳定到足以支撑更强判断。",
        "positive": "经营波动已经开始收敛，说明修复不只体现在单个季度数字上。",
        "neutral": "经营状态处在修复和波动并存阶段，还需要时间验证稳定性。",
        "importance": "这一点决定公司后续表现是偶发改善，还是进入更平稳的经营区间。",
        "impact": "收入稳定度、利润弹性和管理执行节奏",
        "action": "跟踪费用率、组织调整和经营波动是否继续收敛",
        "purpose": "确认改善是不是正在固化成稳定经营表现",
        "focus": "费用率、组织动作、季度波动幅度",
        "why_important": "稳定性不够时，任何阶段性改善都可能被下一轮波动抵消。",
    },
    "profit_realization": {
        "label": "主营利润兑现",
        "risk_title": "利润修复的成色还不够",
        "opportunity_title": "主营盈利改善开始兑现",
        "negative": "利润改善还没有完全证明来自主营经营，修复成色仍需核实。",
        "positive": "利润改善更像来自主营经营修复，而不是短期项目抬升。",
        "neutral": "利润端已有改善线索，但还不足以直接上调盈利质量判断。",
        "importance": "利润修复是不是主营修复，决定这轮改善能不能持续。",
        "impact": "利润质量、估值承受力和经营韧性",
        "action": "复核扣非利润、毛利率和费用率的同步变化",
        "purpose": "确认利润改善是不是主营经营带来的",
        "focus": "扣非利润、毛利率、费用率、主营业务贡献",
        "why_important": "如果利润主要靠短期因素抬升，后续利润弹性往往不稳。",
    },
    "profit_structure": {
        "label": "利润结构成色",
        "risk_title": "利润结构里仍有一次性项目扰动",
        "opportunity_title": "利润结构更接近主营经营质量",
        "negative": "利润结构里仍可能混有一次性项目或非经营性扰动，表观利润不宜直接上调解读。",
        "positive": "利润结构更接近主营经营改善，非经常性扰动对结论的干扰正在下降。",
        "neutral": "利润结构没有明显恶化，但还不足以完全排除一次性因素影响。",
        "importance": "这一步是在区分公司是真的更会赚钱了，还是报表阶段性更好看。",
        "impact": "利润质量、业绩兑现可信度和后续可持续性",
        "action": "核对非经常性损益、投资收益和减值项目的占比变化",
        "purpose": "判断利润改善的来源是否足够健康",
        "focus": "非经常性损益、投资收益、减值项目、主营利润占比",
        "why_important": "利润结构不健康时，短期业绩改善很难转成稳定的经营预期。",
    },
    "profit_sustainability": {
        "label": "利润持续性",
        "risk_title": "利润改善的持续性还没有坐实",
        "opportunity_title": "利润改善具备继续延续的基础",
        "negative": "利润改善能否延续，仍然取决于后续产品、费用和收入承接是否跟上。",
        "positive": "利润改善已不只是单点修复，后续延续性开始有可验证基础。",
        "neutral": "利润趋势仍处在观察期，需要更多连续披露来确认持续性。",
        "importance": "它决定利润改善是一次性修复，还是有可能延续到后续周期。",
        "impact": "利润弹性、中期业绩能见度和经营预期",
        "action": "跟踪后续产品表现和利润弹性的延续情况",
        "purpose": "确认利润改善是否具备持续性",
        "focus": "后续产品表现、利润率变化、费用投放强度",
        "why_important": "持续性坐不实，市场和管理层都很难把当前利润改善当成新常态。",
    },
    "cashflow_match": {
        "label": "利润与现金回流匹配",
        "risk_title": "利润还没有顺畅变成现金",
        "opportunity_title": "回款开始跟上经营修复",
        "negative": "利润改善还没有充分传导到经营现金流，回款质量仍是关键约束。",
        "positive": "利润和经营现金流开始互相印证，说明修复不只停留在报表层面。",
        "neutral": "现金回流没有明显恶化，但也还不足以完全坐实利润修复的质量。",
        "importance": "现金流比利润表更难粉饰，它决定修复是真是假、稳不稳。",
        "impact": "现金流质量、偿债能力和经营韧性",
        "action": "复核经营现金流净额、回款节奏和应收变化",
        "purpose": "确认利润修复是否已经落到现金质量上",
        "focus": "经营现金流净额、应收账款、回款周期、预收变化",
        "why_important": "利润回不到现金，修复就很容易停留在账面改善。",
    },
    "cashflow_volatility": {
        "label": "资金进出波动",
        "risk_title": "资金进出波动仍然偏大",
        "opportunity_title": "资金进出开始更可控",
        "negative": "投资、筹资或经营端的现金波动仍偏大，资金安排的稳定性还不够强。",
        "positive": "现金流波动开始收敛，资金安排更接近可控状态。",
        "neutral": "现金流波动目前没有失控，但还不足以说明资金安排已经明显改善。",
        "importance": "资金进出越不稳定，经营动作和利润修复越容易被打断。",
        "impact": "资金调度能力、经营连续性和财务安全感",
        "action": "跟踪经营、投资和筹资现金流的波动来源",
        "purpose": "判断资金安排是否已经趋稳",
        "focus": "经营/投资/筹资现金流、资本开支、融资节奏",
        "why_important": "波动大时，公司即使有改善迹象，也更容易被资金节奏反复影响。",
    },
    "financial_safety": {
        "label": "短期财务缓冲",
        "risk_title": "短期财务缓冲还不算宽裕",
        "opportunity_title": "账上缓冲仍能托住财务安全",
        "negative": "货币资金、短债覆盖和融资依赖之间的平衡还不够舒服，安全边际偏薄。",
        "positive": "账上资金和债务结构仍保留了一定安全边际，短期没有明显挤压经营。",
        "neutral": "财务安全边际暂未明显恶化，但缓冲厚度仍需要继续确认。",
        "importance": "安全边际决定公司遇到波动时，能不能扛住而不牺牲经营动作。",
        "impact": "偿债能力、融资灵活性和经营安全性",
        "action": "复核货币资金、短期债务和融资依赖的同步变化",
        "purpose": "确认公司是否仍有足够财务缓冲",
        "focus": "货币资金、短期债务、利息负担、融资依赖",
        "why_important": "安全边际偏薄时，一旦经营波动，风险会更快传导到财务端。",
    },
    "demand_environment": {
        "label": "需求环境",
        "risk_title": "外部需求恢复力度仍有限",
        "opportunity_title": "外部需求环境开始改善",
        "negative": "外部需求恢复还不够强，公司兑现增长仍需要更多自身执行来弥补。",
        "positive": "外部需求环境开始改善，为公司兑现增长提供了更顺的底层环境。",
        "neutral": "需求环境没有明显拖累，但也还称不上足够强的顺风。",
        "importance": "外部需求决定公司增长是在逆风里硬扛，还是能借势放大。",
        "impact": "收入兑现难度和增长斜率",
        "action": "跟踪行业景气、需求恢复和终端反馈变化",
        "purpose": "判断外部环境是拖累还是开始顺风",
        "focus": "行业景气、需求恢复节奏、终端反馈",
        "why_important": "需求环境改善时，公司内部动作更容易兑现；反之则要付出更高代价。",
    },
    "competition_environment": {
        "label": "竞争压力",
        "risk_title": "竞争环境正在抬高兑现难度",
        "opportunity_title": "竞争位置仍有一定支撑",
        "negative": "竞争强度没有明显缓和，公司要兑现增长和利润都需要更强执行。",
        "positive": "竞争位置仍有一定支撑，说明公司并未在核心赛道明显掉队。",
        "neutral": "竞争环境可控，但护城河和兑现优势还需要继续验证。",
        "importance": "竞争格局直接决定公司拿增长、守利润要付出多大代价。",
        "impact": "市场份额、盈利空间和兑现效率",
        "action": "拆解竞争格局变化和核心产品/业务的位置",
        "purpose": "确认公司在竞争中是不是仍有优势支点",
        "focus": "竞争对手动作、产品位置、市场份额、渠道变化",
        "why_important": "竞争一旦加剧，即使行业回暖，公司也可能很难把机会转成利润。",
    },
    "external_catalyst_constraint": {
        "label": "政策与外部变量",
        "risk_title": "政策和外部变量仍可能打断节奏",
        "opportunity_title": "外部变量开始转为顺风",
        "negative": "政策、监管或技术变量仍可能改变公司兑现节奏，外部不确定性还没有完全散去。",
        "positive": "外部变量开始从约束转向催化，为后续兑现提供额外顺风。",
        "neutral": "外部变量当前影响中性，但仍需要防止节奏被突发因素打断。",
        "importance": "这类变量往往不是每天发生，但一旦发生就会直接改变兑现时间表。",
        "impact": "收入兑现节奏、项目推进和经营确定性",
        "action": "跟踪政策、监管、技术工具链和外部窗口变化",
        "purpose": "判断外部变量会不会改变项目推进节奏",
        "focus": "政策变化、监管口径、技术工具链、关键外部窗口",
        "why_important": "外部变量一旦转弱，最先受影响的往往是兑现时点和经营确定性。",
    },
}

ASPECT_GUIDES: dict[str, dict[str, Any]] = {
    "overview": {"title": "本次判断建立在什么材料边界上", "domain_group": "overview", "impact": "结论强度和判断边界", "business_question": "现有材料到底足不足以支撑更强判断", "why_key": "先看清材料边界，才能知道哪些结论可以说重、哪些必须保守。", "related_subitems": []},
    "financial_health": {"title": "利润兑现与现金回流是否对得上", "domain_group": "finance", "impact": "利润质量、现金流和经营韧性", "business_question": "利润修复是不是已经落到现金和经营质量上", "why_key": "财务分析里最关键的不是数字好不好看，而是利润、费用和现金流能不能互相印证。", "related_subitems": ["profit_realization", "profit_structure", "cashflow_match"]},
    "governance_compliance": {"title": "治理与合规会不会抬高不确定性", "domain_group": "governance", "impact": "经营确定性、执行稳定性和风险暴露", "business_question": "这些治理与合规线索会不会真正传导到经营层面", "why_key": "治理和合规不一定每天影响业绩，但一旦出问题，往往直接改变经营确定性。", "related_subitems": ["external_catalyst_constraint"]},
    "product_pipeline": {"title": "新品储备能不能接上下一段增长", "domain_group": "growth", "impact": "收入承接、增长持续性和产品节奏", "business_question": "新品储备和上线节奏是否足以接住老产品波动", "why_key": "储备多不等于能兑现，真正重要的是测试、版号和上线节奏能不能接上收入。", "related_subitems": ["core_business_support", "profit_sustainability"]},
    "operation_performance": {"title": "核心产品基本盘稳不稳", "domain_group": "growth", "impact": "收入稳定度、流水承接和经营基本盘", "business_question": "老产品和核心产品还能不能继续托住当前基本盘", "why_key": "产品运营分析最怕把短期活动效果当成长线生命力，所以要分清基本盘和短期拉动。", "related_subitems": ["core_business_support", "operating_stability"]},
    "regulation_publishing": {"title": "版号和发行节奏会不会拖慢兑现", "domain_group": "governance", "impact": "项目推进节奏和收入确认时点", "business_question": "外部审批和发行准备会不会打乱既定节奏", "why_key": "这类问题不一定改变需求，但很容易直接改变兑现时间表。", "related_subitems": ["external_catalyst_constraint"]},
    "industry_trend": {"title": "外部技术与行业变化如何传导到经营", "domain_group": "industry", "impact": "研发效率、竞争位置和兑现难度", "business_question": "行业变化是背景噪音，还是已经影响到公司兑现难度", "why_key": "行业判断不能停留在讲故事，关键是它有没有真的改变公司的经营门槛。", "related_subitems": ["demand_environment", "external_catalyst_constraint"]},
    "marketing_efficiency": {"title": "增长里有多少是投放驱动", "domain_group": "finance", "impact": "增长质量、利润弹性和获客效率", "business_question": "增长是产品自然拉动，还是更多依赖投放换来的", "why_key": "营销效率决定增长质量，高增长如果靠更重投放换来，利润和持续性都要打折。", "related_subitems": ["profit_structure", "operating_stability"]},
    "overseas_market": {"title": "海外市场是增量还是执行波动", "domain_group": "overseas", "impact": "新增收入、区域风险和复制能力", "business_question": "海外布局是不是已经形成可复制的兑现路径", "why_key": "出海价值不在于有没有布局，而在于能不能复制、能不能稳定兑现。", "related_subitems": ["external_catalyst_constraint", "demand_environment"]},
    "ip_dependency": {"title": "内容供给是否过度依赖少数项目", "domain_group": "growth", "impact": "内容供给连续性、增长弹性和产品矩阵稳定性", "business_question": "一旦核心 IP 或项目波动，后续供给能不能补上", "why_key": "内容供给一旦过于集中，波动就会很快反映到收入和利润弹性上。", "related_subitems": ["core_business_support", "profit_sustainability"]},
    "earnings_quality": {"title": "利润修复能不能经得起拆分", "domain_group": "finance", "impact": "利润质量和持续性", "business_question": "利润改善是不是主营改善", "why_key": "盈利质量的核心不只是利润高低，而是利润来源够不够干净、够不够持续。", "related_subitems": ["profit_realization", "profit_structure", "profit_sustainability"]},
    "cashflow_health": {"title": "现金回流和偿债缓冲够不够扎实", "domain_group": "finance", "impact": "现金安全性、偿债能力和经营韧性", "business_question": "利润有没有回到现金，账上缓冲够不够扛波动", "why_key": "现金流问题往往比利润表更早暴露风险，也更直接决定安全边际。", "related_subitems": ["cashflow_match", "cashflow_volatility", "financial_safety"]},
    "growth_continuity": {"title": "增长能不能持续接力", "domain_group": "growth", "impact": "增长延续性和收入斜率", "business_question": "增量来源能不能持续转成经营结果", "why_key": "成长性分析看的不是单次增长，而是增长能不能持续接力。", "related_subitems": ["revenue_growth_quality", "profit_sustainability"]},
    "product_business_structure": {"title": "谁在支撑当前业务基本盘", "domain_group": "growth", "impact": "收入支撑结构和波动弹性", "business_question": "公司现在靠哪条业务赚钱，后面有没有接班梯队", "why_key": "结构稳不稳，决定公司未来遇到波动时有没有可替代的支柱。", "related_subitems": ["core_business_support", "revenue_growth_quality"]},
    "industry_competition": {"title": "竞争和需求环境有没有变好", "domain_group": "industry", "impact": "市场份额、增长难度和盈利空间", "business_question": "外部环境是在帮公司，还是在加大兑现难度", "why_key": "行业变化只有传导到公司层面，才值得写进经营判断。", "related_subitems": ["demand_environment", "competition_environment"]},
    "management_execution": {"title": "管理动作有没有转成经营抓手", "domain_group": "governance", "impact": "执行效率和经营兑现能力", "business_question": "管理层动作有没有真正落成可验证的经营抓手", "why_key": "管理层表述本身不是结论，兑现动作和结果才是。", "related_subitems": ["operating_stability"]},
    "overseas_business": {"title": "海外扩张是否形成可复制路径", "domain_group": "overseas", "impact": "海外增量和区域执行风险", "business_question": "海外业务是不是已经形成稳定复制能力", "why_key": "海外增量最怕只在个别区域成立，无法复制。", "related_subitems": ["demand_environment", "external_catalyst_constraint"]},
    "product_lifecycle": {"title": "老产品与新品切换是否平滑", "domain_group": "growth", "impact": "流水接续和产品周期稳定性", "business_question": "老产品下滑和新品上线之间能不能顺利接棒", "why_key": "产品周期错配时，收入和利润最容易出现断档。", "related_subitems": ["core_business_support", "profit_sustainability"]},
}

TERM_EXPLANATIONS = {
    "扣非利润": "判断主营赚钱能力",
    "经营现金流": "判断利润有没有真正回到现金",
    "费用率": "判断增长是不是靠更重投入换来的",
    "毛利率": "判断产品和业务本身赚钱效率",
    "短债压力": "判断短期债务会不会挤压经营",
    "安全边际": "判断公司遇到波动时还能不能扛住",
    "景气度": "判断行业整体是不是顺风",
    "竞争强度": "判断拿增长和守利润要付出多大代价",
    "产品管线": "判断后续有没有产品可以接棒",
    "长线运营": "判断产品热度能不能维持更久",
    "ROI": "判断投放花出去的钱能不能收回来",
    "区域兑现": "判断海外动作能不能真正变成收入",
    "经营抓手": "判断管理动作有没有落成可执行的事情",
}


def compose_report(context: dict[str, Any], llm_client: LLMClient | None) -> dict[str, Any]:
    return final_report_composer(context=context, llm_client=llm_client)


def final_report_composer(context: dict[str, Any], llm_client: LLMClient | None) -> dict[str, Any]:
    del llm_client

    query = context.get("user_query") or context.get("query", "")
    profile = _profile(context.get("preference_profile", {}))
    score_breakdown = score_to_judgment_rewriter(context.get("score_dimension_outputs", []), context.get("risk", {}))
    expert_modules = expert_voice_adapter(
        context.get("analysis_results", []),
        query=query,
        profile=profile,
        score_breakdown=score_breakdown,
    )
    risk_opportunities = risk_opportunity_rewriter(
        score_breakdown=score_breakdown,
        expert_modules=expert_modules,
        strict=profile["evidence_strictness"] == "strict",
    )
    verification_notes = _verification_focus(
        context.get("validation_outputs", []),
        score_breakdown=score_breakdown,
        expert_modules=expert_modules,
        strict=profile["evidence_strictness"] == "strict",
    )
    action_items = _action_items(score_breakdown, risk_opportunities, expert_modules, verification_notes)
    next_steps = [_format_action_item(item) for item in action_items]
    key_judgments = _key_judgments(score_breakdown, risk_opportunities, expert_modules, verification_notes)
    key_evidence = _key_evidence(score_breakdown, risk_opportunities, expert_modules)
    sections = body_report_rewriter(
        score_breakdown=score_breakdown,
        expert_modules=expert_modules,
        risk_opportunities=risk_opportunities,
        verification_notes=verification_notes,
        action_items=action_items,
        profile=profile,
    )
    executive_summary = _executive_summary(score_breakdown, risk_opportunities, action_items, profile)
    sections = redundancy_merger(executive_summary, sections)
    all_evidence = _all_evidence(context)

    payload = {
        "cover": {"title": REPORT_TITLE, "company_code": context.get("company_code", ""), "query": query},
        "report_layer": {
            "executive_summary": executive_summary,
            "score_breakdown": score_breakdown,
            "key_judgments": key_judgments,
            "risk_opportunities": risk_opportunities,
            "deep_sections": sections,
            "next_steps": next_steps,
            "action_items": action_items,
        },
        "evidence_layer": {
            "key_evidence": key_evidence,
            "verification_focus": verification_notes,
            "evidence_index": all_evidence[:12],
        },
        "machine_layer": {
            "analysis_plan": context.get("analysis_plan", []),
            "skill_runs": context.get("skill_runs", []),
            "activated_skills": context.get("activated_skills", {}),
            "diagnostics": [
                {"label": "计划主题数", "value": str(len(context.get("analysis_plan", [])))},
                {"label": "执行技能数", "value": str(len(context.get("skill_runs", [])))},
                {"label": "评分维度数", "value": str(len(score_breakdown.get("dimensions", [])))},
                {"label": "待补证据项", "value": str(len(verification_notes))},
            ],
            "routing": context.get("routing", {}),
            "preference_profile": profile,
        },
        "sections": sections,
        "appendix": {
            "analysis_plan": context.get("analysis_plan", []),
            "verification_notes": verification_notes,
            "evidence_index": all_evidence[:12],
            "skill_runs": context.get("skill_runs", []),
            "routing": context.get("routing", {}),
            "preference_profile": profile,
        },
        "summary_cards": _summary_cards(score_breakdown),
        "personalization": {
            "report_style": profile["report_style"],
            "focus_priority": profile["focus_priority"],
            "tone_preference": profile["tone_preference"],
            "summary_first": profile["summary_first"],
            "preferred_output_emphasis": profile["preferred_output_emphasis"],
        },
    }

    compatibility_sections = {
        "conclusion": executive_summary,
        "major_findings": "；".join(item["verdict"] for item in key_judgments[:4]),
        "risk_diagnosis": "；".join(f"{item['title']}：{item['summary']}" for item in risk_opportunities["risks"][:3]),
        "key_evidence": "；".join(f"{item['citation']}：{item['summary']}" for item in key_evidence[:5]),
        "action_suggestions": "；".join(next_steps),
        "industry_custom_analysis": "；".join(section["summary"] for section in sections[1:]),
        "verification_and_gaps": "；".join(item["detail"] for item in verification_notes),
    }

    findings = _dedupe_text(
        [item["verdict"] for item in key_judgments]
        + [item["summary"] for item in risk_opportunities["risks"]]
        + [item["summary"] for item in risk_opportunities["opportunities"]]
    )[:6]

    return {
        "report_title": REPORT_TITLE,
        "summary": executive_summary,
        "findings": findings,
        "recommendations": next_steps,
        "report_sections": compatibility_sections,
        "report_payload": payload,
        "verification_notes": verification_notes,
        "evidence": all_evidence[:8],
    }


def body_report_rewriter(
    *,
    score_breakdown: dict[str, Any],
    expert_modules: list[dict[str, Any]],
    risk_opportunities: dict[str, list[dict[str, Any]]],
    verification_notes: list[dict[str, str]],
    action_items: list[dict[str, str]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    sections.append(_overall_diagnosis_section(score_breakdown, risk_opportunities, expert_modules, verification_notes, action_items))

    for module in _select_body_modules(expert_modules, profile):
        guide = module["guide"]
        related_phrases = _dedupe_text([item.get("summary", "") for item in module.get("related_subitems", [])])[:2]
        chain = reasoning_chain_rewriter(
            lead=_module_lead(module, related_phrases),
            evidence=module.get("evidence", []),
            signals=module.get("findings", []),
            why_key=guide.get("why_key", ""),
            meaning=_module_meaning(module, related_phrases),
            conclusion=_module_conclusion(module, related_phrases),
            impact=guide.get("impact", "经营结果"),
            expert_role=module.get("expert_role", ""),
            core_question=module.get("core_question", ""),
            preferred_terms=module.get("preferred_terms", []),
            pending_check=(module.get("pending_checks") or [""])[0],
        )
        sections.append(
            {
                "key": module["key"],
                "title": module["title"],
                "summary": chain["summary"],
                "body": chain["body"],
                "evidence": module.get("evidence", [])[:3],
                "pending_checks": chain["pending_checks"],
                "expert_role": module.get("expert_role", ""),
                "section_type": "body_module",
            }
        )

    return sections[:MAX_BODY_SECTIONS]


def reasoning_chain_rewriter(
    *,
    lead: str,
    evidence: list[dict[str, Any]],
    signals: list[str],
    why_key: str,
    meaning: str,
    conclusion: str,
    impact: str,
    expert_role: str = "",
    core_question: str = "",
    preferred_terms: list[str] | None = None,
    pending_check: str = "",
) -> dict[str, Any]:
    summary = language_polisher(lead)
    paragraphs: list[str] = []
    evidence_sentence = _evidence_sentence(evidence, signals, why_key)
    if evidence_sentence:
        paragraphs.append(evidence_sentence)

    interpretation_parts: list[str] = []
    if expert_role and core_question:
        interpretation_parts.append(f"从{expert_role}的角度，更关键的问题是：{core_question}")
    terms_sentence = _terms_sentence(preferred_terms or [])
    if terms_sentence:
        interpretation_parts.append(terms_sentence)
    normalized_meaning = _strip_reasoning_prefix(
        meaning,
        prefixes=(
            "这表明",
            "这说明",
            "这本质上是在回答",
        ),
    )
    normalized_conclusion = _strip_reasoning_prefix(
        conclusion,
        prefixes=(
            "因此当前更合理的判断是",
            "因此现阶段更合理的结论是",
            "当前更合理的判断是",
            "现阶段更合理的结论是",
            "更合理的结论是",
        ),
    )
    interpretation_parts.append(f"这些信号说明{normalized_meaning}，因此当前更合理的判断是{normalized_conclusion}，它会首先影响{impact}。")
    paragraphs.append(language_polisher(" ".join(part for part in interpretation_parts if part)))

    pending_checks: list[str] = []
    if pending_check:
        pending_text = language_polisher(f"仍需补看{pending_check}，因为这会直接决定对{impact}的判断能否进一步增强。")
        pending_checks.append(pending_text)
        paragraphs.append(pending_text)

    return {
        "summary": summary,
        "body": [paragraph for paragraph in _dedupe_text(paragraphs) if not _duplicate(paragraph, summary)],
        "pending_checks": pending_checks,
    }


def score_to_judgment_rewriter(score_dimensions: list[dict[str, Any]], risk: dict[str, Any]) -> dict[str, Any]:
    transformed_dimensions = [_rewrite_dimension(item) for item in score_dimensions]
    total_score = int(risk.get("total_score", sum(item.get("score", 0) for item in transformed_dimensions)))
    total_score = max(0, min(100, total_score))
    return {
        "total_score": total_score,
        "risk_level": risk.get("risk_level") or _risk_level(total_score),
        "overall_state": _overall_state(total_score),
        "top_deductions": _top_deductions(transformed_dimensions),
        "score_note": "这份评分反映的是当前披露口径下的经营体检，不等于企业长期价值的终局判断；关键还是看后续现金回流、增长承接和执行兑现能否继续验证。",
        "dimensions": transformed_dimensions,
    }


def risk_opportunity_rewriter(
    *,
    score_breakdown: dict[str, Any],
    expert_modules: list[dict[str, Any]],
    strict: bool,
) -> dict[str, list[dict[str, Any]]]:
    risks: list[dict[str, Any]] = []
    opportunities: list[dict[str, Any]] = []

    negative_candidates: list[dict[str, Any]] = []
    positive_candidates: list[dict[str, Any]] = []
    for dimension in score_breakdown.get("dimensions", []):
        for sub in dimension.get("sub_scores", []):
            ratio = sub["score"] / max(sub["max_score"], 1)
            candidate = {"dimension": dimension, "sub": sub, "ratio": ratio}
            if sub.get("_polarity") == "negative" or ratio <= 0.52:
                negative_candidates.append(candidate)
            elif sub.get("_polarity") == "positive" or ratio >= 0.75:
                positive_candidates.append(candidate)

    negative_candidates.sort(key=lambda item: (item["ratio"], item["sub"]["max_score"]))
    positive_candidates.sort(key=lambda item: (item["ratio"], item["sub"]["max_score"]), reverse=True)

    for candidate in negative_candidates[:2]:
        sub = candidate["sub"]
        guide = sub.get("_guide") or _subitem_guide(sub.get("key", ""))
        evidence = sub.get("evidence_refs", [])[:2]
        risks.append(
            {
                "title": guide["risk_title"],
                "summary": sub.get("summary", guide["negative"]),
                "basis": _basis(evidence, guide["importance"]),
                "impact": language_polisher(f"如果这一点迟迟不能改善，会先压制{guide['impact']}。"),
                "follow_up": guide["focus"],
                "tone": "risk",
                "evidence": evidence,
                "action_profile": {
                    "action": guide["action"],
                    "purpose": guide["purpose"],
                    "focus": guide["focus"],
                    "importance": guide["why_important"],
                },
            }
        )

    for candidate in positive_candidates[:2]:
        sub = candidate["sub"]
        guide = sub.get("_guide") or _subitem_guide(sub.get("key", ""))
        evidence = sub.get("evidence_refs", [])[:2]
        opportunities.append(
            {
                "title": guide["opportunity_title"],
                "summary": sub.get("summary", guide["positive"]),
                "basis": _basis(evidence, guide["importance"]),
                "impact": language_polisher(f"如果这一点继续兑现，会改善{guide['impact']}。"),
                "follow_up": guide["focus"],
                "tone": "good",
                "evidence": evidence,
                "action_profile": {
                    "action": guide["action"],
                    "purpose": guide["purpose"],
                    "focus": guide["focus"],
                    "importance": guide["why_important"],
                },
            }
        )

    for module in expert_modules:
        if len(risks) < 3 and module["tone"] == "risk":
            risks.append(_module_risk_or_opportunity(module, tone="risk"))
        if len(opportunities) < 2 and module["tone"] == "good":
            opportunities.append(_module_risk_or_opportunity(module, tone="good"))

    if strict:
        risks = [item for item in risks if item.get("evidence")]
        opportunities = [item for item in opportunities if item.get("evidence")]

    return {"risks": _dedupe_items(risks, 3), "opportunities": _dedupe_items(opportunities, 2)}


def redundancy_merger(executive_summary: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary_sentences = [item for item in re.split(r"[。！？；\n]+", executive_summary or "") if item.strip()]
    seen_sentences = list(summary_sentences)
    cleaned_sections: list[dict[str, Any]] = []

    for section in sections:
        new_section = dict(section)
        summary = language_polisher(section.get("summary", ""))
        if any(_duplicate(summary, sentence) for sentence in summary_sentences):
            summary = ""

        body: list[str] = []
        for paragraph in section.get("body", []):
            polished = language_polisher(paragraph)
            if not polished:
                continue
            if summary and _duplicate(polished, summary):
                continue
            if any(_duplicate(polished, existing) for existing in body):
                continue
            if any(_duplicate(polished, sentence) for sentence in seen_sentences):
                continue
            body.append(polished)

        if summary and any(_duplicate(summary, sentence) for sentence in seen_sentences):
            summary = ""

        new_section["summary"] = summary
        new_section["body"] = body
        new_section["pending_checks"] = _dedupe_text([language_polisher(item) for item in section.get("pending_checks", [])])
        if summary:
            seen_sentences.append(summary)
        seen_sentences.extend(body)
        cleaned_sections.append(new_section)

    return cleaned_sections


def language_polisher(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    replacements = {
        "当前更适合作为约束项持续跟踪": "当前更像需要保留的约束条件",
        "按中性偏保守口径处理": "暂时按偏谨慎口径理解",
        "专项会直接影响本次报告判断强度": "是这次判断里需要单独看清的一环",
        "负向信号数量高于改善信号": "承压线索目前仍多于改善线索",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)

    for fragment in BANNED_TEXT_FRAGMENTS:
        cleaned = cleaned.replace(fragment, "")

    cleaned = re.sub(r"\b[A-Za-z]+Skill\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[；;]{2,}", "；", cleaned)
    cleaned = re.sub(r"[。]{2,}", "。", cleaned)
    cleaned = cleaned.strip(" ；;。")
    return cleaned + ("。" if cleaned and not cleaned.endswith(("。", "！", "？")) else "")


def expert_voice_adapter(
    analysis_results: list[dict[str, Any]],
    *,
    query: str,
    profile: dict[str, Any],
    score_breakdown: dict[str, Any],
) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    subitem_index = _subitem_index(score_breakdown)

    for item in analysis_results:
        outputs = item.get("outputs", [])
        if not outputs:
            continue

        subtask = item.get("subtask", {})
        key = subtask.get("key", "topic")
        guide = ASPECT_GUIDES.get(key, _fallback_aspect_guide(key, subtask.get("title", "专题分析")))
        primary_output = _primary_output(outputs)
        expert_profile = primary_output.get("expert_profile") or {}
        evidence = _evidence_refs(
            select_ranked_evidence(
                (item.get("evidence_pack") or {}).get("items", []),
                keywords=(query, subtask.get("title", ""), subtask.get("aspect", ""), key),
                limit=3,
            )
        )
        output_evidence = _evidence_refs([ref for output in outputs for ref in output.get("evidence_refs", [])])
        merged_evidence = dedupe_evidence(output_evidence + evidence, limit=4)
        findings = _dedupe_text([finding for output in outputs for finding in output.get("findings", [])])
        recommendations = _dedupe_text([rec for output in outputs for rec in output.get("recommendations", [])])
        pending_checks = _dedupe_text([check for output in outputs for check in output.get("pending_checks", [])])
        related_subitems = [subitem_index[sub_key] for sub_key in guide.get("related_subitems", []) if sub_key in subitem_index]
        tone = _module_tone(primary_output.get("summary", ""), findings, recommendations)
        importance = _module_importance(
            key=key,
            evidence_count=len(merged_evidence),
            confidence=float(primary_output.get("confidence", 0)),
            tone=tone,
            profile=profile,
            related_subitems=related_subitems,
        )

        modules.append(
            {
                "key": key,
                "title": guide["title"],
                "guide": guide,
                "summary": language_polisher(primary_output.get("summary", "")),
                "findings": findings,
                "recommendations": recommendations,
                "pending_checks": pending_checks,
                "expert_role": expert_profile.get("expert_role") or guide.get("expert_role", ""),
                "core_question": (expert_profile.get("core_questions") or [""])[0],
                "preferred_terms": expert_profile.get("preferred_terms") or [],
                "evidence": merged_evidence,
                "confidence": float(primary_output.get("confidence", 0)),
                "tone": tone,
                "importance": importance,
                "domain_group": guide.get("domain_group", "other"),
                "related_subitems": related_subitems,
            }
        )

    modules.sort(key=lambda item: item["importance"], reverse=True)
    return modules


def _profile(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_style": raw.get("report_style", "standard"),
        "focus_priority": raw.get("focus_priority", "balanced"),
        "preferred_topics": list(raw.get("preferred_topics", [])),
        "tone_preference": raw.get("tone_preference", "readable_briefing"),
        "summary_first": bool(raw.get("summary_first", True)),
        "evidence_strictness": raw.get("evidence_strictness", "standard"),
        "preferred_output_emphasis": list(raw.get("preferred_output_emphasis", [])),
    }


def _rewrite_dimension(item: dict[str, Any]) -> dict[str, Any]:
    transformed_sub_scores = [_rewrite_subscore(sub, item.get("dimension_key", "")) for sub in item.get("sub_scores", [])]
    ratio = int(item.get("score", 0)) / max(int(item.get("max_score", 1)), 1)
    label = DIMENSION_DISPLAY_LABELS.get(item.get("dimension_key", ""), item.get("dimension_label", "维度"))
    negative_points = [sub["summary"] for sub in transformed_sub_scores if sub.get("_polarity") == "negative"][:2]
    positive_points = [sub["summary"] for sub in transformed_sub_scores if sub.get("_polarity") == "positive"][:2]

    if negative_points and ratio < 0.6:
        summary = f"{label}是当前结论里最需要谨慎看的部分，压力主要集中在{negative_points[0].rstrip('。')}。"
    elif positive_points and ratio >= 0.75:
        summary = f"{label}目前相对稳，最主要的支撑来自{positive_points[0].rstrip('。')}。"
    elif negative_points and positive_points:
        summary = f"{label}同时存在修复和约束，现阶段更像边改善边验证，尤其要看{negative_points[0].rstrip('。')}。"
    elif positive_points:
        summary = f"{label}暂未看到明显失衡，已有一定支撑，但还需要继续验证持续性。"
    else:
        summary = f"{label}暂时没有明显改善或恶化的确定性信号，判断仍以谨慎为主。"

    return {
        "dimension_key": item.get("dimension_key", ""),
        "dimension_label": label,
        "score": int(item.get("score", 0)),
        "max_score": int(item.get("max_score", 0)),
        "summary": language_polisher(summary),
        "positive_factors": positive_points,
        "negative_factors": negative_points,
        "uncertainty_flags": _dedupe_text(item.get("uncertainty_flags", [])),
        "sub_scores": transformed_sub_scores,
        "evidence_refs": _evidence_refs(item.get("evidence_refs", [])),
    }


def _rewrite_subscore(sub: dict[str, Any], dimension_key: str) -> dict[str, Any]:
    guide = _subitem_guide(sub.get("key", ""))
    ratio = int(sub.get("score", 0)) / max(int(sub.get("max_score", 1)), 1)
    polarity = sub.get("polarity", "")
    if sub.get("uncertainty"):
        summary = f"关于{guide['label']}的直接证据还不够，暂时只能把它当成待验证变量。"
        reason = "目前缺少足够直接的披露，不宜下更强判断。"
        polarity = "neutral"
    elif polarity == "positive" or ratio >= 0.75:
        summary = guide["positive"]
        reason = guide["importance"]
        polarity = "positive"
    elif polarity == "negative" or ratio <= 0.52:
        summary = guide["negative"]
        reason = guide["importance"]
        polarity = "negative"
    else:
        summary = guide["neutral"]
        reason = guide["importance"]
        polarity = "neutral"

    return {
        "key": sub.get("key", ""),
        "label": guide["label"],
        "score": int(sub.get("score", 0)),
        "max_score": int(sub.get("max_score", 0)),
        "reason": language_polisher(reason),
        "summary": language_polisher(summary),
        "uncertainty": bool(sub.get("uncertainty", False)),
        "follow_up": guide["focus"],
        "evidence_refs": _evidence_refs(sub.get("evidence_refs", [])),
        "_guide": guide,
        "_polarity": polarity,
        "_dimension_key": dimension_key,
    }


def _top_deductions(dimensions: list[dict[str, Any]]) -> list[str]:
    candidates: list[tuple[float, str]] = []
    for dimension in dimensions:
        for sub in dimension.get("sub_scores", []):
            ratio = sub["score"] / max(sub["max_score"], 1)
            if sub.get("_polarity") == "negative" or ratio <= 0.52:
                candidates.append((ratio, sub.get("_guide", {}).get("risk_title", sub.get("summary", ""))))
    candidates.sort(key=lambda item: item[0])
    return _dedupe_text([item[1] for item in candidates])[:3] or ["当前未识别出明确的集中约束项。"]


def _overall_state(score: int) -> str:
    if score >= 80:
        return "经营状态整体稳健"
    if score >= 60:
        return "经营基本盘稳定，但仍有关键约束"
    if score >= 40:
        return "修复与约束并存"
    if score >= 20:
        return "多个关键环节仍然偏弱"
    return "经营承压较为明显"


def _risk_level(score: int) -> str:
    if score >= 80:
        return "低风险"
    if score >= 60:
        return "中低风险"
    if score >= 40:
        return "中风险"
    if score >= 20:
        return "中高风险"
    return "高风险"


def _module_lead(module: dict[str, Any], related_phrases: list[str]) -> str:
    if module["tone"] == "risk" and related_phrases:
        return f"{module['title']}是当前判断里需要重点看清的一环。就现有披露看，{related_phrases[0].rstrip('。')}。"
    if module["tone"] == "good" and related_phrases:
        return f"{module['title']}目前保留了相对积极的支撑。核心原因在于{related_phrases[0].rstrip('。')}。"
    if module.get("summary"):
        return f"{module['title']}当前最重要的判断是：{module['summary'].rstrip('。')}。"
    return f"{module['title']}当前仍处在需要重点解释的观察区间。"


def _module_meaning(module: dict[str, Any], related_phrases: list[str]) -> str:
    if related_phrases:
        return f"这表明{module['guide']['business_question']}，而不是只看表面上的单个指标变化"
    return f"这本质上是在回答{module['guide']['business_question']}"


def _module_conclusion(module: dict[str, Any], related_phrases: list[str]) -> str:
    if module["tone"] == "risk":
        return f"{(related_phrases[:1] or ['这一部分'])[0].rstrip('。')}仍然更像约束项而不是支撑项"
    if module["tone"] == "good":
        return f"{(related_phrases[:1] or ['这一部分'])[0].rstrip('。')}已经提供了可验证的支撑"
    return f"这部分尚未形成单边趋势，更适合继续围绕{module['guide']['impact']}验证"


def _overall_diagnosis_section(
    score_breakdown: dict[str, Any],
    risk_opportunities: dict[str, list[dict[str, Any]]],
    expert_modules: list[dict[str, Any]],
    verification_notes: list[dict[str, str]],
    action_items: list[dict[str, str]],
) -> dict[str, Any]:
    risk_item = (risk_opportunities.get("risks") or [{}])[0]
    opportunity_item = (risk_opportunities.get("opportunities") or [{}])[0]
    evidence = dedupe_evidence([ref for module in expert_modules[:2] for ref in module.get("evidence", [])], limit=3)
    lead = f"整体看，公司目前处在“{score_breakdown.get('overall_state', '')}”阶段。"
    if risk_item.get("title"):
        lead += f" 当前压制判断上限的核心约束来自“{risk_item['title']}”。"
    if opportunity_item.get("title"):
        lead += f" 但“{opportunity_item['title']}”说明公司并非没有支撑。"

    meaning = f"当前最需要确认的是：{action_items[0]['purpose']}" if action_items else "当前最需要确认的，不是有没有改善迹象，而是改善能不能继续盖过约束"
    conclusion = f"因此现阶段更合理的结论是，公司仍有修复基础，但判断上限暂时受限于{risk_item.get('title', '关键约束')}"
    chain = reasoning_chain_rewriter(
        lead=lead,
        evidence=evidence,
        signals=[risk_item.get("summary", ""), opportunity_item.get("summary", "")],
        why_key="这组信号值得重视，因为它说明公司不是单向改善或单向恶化，而是处在分化修复阶段。",
        meaning=meaning,
        conclusion=conclusion,
        impact="收入、利润、现金流和增长持续性",
        pending_check=(verification_notes[0]["detail"] if verification_notes else ""),
    )
    return {
        "key": "overall_diagnosis",
        "title": "综合判断",
        "summary": chain["summary"],
        "body": chain["body"],
        "evidence": evidence,
        "pending_checks": chain["pending_checks"],
        "expert_role": "",
        "section_type": "overall",
    }


def _verification_focus(
    validation_outputs: list[dict[str, Any]],
    *,
    score_breakdown: dict[str, Any],
    expert_modules: list[dict[str, Any]],
    strict: bool,
) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    for output in validation_outputs:
        title = output.get("skill_name", "待补核验")
        for pending in output.get("pending_checks", [])[:1]:
            cleaned = language_polisher(pending)
            if cleaned:
                notes.append({"severity": "warn", "title": title, "detail": cleaned})
    for dimension in score_breakdown.get("dimensions", []):
        for sub in dimension.get("sub_scores", []):
            if sub.get("uncertainty"):
                guide = sub.get("_guide") or _subitem_guide(sub.get("key", ""))
                notes.append({"severity": "warn", "title": dimension["dimension_label"], "detail": language_polisher(f"还需要补看{guide['focus']}，否则很难判断{guide['impact']}是否真的在改善。")})
        if strict and not dimension.get("evidence_refs"):
            notes.append({"severity": "warn", "title": dimension["dimension_label"], "detail": language_polisher(f"{dimension['dimension_label']}目前缺少更强的直接披露，结论仍需保守。")})
    for module in expert_modules:
        if module.get("pending_checks"):
            notes.append({"severity": "warn", "title": module["title"], "detail": language_polisher(f"仍需补看{module['pending_checks'][0]}，这会直接影响“{module['title']}”的判断强度。")})

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in notes:
        key = (item["title"], item["detail"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:3]


def _key_judgments(
    score_breakdown: dict[str, Any],
    risk_opportunities: dict[str, list[dict[str, Any]]],
    expert_modules: list[dict[str, Any]],
    verification_notes: list[dict[str, str]],
) -> list[dict[str, Any]]:
    judgments = [{
        "title": "总体判断",
        "verdict": f"公司当前总分为 {score_breakdown['total_score']}/100，整体处在“{score_breakdown['overall_state']}”阶段。",
        "explanation": "这不是单点改善或单点承压可以解释的状态，而是多个关键环节同时在修复与约束之间拉扯。",
        "confidence": "中高",
        "tone": _risk_tone(score_breakdown["risk_level"]),
        "evidence_anchors": [],
    }]
    if risk_opportunities.get("risks"):
        top_risk = risk_opportunities["risks"][0]
        judgments.append({"title": "最主要约束", "verdict": top_risk["title"], "explanation": language_polisher(f"{top_risk['summary']} {top_risk['impact']}"), "confidence": "中", "tone": "risk", "evidence_anchors": [evidence_citation(item) for item in top_risk.get("evidence", [])[:2]]})
    if risk_opportunities.get("opportunities"):
        top_opportunity = risk_opportunities["opportunities"][0]
        judgments.append({"title": "最重要支撑", "verdict": top_opportunity["title"], "explanation": language_polisher(f"{top_opportunity['summary']} {top_opportunity['impact']}"), "confidence": "中", "tone": "good", "evidence_anchors": [evidence_citation(item) for item in top_opportunity.get("evidence", [])[:2]]})
    if verification_notes:
        judgments.append({"title": "当前最需要核实", "verdict": verification_notes[0]["detail"], "explanation": "这不是边角信息，而是会影响结论能否进一步增强的关键缺口。", "confidence": "中", "tone": "warn", "evidence_anchors": []})
    elif expert_modules:
        module = expert_modules[0]
        judgments.append({"title": "优先展开的议题", "verdict": module["title"], "explanation": module.get("summary", ""), "confidence": "中", "tone": module.get("tone", "neutral"), "evidence_anchors": [evidence_citation(item) for item in module.get("evidence", [])[:2]]})
    return judgments[:4]


def _key_evidence(score_breakdown: dict[str, Any], risk_opportunities: dict[str, list[dict[str, Any]]], expert_modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    digests: list[dict[str, Any]] = []
    for item in (risk_opportunities.get("risks") or [])[:2] + (risk_opportunities.get("opportunities") or [])[:2]:
        if item.get("evidence"):
            evidence = item["evidence"][0]
            digests.append({"title": item["title"], "summary": language_polisher(summarize_evidence(evidence)), "supports": language_polisher(item["summary"]), "citation": evidence_citation(evidence), "evidence": [evidence]})
    for module in expert_modules[:2]:
        if module.get("evidence"):
            evidence = module["evidence"][0]
            digests.append({"title": module["title"], "summary": language_polisher(summarize_evidence(evidence)), "supports": language_polisher(module.get("summary", "")), "citation": evidence_citation(evidence), "evidence": [evidence]})
    for dimension in score_breakdown.get("dimensions", [])[:2]:
        if dimension.get("evidence_refs"):
            evidence = dimension["evidence_refs"][0]
            digests.append({"title": dimension["dimension_label"], "summary": language_polisher(summarize_evidence(evidence)), "supports": language_polisher(dimension.get("summary", "")), "citation": evidence_citation(evidence), "evidence": [evidence]})
    return _dedupe_items(digests, 6)


def _action_items(
    score_breakdown: dict[str, Any],
    risk_opportunities: dict[str, list[dict[str, Any]]],
    expert_modules: list[dict[str, Any]],
    verification_notes: list[dict[str, str]],
) -> list[dict[str, str]]:
    del score_breakdown
    items: list[dict[str, str]] = []
    for item in risk_opportunities.get("risks", [])[:1] + risk_opportunities.get("opportunities", [])[:1]:
        profile = item.get("action_profile") or {}
        if profile:
            items.append({"action": profile.get("action", ""), "purpose": profile.get("purpose", ""), "focus": profile.get("focus", ""), "importance": profile.get("importance", "")})
    for module in expert_modules:
        if len(items) >= 3:
            break
        if module.get("recommendations"):
            guide = module["guide"]
            items.append({"action": module["recommendations"][0].rstrip("。"), "purpose": f"把“{guide['title']}”对应的判断进一步做实", "focus": guide.get("impact", ""), "importance": language_polisher(guide.get("why_key", ""))})
    if verification_notes and len(items) < 3:
        items.append({"action": verification_notes[0]["detail"].replace("仍需", "补看").replace("还需要", "补看").rstrip("。"), "purpose": "补齐当前最影响结论强度的证据缺口", "focus": verification_notes[0]["title"], "importance": "证据缺口补齐后，关键判断才能从谨慎表述升级为更明确结论。"})

    cleaned: list[dict[str, str]] = []
    seen_actions: set[str] = set()
    for item in items:
        action = language_polisher(item.get("action", "")).rstrip("。")
        if action and action not in seen_actions:
            seen_actions.add(action)
            cleaned.append({"action": action, "purpose": language_polisher(item.get("purpose", "")), "focus": language_polisher(item.get("focus", "")), "importance": language_polisher(item.get("importance", ""))})
    return cleaned[:3]


def _executive_summary(
    score_breakdown: dict[str, Any],
    risk_opportunities: dict[str, list[dict[str, Any]]],
    action_items: list[dict[str, str]],
    profile: dict[str, Any],
) -> str:
    parts = [f"结论先行：公司当前总分 {score_breakdown['total_score']}/100，风险等级为 {score_breakdown['risk_level']}，整体处在“{score_breakdown['overall_state']}”阶段。"]
    if risk_opportunities.get("risks"):
        parts.append(f"当前最需要警惕的是“{risk_opportunities['risks'][0]['title']}”，因为{risk_opportunities['risks'][0]['summary'].rstrip('。')}。")
    if risk_opportunities.get("opportunities"):
        parts.append(f"同时，“{risk_opportunities['opportunities'][0]['title']}”说明公司并非没有支撑，关键在于后续能否继续兑现。")
    if action_items:
        parts.append(f"下一步最优先的动作是：{action_items[0]['action']}。")
    if profile["tone_preference"] == "investment_research":
        parts.append("从投资研究视角看，真正要确认的是这轮修复能否转化为更稳的风险收益比。")
    elif profile["tone_preference"] == "management_diagnosis":
        parts.append("从经营诊断视角看，核心是判断管理动作和业务承接是否已经形成闭环。")

    limit = 160 if profile["report_style"] == "concise" else 240 if profile["report_style"] == "standard" else 320
    return _build_limited_summary(parts, limit=limit)


def _summary_cards(score_breakdown: dict[str, Any]) -> list[dict[str, str]]:
    cards = [{"label": "总分", "value": str(score_breakdown["total_score"])}, {"label": "风险等级", "value": score_breakdown["risk_level"]}]
    for dimension in score_breakdown.get("dimensions", []):
        cards.append({"label": dimension["dimension_label"], "value": f"{dimension['score']} / {dimension['max_score']}"})
    return cards


def _module_risk_or_opportunity(module: dict[str, Any], *, tone: str) -> dict[str, Any]:
    follow_up = module.get("recommendations", [""])
    guide = module["guide"]
    return {
        "title": module["title"],
        "summary": module.get("summary", ""),
        "basis": _basis(module.get("evidence", [])[:2], guide.get("why_key", "")),
        "impact": language_polisher(f"这会直接影响{guide.get('impact', '经营结果')}。"),
        "follow_up": follow_up[0] if follow_up else "",
        "tone": "risk" if tone == "risk" else "good",
        "evidence": module.get("evidence", [])[:2],
        "action_profile": {"action": follow_up[0] if follow_up else guide.get("title", ""), "purpose": f"把“{guide['title']}”对应的判断继续做实", "focus": guide.get("impact", ""), "importance": guide.get("why_key", "")},
    }


def _format_action_item(item: dict[str, str]) -> str:
    return language_polisher(f"{item['action']}。目的：{item['purpose']}。重点看：{item['focus']}。为什么重要：{item['importance']}")


def _select_body_modules(expert_modules: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_groups: set[str] = set()
    limit = 3 if profile["report_style"] != "deep" else 4
    for module in expert_modules:
        group = module.get("domain_group", "other")
        if group not in seen_groups or len(selected) < 2:
            selected.append(module)
            seen_groups.add(group)
        if len(selected) >= limit:
            break
    if len(selected) < min(limit, len(expert_modules)):
        for module in expert_modules:
            if module not in selected:
                selected.append(module)
            if len(selected) >= limit:
                break
    return selected[:limit]


def _module_importance(*, key: str, evidence_count: int, confidence: float, tone: str, profile: dict[str, Any], related_subitems: list[dict[str, Any]]) -> int:
    importance = evidence_count * 4 + round(confidence * 10)
    if tone == "risk":
        importance += 3
    if key in _focus_aspects(profile["focus_priority"]):
        importance += 4
    if any(sub.get("_polarity") == "negative" for sub in related_subitems):
        importance += 2
    if any(sub.get("_polarity") == "positive" for sub in related_subitems):
        importance += 1
    return importance


def _focus_aspects(focus_priority: str) -> set[str]:
    if focus_priority == "finance_first":
        return {"financial_health", "earnings_quality", "cashflow_health", "marketing_efficiency"}
    if focus_priority == "growth_first":
        return {"growth_continuity", "product_business_structure", "product_pipeline", "operation_performance", "product_lifecycle"}
    if focus_priority == "risk_first":
        return {"financial_health", "governance_compliance", "regulation_publishing", "industry_competition"}
    return set()


def _module_tone(summary: str, findings: list[str], recommendations: list[str]) -> str:
    return _tone(" ".join([summary] + findings + recommendations))


def _primary_output(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    return max(outputs, key=lambda item: (float(item.get("confidence", 0)), len(item.get("evidence_refs", [])), len(item.get("findings", []))))


def _subitem_index(score_breakdown: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {sub["key"]: sub for dimension in score_breakdown.get("dimensions", []) for sub in dimension.get("sub_scores", [])}


def _subitem_guide(key: str) -> dict[str, str]:
    return SUBITEM_GUIDES.get(key, {"label": key or "关键环节", "risk_title": "这一环节仍存在明显约束", "opportunity_title": "这一环节保留一定支撑", "negative": "这一环节当前仍需谨慎看待。", "positive": "这一环节当前有一定支撑。", "neutral": "这一环节仍处在观察区间。", "importance": "这类信号会直接影响经营判断强度。", "impact": "经营结果", "action": "补看这一环节的直接材料", "purpose": "确认这一环节是否正在改善", "focus": "相关披露和关键指标", "why_important": "它会直接影响结论强度。"})


def _fallback_aspect_guide(key: str, title: str) -> dict[str, Any]:
    return {"title": title or key or "专题分析", "domain_group": "other", "impact": "经营结果", "business_question": "这一主题会如何影响经营判断", "why_key": "这部分之所以重要，是因为它会直接影响对公司经营状态的理解。", "related_subitems": []}


def _evidence_sentence(evidence: list[dict[str, Any]], signals: list[str], why_key: str) -> str:
    citations = _format_citations(evidence, limit=2)
    signal_text = _signal_text(signals)
    if evidence:
        text = f"证据主要来自{citations}。相关披露显示{summarize_evidence(evidence[0])}"
        if signal_text:
            text += f"，并且可以和“{signal_text}”互相印证"
        text += f"。{why_key}"
        return language_polisher(text)
    if signal_text:
        return language_polisher(f"现有信号主要表现为“{signal_text}”。{why_key}")
    return language_polisher(why_key)


def _basis(items: list[dict[str, Any]], importance: str) -> str:
    if not items:
        return language_polisher("当前还缺少足够直接的披露，需要补看更强材料后再下更重结论。")
    return language_polisher(f"证据主要来自{_format_citations(items, limit=2)}。相关披露显示{summarize_evidence(items[0])}。{importance}")


def _signal_text(signals: list[str]) -> str:
    cleaned = [language_polisher(item).rstrip("。") for item in signals if item]
    return "；".join(_dedupe_text(cleaned[:2])) if cleaned else ""


def _format_citations(items: list[dict[str, Any]], *, limit: int = 2) -> str:
    citations = [evidence_citation(item) for item in items[:limit] if item]
    citations = [item for item in citations if item]
    if not citations:
        return "相关披露"
    return citations[0] if len(citations) == 1 else "、".join(citations)


def _terms_sentence(preferred_terms: list[str]) -> str:
    parts = []
    for term in preferred_terms[:2]:
        explanation = TERM_EXPLANATIONS.get(term)
        parts.append(f"{term}用来{explanation}" if explanation else term)
    if not parts:
        return ""
    return f"这里更看重{parts[0]}" if len(parts) == 1 else f"这里更看重{parts[0]}，也会结合{parts[1]}"


def _all_evidence(context: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    values.extend((context.get("evidence_pack") or {}).get("items") or [])
    for item in context.get("analysis_results", []):
        values.extend((item.get("evidence_pack") or {}).get("items") or [])
    return dedupe_evidence(_evidence_refs(values), limit=20)


def _evidence_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_evidence([to_evidence_ref(item) for item in items if item], limit=None)


def _dedupe_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    for item in items:
        if any(_duplicate(item.get("title", ""), existing.get("title", "")) or _duplicate(item.get("summary", ""), existing.get("summary", "")) for existing in deduped):
            continue
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def _dedupe_text(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        cleaned = (value or "").strip()
        if cleaned and not any(_duplicate(cleaned, existing) for existing in deduped):
            deduped.append(cleaned)
    return deduped


def _build_limited_summary(parts: list[str], *, limit: int) -> str:
    summary = ""
    for part in _dedupe_text(parts):
        polished = language_polisher(part)
        if not polished:
            continue
        candidate = polished if not summary else f"{summary} {polished}"
        if len(candidate) > limit:
            break
        summary = candidate

    if summary:
        return summary

    fallback = language_polisher(" ".join(_dedupe_text(parts)))
    if len(fallback) <= limit:
        return fallback
    return fallback[:limit].rstrip("，；。") + "。"


def _strip_reasoning_prefix(text: str, *, prefixes: tuple[str, ...]) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    while cleaned:
        updated = cleaned
        for prefix in prefixes:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].lstrip("：， ")
        if cleaned == updated:
            break
    return cleaned


def _duplicate(left: str, right: str) -> bool:
    l = _duplicate_key(left)
    r = _duplicate_key(right)
    if not l or not r:
        return False
    if l == r or l in r or r in l:
        return True
    return SequenceMatcher(None, l, r).ratio() >= SUMMARY_SIMILARITY_THRESHOLD


def _duplicate_key(text: str) -> str:
    normalized = re.sub(r"\s+", "", text or "").lower()
    return re.sub(r"[，。！？；：、,.;:!?\"'“”‘’（）()《》【】\[\]<>]", "", normalized)


def _tone(text: str) -> str:
    if any(token in text for token in ("风险", "承压", "不足", "拖累", "下滑", "恶化", "减值", "波动", "压力")):
        return "risk"
    if any(token in text for token in ("改善", "增长", "提升", "修复", "机会", "回暖", "稳健", "支撑")):
        return "good"
    return "neutral"


def _risk_tone(level: str) -> str:
    if "高风险" in level:
        return "risk"
    if "中" in level:
        return "warn"
    return "good"
