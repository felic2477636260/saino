from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class AnalysisSubtask:
    key: str
    title: str
    goal: str
    aspect: str
    query_focus: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


SUBTASK_LIBRARY: dict[str, dict[str, str]] = {
    "overview": {
        "title": "材料概览与公司画像",
        "goal": "梳理分析覆盖范围、核心材料来源、业务轮廓和研究边界。",
        "focus": "公司概况 核心业务 管理层讨论 风险因素",
    },
    "financial_health": {
        "title": "财务与经营健康度",
        "goal": "围绕收入、利润、现金流与债务压力判断经营稳健度。",
        "focus": "营收 利润 现金流 负债 成本 费用 经营表现",
    },
    "governance_compliance": {
        "title": "治理与合规观察",
        "goal": "识别治理、内控、监管与重大合规约束。",
        "focus": "治理 合规 内控 监管 诉讼 风险",
    },
    "cashflow_health": {
        "title": "现金流与偿债专项",
        "goal": "判断现金流质量、流动性安全边际与偿债压力。",
        "focus": "经营现金流 回款 偿债 融资 资金安全 流动性",
    },
    "earnings_quality": {
        "title": "盈利质量专项",
        "goal": "判断利润修复质量、利润结构和盈利持续性。",
        "focus": "净利润 扣非 毛利率 费用率 盈利质量 利润持续性",
    },
    "growth_continuity": {
        "title": "成长持续性分析",
        "goal": "识别增长来源、承接逻辑和中期持续性。",
        "focus": "增长 成长 持续性 承接 增量 修复",
    },
    "product_business_structure": {
        "title": "产品与业务结构分析",
        "goal": "判断核心业务支撑、结构集中度和业务组合韧性。",
        "focus": "产品线 业务线 收入结构 核心业务 组合 集中度",
    },
    "industry_competition": {
        "title": "行业竞争分析",
        "goal": "识别外部需求环境、竞争格局和公司相对位置。",
        "focus": "行业 竞争 格局 份额 需求 景气 政策",
    },
    "management_execution": {
        "title": "管理层执行力分析",
        "goal": "拆解管理层表述、经营抓手和组织执行约束。",
        "focus": "管理层 执行力 组织 调整 战略 抓手",
    },
    "overseas_business": {
        "title": "海外业务分析",
        "goal": "判断海外业务是否形成真实增量与可复制能力。",
        "focus": "海外 出海 国际 区域 海外收入 发行",
    },
    "product_lifecycle": {
        "title": "产品生命周期分析",
        "goal": "评估老产品衰退、新品承接和周期切换风险。",
        "focus": "生命周期 老产品 新品 承接 衰退 储备",
    },
    "product_pipeline": {
        "title": "产品储备与上线节奏",
        "goal": "分析新品储备、测试进展与上线节奏。",
        "focus": "新品 储备 测试 上线 产品线 进展",
    },
    "operation_performance": {
        "title": "核心产品运营表现",
        "goal": "分析老产品表现、用户活跃与经营改善/承压线索。",
        "focus": "流水 活跃 留存 运营 老产品 承压 改善",
    },
    "regulation_publishing": {
        "title": "版号与发行环境",
        "goal": "识别版号、监管和发行节奏对兑现的影响。",
        "focus": "版号 发行 审批 合规 政策 上线节奏",
    },
    "industry_trend": {
        "title": "行业与技术趋势",
        "goal": "分析行业变化和技术变量对公司经营的影响。",
        "focus": "行业趋势 技术变化 AI 景气 需求 政策",
    },
    "marketing_efficiency": {
        "title": "买量与营销效率",
        "goal": "识别投放效率、营销回收和获客压力。",
        "focus": "买量 营销 投放 销售费用 获客 ROI",
    },
    "overseas_market": {
        "title": "海外市场与区域发行",
        "goal": "识别海外增长与区域市场风险。",
        "focus": "海外 出海 区域市场 国际 发行",
    },
    "ip_dependency": {
        "title": "IP 依赖与内容供给",
        "goal": "判断 IP 依赖、续作供给与内容稳定性。",
        "focus": "IP 授权 续作 内容供给 研发储备",
    },
}


def build_analysis_plan(
    query: str,
    industry: str = "generic",
    selected_aspects: list[str] | None = None,
) -> list[dict[str, str]]:
    normalized_query = (query or "").strip() or "请生成企业体检报告"
    aspects = selected_aspects or _default_aspects(industry)
    plan: list[dict[str, str]] = []

    for aspect in aspects:
        spec = SUBTASK_LIBRARY.get(aspect)
        if not spec:
            continue
        plan.append(
            AnalysisSubtask(
                key=aspect,
                title=spec["title"],
                goal=spec["goal"],
                aspect=aspect,
                query_focus=f"{normalized_query} {spec['focus']}",
            ).to_dict()
        )

    return plan


def _default_aspects(industry: str) -> list[str]:
    aspects = ["overview", "financial_health", "governance_compliance"]
    if (industry or "").strip().lower() == "game":
        aspects.extend(["product_pipeline", "operation_performance", "industry_trend"])
    return aspects
