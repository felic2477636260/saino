from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field


class PreferenceProfile(BaseModel):
    report_style: Literal["concise", "standard", "deep"] = "standard"
    focus_priority: Literal["risk_first", "growth_first", "finance_first", "balanced"] = "balanced"
    preferred_topics: list[str] = Field(default_factory=list)
    suppressed_topics: list[str] = Field(default_factory=list)
    tone_preference: Literal["investment_research", "management_diagnosis", "readable_briefing"] = "readable_briefing"
    summary_first: bool = True
    evidence_strictness: Literal["strict", "standard", "flexible"] = "standard"
    preferred_output_emphasis: list[str] = Field(default_factory=list)
    domain_hint: str = ""
    user_intent_raw: str = ""
    confidence: float = 0.0


class AnalyzeRequest(BaseModel):
    company_code: str | None = None
    company_name: str | None = None
    query: str = Field(default="请生成企业体检报告")
    preference_note: str = ""
    top_k: int = 8


class AskRequest(BaseModel):
    task_id: str | None = None
    company_code: str | None = None
    question: str
    top_k: int = 5


class EvidenceItem(BaseModel):
    page_no: int
    text: str = Field(validation_alias=AliasChoices("text", "chunk_text"))
    source: str
    section_title: str = ""
    section_path: str = ""
    relevance_score: float = 0
    reason: str = ""
    quote: str = ""
    evidence_type: str = ""
    priority_level: int = 0


class VerificationNote(BaseModel):
    severity: str
    title: str
    detail: str


class ExpertProfile(BaseModel):
    expert_role: str = ""
    domain_focus: str = ""
    core_questions: list[str] = Field(default_factory=list)
    preferred_terms: list[str] = Field(default_factory=list)
    translation_rule: str = ""
    reasoning_style: str = ""


class AnalysisPlanItem(BaseModel):
    key: str
    title: str
    goal: str
    aspect: str
    query_focus: str


class SkillRunItem(BaseModel):
    name: str
    skill_type: str
    skill_category: str
    summary: str
    confidence: float = 0
    evidence_count: int = 0
    findings_count: int = 0
    recommendations_count: int = 0


class StructuredReportSection(BaseModel):
    key: str
    title: str
    summary: str = ""
    body: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    pending_checks: list[str] = Field(default_factory=list)
    expert_role: str = ""
    section_type: str = ""


class ReportJudgment(BaseModel):
    title: str
    verdict: str
    explanation: str = ""
    confidence: str = "medium"
    tone: str = "neutral"
    evidence_anchors: list[str] = Field(default_factory=list)


class RiskOpportunityItem(BaseModel):
    title: str
    summary: str
    basis: str = ""
    impact: str = ""
    follow_up: str = ""
    tone: str = "neutral"
    evidence: list[EvidenceItem] = Field(default_factory=list)


class KeyEvidenceDigest(BaseModel):
    title: str
    summary: str
    supports: str = ""
    citation: str = ""
    evidence: list[EvidenceItem] = Field(default_factory=list)


class RecommendationAction(BaseModel):
    action: str
    purpose: str
    focus: str
    importance: str


class ScoreSubItem(BaseModel):
    key: str
    label: str
    score: int
    max_score: int
    reason: str = ""
    summary: str = ""
    uncertainty: bool = False
    follow_up: str = ""
    evidence_refs: list[EvidenceItem] = Field(default_factory=list)


class ScoreDimension(BaseModel):
    dimension_key: str
    dimension_label: str
    score: int
    max_score: int
    summary: str = ""
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
    sub_scores: list[ScoreSubItem] = Field(default_factory=list)
    evidence_refs: list[EvidenceItem] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    total_score: int = 0
    risk_level: str = ""
    overall_state: str = ""
    top_deductions: list[str] = Field(default_factory=list)
    score_note: str = ""
    dimensions: list[ScoreDimension] = Field(default_factory=list)


class ReportLayer(BaseModel):
    executive_summary: str = ""
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    key_judgments: list[ReportJudgment] = Field(default_factory=list)
    risk_opportunities: dict[str, list[RiskOpportunityItem]] = Field(
        default_factory=lambda: {"risks": [], "opportunities": []}
    )
    deep_sections: list[StructuredReportSection] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    action_items: list[RecommendationAction] = Field(default_factory=list)


class EvidenceLayer(BaseModel):
    key_evidence: list[KeyEvidenceDigest] = Field(default_factory=list)
    verification_focus: list[VerificationNote] = Field(default_factory=list)
    evidence_index: list[EvidenceItem] = Field(default_factory=list)


class MachineDiagnostic(BaseModel):
    label: str
    value: str


class MachineLayer(BaseModel):
    analysis_plan: list[AnalysisPlanItem] = Field(default_factory=list)
    skill_runs: list[SkillRunItem] = Field(default_factory=list)
    activated_skills: dict[str, list[str]] = Field(default_factory=dict)
    diagnostics: list[MachineDiagnostic] = Field(default_factory=list)
    routing: dict[str, Any] = Field(default_factory=dict)
    preference_profile: PreferenceProfile = Field(default_factory=PreferenceProfile)


class ReportAppendix(BaseModel):
    analysis_plan: list[AnalysisPlanItem] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)
    evidence_index: list[EvidenceItem] = Field(default_factory=list)
    skill_runs: list[SkillRunItem] = Field(default_factory=list)
    routing: dict[str, Any] = Field(default_factory=dict)
    preference_profile: PreferenceProfile = Field(default_factory=PreferenceProfile)


class ReportPayload(BaseModel):
    cover: dict[str, str] = Field(default_factory=dict)
    report_layer: ReportLayer = Field(default_factory=ReportLayer)
    evidence_layer: EvidenceLayer = Field(default_factory=EvidenceLayer)
    machine_layer: MachineLayer = Field(default_factory=MachineLayer)
    sections: list[StructuredReportSection] = Field(default_factory=list)
    appendix: ReportAppendix = Field(default_factory=ReportAppendix)
    summary_cards: list[dict[str, str]] = Field(default_factory=list)
    personalization: dict[str, Any] = Field(default_factory=dict)


class SkillInfo(BaseModel):
    skill_id: str
    name: str
    skill_type: str
    description: str
    skill_layer: str | None = None
    skill_category: str | None = None
    goal: str | None = None
    version: str | None = None
    trigger_condition: str | None = None
    applicable_when: list[str] = Field(default_factory=list)
    not_applicable_when: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    optional_inputs: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    evidence_requirements: str | None = None
    evaluation_criteria: list[str] = Field(default_factory=list)
    failure_handling: str | None = None
    priority: int | None = None
    tags: list[str] = Field(default_factory=list)
    expert_role: str | None = None
    domain_focus: str | None = None
    core_questions: list[str] = Field(default_factory=list)
    preferred_terms: list[str] = Field(default_factory=list)
    translation_rule: str | None = None
    reasoning_style: str | None = None


class PromptTemplate(BaseModel):
    template_id: str
    industry_key: str
    industry_label: str
    module_group: str = "custom"
    capability_label: str = ""
    title: str
    description: str
    query_template: str
    preference_template: str = ""
    guidance: list[str] = Field(default_factory=list)
    suggested_documents: list[str] = Field(default_factory=list)
    example_company_code: str = ""
    is_custom: bool = False


class UploadedDocumentItem(BaseModel):
    doc_id: str
    company_code: str
    company_name: str = ""
    report_type: str
    filename: str
    source_path: str = ""
    title: str = ""
    total_pages: int = 0
    created_at: str | None = None


class UploadDocumentResponse(BaseModel):
    uploaded_count: int
    company_code: str
    material_type: str
    allowed_file_types: list[str] = Field(default_factory=list)
    documents: list[UploadedDocumentItem] = Field(default_factory=list)


class UploadCapabilityResponse(BaseModel):
    allowed_file_types: list[str] = Field(default_factory=list)
    accept_extensions: list[str] = Field(default_factory=list)


class ReportHistoryItem(BaseModel):
    task_id: str
    company_code: str
    query: str
    status: str
    created_at: str
    report_title: str = ""


class AnalyzeResponse(BaseModel):
    task_id: str
    company_code: str
    query: str
    report_title: str = "企业体检报告"
    summary: str
    total_score: int = 0
    risk_score: int
    risk_level: str
    findings: list[str]
    evidence: list[EvidenceItem]
    recommendations: list[str]
    activated_skills: dict[str, list[str]]
    custom_skill_outputs: dict[str, Any]
    report_sections: dict[str, str]
    analysis_plan: list[AnalysisPlanItem] = Field(default_factory=list)
    verification_notes: list[VerificationNote] = Field(default_factory=list)
    skill_runs: list[SkillRunItem] = Field(default_factory=list)
    report_payload: ReportPayload = Field(default_factory=ReportPayload)
    preference_profile: PreferenceProfile = Field(default_factory=PreferenceProfile)
    available_exports: list[str] = Field(default_factory=lambda: ["json", "markdown", "html", "pdf"])


class ReportDetailResponse(AnalyzeResponse):
    status: str
    created_at: str


class AskResponse(BaseModel):
    task_id: str | None = None
    answer: str
    evidence: list[EvidenceItem]


class ApiEnvelope(BaseModel):
    success: bool = True
    data: Any
    message: str = "ok"
