export interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface HealthData {
  status: string;
  llm_mode: "real";
  llm_ready: boolean;
  ark_base_url: string;
  model_name: string;
  ark_timeout_seconds: number;
  has_api_key: boolean;
  last_llm_error: string | null;
}

export interface SystemCacheClearResponse {
  cleared: {
    analysis_tasks: number;
    risk_results: number;
    skill_logs: number;
    report_evaluations: number;
    parsed_documents: number;
    parsed_pages: number;
    evidence_chunks: number;
    company_records: number;
  };
  preserved: {
    raw_source_files: boolean;
    api_configuration: boolean;
  };
}

export interface PromptTemplate {
  template_id: string;
  industry_key: string;
  industry_label: string;
  module_group: string;
  capability_label: string;
  title: string;
  description: string;
  query_template: string;
  preference_template: string;
  guidance: string[];
  suggested_documents: string[];
  example_company_code: string;
  is_custom: boolean;
}

export interface SkillInfo {
  skill_id: string;
  name: string;
  skill_type: string;
  description: string;
  skill_layer?: string | null;
  skill_category?: string | null;
  goal?: string | null;
  version?: string | null;
  trigger_condition?: string | null;
  applicable_when?: string[];
  not_applicable_when?: string[];
  required_inputs?: string[];
  optional_inputs?: string[];
  dependencies?: string[];
  output_schema?: Record<string, unknown>;
  evidence_requirements?: string | null;
  evaluation_criteria?: string[];
  failure_handling?: string | null;
  priority?: number | null;
  tags?: string[];
  expert_role?: string | null;
  domain_focus?: string | null;
  core_questions?: string[];
  preferred_terms?: string[];
  translation_rule?: string | null;
  reasoning_style?: string | null;
}

export interface ExpertProfile {
  expert_role: string;
  domain_focus: string;
  core_questions: string[];
  preferred_terms: string[];
  translation_rule: string;
  reasoning_style: string;
}

export interface EvidenceItem {
  page_no: number;
  text: string;
  source: string;
  section_title: string;
  section_path: string;
  relevance_score: number;
  reason: string;
  quote: string;
  evidence_type?: string;
  priority_level?: number;
}

export interface VerificationNote {
  severity: string;
  title: string;
  detail: string;
}

export interface AnalysisPlanItem {
  key: string;
  title: string;
  goal: string;
  aspect: string;
  query_focus: string;
}

export interface SkillRunItem {
  name: string;
  skill_type: string;
  skill_category: string;
  summary: string;
  confidence: number;
  evidence_count: number;
  findings_count: number;
  recommendations_count: number;
}

export interface StructuredReportSection {
  key: string;
  title: string;
  summary: string;
  body: string[];
  evidence: EvidenceItem[];
  pending_checks: string[];
  expert_role?: string;
  section_type?: string;
}

export interface ReportJudgment {
  title: string;
  verdict: string;
  explanation: string;
  confidence: string;
  tone: "neutral" | "good" | "warn" | "risk";
  evidence_anchors: string[];
}

export interface RiskOpportunityItem {
  title: string;
  summary: string;
  basis: string;
  impact: string;
  follow_up: string;
  tone: "neutral" | "good" | "warn" | "risk";
  evidence: EvidenceItem[];
}

export interface KeyEvidenceDigest {
  title: string;
  summary: string;
  supports: string;
  citation: string;
  evidence: EvidenceItem[];
}

export interface RecommendationAction {
  action: string;
  purpose: string;
  focus: string;
  importance: string;
}

export interface ScoreSubItem {
  key: string;
  label: string;
  score: number;
  max_score: number;
  reason: string;
  summary: string;
  uncertainty: boolean;
  follow_up: string;
  evidence_refs: EvidenceItem[];
}

export interface ScoreDimension {
  dimension_key: string;
  dimension_label: string;
  score: number;
  max_score: number;
  summary: string;
  positive_factors: string[];
  negative_factors: string[];
  uncertainty_flags: string[];
  sub_scores: ScoreSubItem[];
  evidence_refs: EvidenceItem[];
}

export interface ScoreBreakdown {
  total_score: number;
  risk_level: string;
  overall_state: string;
  top_deductions: string[];
  score_note: string;
  dimensions: ScoreDimension[];
}

export interface ReportLayer {
  executive_summary?: string;
  score_breakdown?: ScoreBreakdown;
  key_judgments?: ReportJudgment[];
  risk_opportunities?: {
    risks?: RiskOpportunityItem[];
    opportunities?: RiskOpportunityItem[];
  };
  deep_sections?: StructuredReportSection[];
  next_steps?: string[];
  action_items?: RecommendationAction[];
}

export interface EvidenceLayer {
  key_evidence?: KeyEvidenceDigest[];
  verification_focus?: VerificationNote[];
  evidence_index?: EvidenceItem[];
}

export interface MachineDiagnostic {
  label: string;
  value: string;
}

export interface MachineLayer {
  analysis_plan?: AnalysisPlanItem[];
  skill_runs?: SkillRunItem[];
  activated_skills?: {
    generic: string[];
    custom: string[];
  };
  diagnostics?: MachineDiagnostic[];
  routing?: Record<string, unknown>;
  preference_profile?: PreferenceProfile;
}

export interface PreferenceProfile {
  report_style: "concise" | "standard" | "deep";
  focus_priority: "risk_first" | "growth_first" | "finance_first" | "balanced";
  preferred_topics: string[];
  suppressed_topics: string[];
  tone_preference: "investment_research" | "management_diagnosis" | "readable_briefing";
  summary_first: boolean;
  evidence_strictness: "strict" | "standard" | "flexible";
  preferred_output_emphasis: string[];
  domain_hint: string;
  user_intent_raw: string;
  confidence: number;
}

export interface AnalyzePayload {
  company_code: string;
  query: string;
  preference_note: string;
  top_k: number;
}

export interface CustomSkillOutput {
  summary?: string;
  findings?: string[];
  recommendations?: string[];
  evidence_refs?: EvidenceItem[];
  confidence?: number;
  pending_checks?: string[];
  expert_profile?: ExpertProfile;
  [key: string]: unknown;
}

export interface ReportPayload {
  cover?: {
    title?: string;
    company_code?: string;
    query?: string;
  };
  report_layer?: ReportLayer;
  evidence_layer?: EvidenceLayer;
  machine_layer?: MachineLayer;
  summary_cards?: Array<{ label: string; value: string }>;
  personalization?: Record<string, unknown>;
  sections?: StructuredReportSection[];
  appendix?: {
    analysis_plan?: AnalysisPlanItem[];
    verification_notes?: VerificationNote[];
    evidence_index?: EvidenceItem[];
    skill_runs?: SkillRunItem[];
    routing?: Record<string, unknown>;
    preference_profile?: PreferenceProfile;
  };
}

export interface AnalyzeResponse {
  task_id: string;
  company_code: string;
  query: string;
  report_title: string;
  summary: string;
  total_score?: number;
  risk_score: number;
  risk_level: string;
  findings: string[];
  evidence: EvidenceItem[];
  recommendations: string[];
  activated_skills: {
    generic: string[];
    custom: string[];
  };
  custom_skill_outputs: Record<string, CustomSkillOutput>;
  report_sections: Record<string, string>;
  analysis_plan: AnalysisPlanItem[];
  verification_notes: VerificationNote[];
  skill_runs: SkillRunItem[];
  report_payload: ReportPayload;
  preference_profile: PreferenceProfile;
  available_exports: string[];
}

export interface ReportHistoryItem {
  task_id: string;
  company_code: string;
  query: string;
  status: string;
  created_at: string;
  report_title: string;
}

export interface ReportDetailResponse extends AnalyzeResponse {
  status: string;
  created_at: string;
}

export type SkillCatalog = Record<string, SkillInfo>;
