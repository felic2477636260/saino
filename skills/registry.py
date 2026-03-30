from __future__ import annotations

import logging
from typing import Any

from skills.base import BaseSkill
from skills.custom.game_industry_trend import GameIndustryTrendSkill
from skills.custom.game_ip_supply_stability import GameIPSupplyStabilitySkill
from skills.custom.game_marketing_efficiency import GameMarketingEfficiencySkill
from skills.custom.game_operation_performance import GameOperationPerformanceSkill
from skills.custom.game_overseas_market import GameOverseasMarketSkill
from skills.custom.game_product_pipeline import GameProductPipelineSkill
from skills.custom.game_regulation_publishing import GameRegulationAndPublishingSkill
from skills.enhanced_analysis import (
    CashflowSpecialistSkill,
    EarningsQualitySpecialistSkill,
    GrowthContinuitySkill,
    IndustryCompetitionSkill,
    ManagementExecutionSkill,
    OverseasBusinessSkill,
    ProductBusinessStructureSkill,
    ProductLifecycleSkill,
)
from skills.explain import ExplainSkill
from skills.generic_analysis import CompanyOverviewSkill, FinancialHealthSkill, GovernanceComplianceSkill
from skills.retrieve import RetrieveSkill
from skills.risk_score import RiskScoreSkill
from skills.score_dimensions import (
    BusinessQualityScoreSkill,
    CashflowHealthScoreSkill,
    EarningsQualityScoreSkill,
    IndustryEnvironmentScoreSkill,
)
from skills.validators import ConsistencyCheckSkill, EvidenceGapSkill


logger = logging.getLogger(__name__)


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: list[BaseSkill] = []

    def register(self, skill: BaseSkill) -> None:
        self._skills.append(skill)

    def all(self) -> list[BaseSkill]:
        return list(self._skills)

    def get(self, skill_name: str) -> BaseSkill:
        for skill in self._skills:
            if skill.skill_name == skill_name or skill.id == skill_name:
                return skill
        raise KeyError(f"skill not found: {skill_name}")

    def matching(
        self,
        context: dict[str, Any],
        skill_type: str | None = None,
        skill_category: str | None = None,
        skill_layer: str | None = None,
        allowed_skill_ids: set[str] | None = None,
    ) -> list[BaseSkill]:
        matched: list[BaseSkill] = []
        for skill in self._skills:
            if skill_type and skill.skill_type != skill_type:
                continue
            if skill_category and skill.skill_category != skill_category:
                continue
            if skill_layer and getattr(skill, "skill_layer", None) != skill_layer:
                continue
            if allowed_skill_ids is not None and skill.id not in allowed_skill_ids and skill.skill_name not in allowed_skill_ids:
                continue
            try:
                if skill.match(context):
                    matched.append(skill)
            except Exception as exc:
                logger.exception("skill %s match failed: %s", skill.skill_name, exc)
        matched.sort(key=lambda item: (getattr(item, "priority", 50), item.skill_name), reverse=True)
        return matched

    def describe(self) -> list[dict[str, Any]]:
        return [skill.info() for skill in self._skills]


def build_default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(RetrieveSkill())
    registry.register(RiskScoreSkill())
    registry.register(CompanyOverviewSkill())
    registry.register(FinancialHealthSkill())
    registry.register(GovernanceComplianceSkill())
    registry.register(CashflowSpecialistSkill())
    registry.register(EarningsQualitySpecialistSkill())
    registry.register(GrowthContinuitySkill())
    registry.register(ProductBusinessStructureSkill())
    registry.register(IndustryCompetitionSkill())
    registry.register(ManagementExecutionSkill())
    registry.register(OverseasBusinessSkill())
    registry.register(ProductLifecycleSkill())
    registry.register(GameProductPipelineSkill())
    registry.register(GameOperationPerformanceSkill())
    registry.register(GameRegulationAndPublishingSkill())
    registry.register(GameIndustryTrendSkill())
    registry.register(GameMarketingEfficiencySkill())
    registry.register(GameOverseasMarketSkill())
    registry.register(GameIPSupplyStabilitySkill())
    registry.register(EvidenceGapSkill())
    registry.register(ConsistencyCheckSkill())
    registry.register(BusinessQualityScoreSkill())
    registry.register(EarningsQualityScoreSkill())
    registry.register(CashflowHealthScoreSkill())
    registry.register(IndustryEnvironmentScoreSkill())
    registry.register(ExplainSkill())
    return registry
