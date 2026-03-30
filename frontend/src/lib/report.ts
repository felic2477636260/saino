import type {
  AnalyzeResponse,
  CustomSkillOutput,
  HealthData,
  KeyEvidenceDigest,
  RecommendationAction,
  ReportDetailResponse,
  ReportJudgment,
  RiskOpportunityItem,
  ScoreBreakdown,
  SkillCatalog,
  SkillRunItem,
  StructuredReportSection,
  VerificationNote,
} from "@/types/api";

export type Tone = "neutral" | "good" | "warn" | "risk";

export interface SkillTraceItem {
  key: string;
  label: string;
  description: string;
  typeLabel: string;
  summary: string;
  findingsCount: number;
  recommendationsCount: number;
}

export interface SkillTraceGroup {
  title: string;
  items: SkillTraceItem[];
  emptyText: string;
}

export interface ReportSectionEntry {
  key: string;
  label: string;
  summary: string;
  paragraphs: string[];
  pendingChecks: string[];
  expertRole: string;
}

const LEGACY_SECTION_LABELS: Record<string, string> = {
  conclusion: "执行摘要",
  major_findings: "综合诊断结论",
  risk_diagnosis: "核心风险诊断",
  key_evidence: "关键证据摘要",
  action_suggestions: "最终结论",
  industry_custom_analysis: "专题分析",
  verification_and_gaps: "待验证事项",
};

const SUMMARY_METRIC_ORDER = ["总分", "风险等级", "经营基本盘", "利润兑现质量", "现金回流与财务缓冲", "外部环境与竞争位置"];

const SUMMARY_METRIC_LABEL_ALIASES: Record<string, string> = {
  健康度评分: "总分",
  健康度: "总分",
  风险分: "总分",
  经营质量: "经营基本盘",
  盈利质量: "利润兑现质量",
  现金流健康度: "现金回流与财务缓冲",
  行业与外部环境适配度: "外部环境与竞争位置",
};

function normalizeSummaryMetricLabel(label: string | undefined): string {
  const normalized = (label ?? "").trim();
  if (!normalized) {
    return "";
  }
  return SUMMARY_METRIC_LABEL_ALIASES[normalized] ?? normalized;
}

function splitParagraphs(content: string): string[] {
  const trimmed = content.trim();
  if (!trimmed) {
    return [];
  }
  return trimmed
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeTone(value: string | undefined): Tone {
  if (value === "good" || value === "warn" || value === "risk") {
    return value;
  }
  return "neutral";
}

function confidenceText(value: number): string {
  if (value >= 0.75) {
    return "高置信";
  }
  if (value >= 0.5) {
    return "中置信";
  }
  return "低置信";
}

function skillLabel(name: string): string {
  return name.replace(/Skill$/, "").replace(/([a-z])([A-Z])/g, "$1 $2");
}

function customOutputSummary(output: CustomSkillOutput | undefined, fallback: string): string {
  if (!output) {
    return fallback;
  }
  return typeof output.summary === "string" && output.summary.trim() ? output.summary.trim() : fallback;
}

function fallbackJudgments(report: ReportDetailResponse): ReportJudgment[] {
  return report.findings.map((item, index) => ({
    title: `判断 ${index + 1}`,
    verdict: item,
    explanation: "",
    confidence: "中",
    tone: classifyFinding(item),
    evidence_anchors: [],
  }));
}

function fallbackRiskOpportunities(report: ReportDetailResponse): {
  risks: RiskOpportunityItem[];
  opportunities: RiskOpportunityItem[];
} {
  const risks: RiskOpportunityItem[] = report.findings
    .filter((item) => {
      const tone = classifyFinding(item);
      return tone === "risk" || tone === "warn";
    })
    .slice(0, 3)
    .map((item) => ({
      title: "风险线索",
      summary: item,
      basis: "",
      impact: "",
      follow_up: "",
      tone: normalizeTone(classifyFinding(item)),
      evidence: [],
    }));

  const opportunities: RiskOpportunityItem[] = report.findings
    .filter((item) => classifyFinding(item) === "good")
    .slice(0, 3)
    .map((item) => ({
      title: "机会线索",
      summary: item,
      basis: "",
      impact: "",
      follow_up: "",
      tone: "good",
      evidence: [],
    }));

  return { risks, opportunities };
}

function fallbackKeyEvidence(report: ReportDetailResponse): KeyEvidenceDigest[] {
  return report.evidence.slice(0, 4).map((item) => ({
    title: item.section_title || item.section_path || item.source,
    summary: summarizeText(item.quote || item.text, 96),
    supports: "为当前报告提供基础支撑。",
    citation: `${item.source} P${item.page_no}`,
    evidence: [item],
  }));
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function summarizeText(text: string, maxLength = 56): string {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) {
    return compact;
  }
  return `${compact.slice(0, maxLength)}…`;
}

export function getRiskTone(level: string): Tone {
  if (level.includes("高风险")) {
    return "risk";
  }
  if (level.includes("中")) {
    return "warn";
  }
  if (level.includes("低风险")) {
    return "good";
  }
  return "neutral";
}

export function getStatusLabel(status: string): string {
  if (status === "completed" || status === "success") {
    return "已完成";
  }
  if (status === "running") {
    return "生成中";
  }
  if (status === "failed" || status === "error") {
    return "失败";
  }
  return "未开始";
}

export function getModeLabel(health: HealthData | null): string {
  if (!health) {
    return "离线";
  }
  return "真实 API";
}

export function classifyFinding(text: string): Tone {
  const content = text.toLowerCase();
  if (/(风险|承压|下滑|不足|异常|减值|波动)/.test(content)) {
    return "risk";
  }
  if (/(改善|增长|提升|回暖|稳健|修复|机会|弹性)/.test(content)) {
    return "good";
  }
  if (/(关注|跟踪|观察|待验证|待核验)/.test(content)) {
    return "warn";
  }
  return "neutral";
}

export function getToneLabel(tone: Tone): string {
  if (tone === "good") {
    return "积极";
  }
  if (tone === "warn") {
    return "关注";
  }
  if (tone === "risk") {
    return "风险";
  }
  return "观察";
}

export function getExecutiveSummary(report: ReportDetailResponse): string {
  return report.report_payload?.report_layer?.executive_summary?.trim() || report.summary;
}

export function getScoreBreakdown(report: ReportDetailResponse): ScoreBreakdown | null {
  return report.report_payload?.report_layer?.score_breakdown ?? null;
}

function hasExecutiveSummary(report: Pick<AnalyzeResponse, "report_payload" | "summary">): boolean {
  const summary = report.report_payload?.report_layer?.executive_summary?.trim() || report.summary?.trim() || "";
  return Boolean(summary);
}

function isSummarySection(section: StructuredReportSection): boolean {
  const title = section.title.trim();
  const key = section.key.trim();
  return key === "executive_summary" || key === "conclusion" || title === "执行摘要" || title === "鎵ц鎽樿";
}

export function getSummaryMetrics(report: ReportDetailResponse): Array<{ label: string; value: string }> {
  const cards = report.report_payload?.summary_cards ?? [];
  const metrics = new Map<string, string>();

  for (const card of cards) {
    const label = normalizeSummaryMetricLabel(card.label);
    const value = String(card.value ?? "").trim();
    if (label && value && !metrics.has(label)) {
      metrics.set(label, value);
    }
  }

  const scoreBreakdown = getScoreBreakdown(report);
  if (!metrics.has("总分")) {
    metrics.set("总分", String(scoreBreakdown?.total_score ?? report.total_score ?? report.risk_score));
  }
  if (!metrics.has("风险等级") && (scoreBreakdown?.risk_level || report.risk_level.trim())) {
    metrics.set("风险等级", scoreBreakdown?.risk_level ?? report.risk_level.trim());
  }

  const orderedMetrics = SUMMARY_METRIC_ORDER.filter((label) => metrics.has(label)).map((label) => ({
    label,
    value: metrics.get(label) ?? "",
  }));

  for (const [label, value] of metrics.entries()) {
    if (!SUMMARY_METRIC_ORDER.includes(label)) {
      orderedMetrics.push({ label, value });
    }
  }

  return orderedMetrics;
}

export function getKeyJudgments(report: ReportDetailResponse): ReportJudgment[] {
  const judgments = report.report_payload?.report_layer?.key_judgments ?? [];
  return judgments.length ? judgments : fallbackJudgments(report);
}

export function getRiskOpportunities(report: ReportDetailResponse): {
  risks: RiskOpportunityItem[];
  opportunities: RiskOpportunityItem[];
} {
  const groups = report.report_payload?.report_layer?.risk_opportunities;
  if (groups?.risks?.length || groups?.opportunities?.length) {
    return {
      risks: (groups.risks ?? []).map((item) => ({ ...item, tone: normalizeTone(item.tone) })),
      opportunities: (groups.opportunities ?? []).map((item) => ({ ...item, tone: normalizeTone(item.tone) })),
    };
  }
  return fallbackRiskOpportunities(report);
}

export function getNextSteps(report: ReportDetailResponse): string[] {
  const steps = report.report_payload?.report_layer?.next_steps ?? [];
  return steps.length ? steps : report.recommendations;
}

export function getActionItems(report: ReportDetailResponse): RecommendationAction[] {
  const items = report.report_payload?.report_layer?.action_items ?? [];
  if (items.length) {
    return items;
  }
  return getNextSteps(report).map((item) => ({
    action: item,
    purpose: "",
    focus: "",
    importance: "",
  }));
}

export function getKeyEvidence(report: ReportDetailResponse): KeyEvidenceDigest[] {
  const items = report.report_payload?.evidence_layer?.key_evidence ?? [];
  return items.length ? items : fallbackKeyEvidence(report);
}

export function getVerificationFocus(report: ReportDetailResponse): VerificationNote[] {
  const items = report.report_payload?.evidence_layer?.verification_focus ?? [];
  return items.length ? items : report.verification_notes;
}

export function getTechnicalDiagnostics(report: ReportDetailResponse): Array<{ label: string; value: string }> {
  const diagnostics = report.report_payload?.machine_layer?.diagnostics ?? [];
  if (diagnostics.length) {
    return diagnostics;
  }
  return [
    { label: "计划主题数", value: String(report.analysis_plan.length) },
    { label: "执行技能数", value: String(report.skill_runs.length) },
    { label: "关键证据数", value: String(report.evidence.length) },
    { label: "待验证项", value: String(report.verification_notes.length) },
  ];
}

function buildTraceItem(run: SkillRunItem, skillCatalog: SkillCatalog, customOutputs: Record<string, CustomSkillOutput>): SkillTraceItem {
  const catalogItem = skillCatalog[run.name];
  const summary = customOutputSummary(customOutputs[run.name], run.summary || "已参与本次分析流程。");
  const expertRole = customOutputs[run.name]?.expert_profile?.expert_role || catalogItem?.expert_role;
  return {
    key: run.name,
    label: skillLabel(run.name),
    description: expertRole ? `${expertRole} · ${catalogItem?.description || "参与本次分析流程。"}` : catalogItem?.description || "参与本次分析流程。",
    typeLabel: `${run.skill_type === "custom" ? "定制" : "通用"} · ${run.skill_category}`,
    summary: `${summary} ${confidenceText(run.confidence)}，证据 ${run.evidence_count} 条。`,
    findingsCount: run.findings_count,
    recommendationsCount: run.recommendations_count,
  };
}

export function buildSkillGroups(report: ReportDetailResponse, skillCatalog: SkillCatalog): SkillTraceGroup[] {
  const runs = report.report_payload?.machine_layer?.skill_runs ?? report.skill_runs ?? [];
  const customOutputs = report.custom_skill_outputs ?? {};

  const genericItems = runs
    .filter((item) => item.skill_type !== "custom")
    .map((item) => buildTraceItem(item, skillCatalog, customOutputs));
  const customItems = runs
    .filter((item) => item.skill_type === "custom")
    .map((item) => buildTraceItem(item, skillCatalog, customOutputs));

  return [
    {
      title: "通用技能",
      items: genericItems,
      emptyText: "当前没有额外通用技能记录。",
    },
    {
      title: "定制技能",
      items: customItems,
      emptyText: "当前没有定制技能参与。",
    },
  ];
}

function normalizeSectionContent(section: StructuredReportSection): Pick<ReportSectionEntry, "summary" | "paragraphs"> {
  const summary = section.summary.trim();
  const paragraphs = section.body.reduce<string[]>((items, paragraph) => {
    const cleaned = paragraph.trim();
    if (!cleaned) {
      return items;
    }
    if (summary && isDuplicateSectionText(summary, cleaned)) {
      return items;
    }
    if (items.some((item) => isDuplicateSectionText(item, cleaned))) {
      return items;
    }
    items.push(cleaned);
    return items;
  }, []);

  return {
    summary,
    paragraphs,
  };
}

function isDuplicateSectionText(left: string, right: string): boolean {
  const normalizedLeft = left.replace(/\s+/g, "");
  const normalizedRight = right.replace(/\s+/g, "");
  if (!normalizedLeft || !normalizedRight) {
    return false;
  }
  return normalizedLeft === normalizedRight || normalizedLeft.includes(normalizedRight) || normalizedRight.includes(normalizedLeft);
}

export function getOrderedReportSections(report: Pick<AnalyzeResponse, "report_payload" | "report_sections" | "summary">): ReportSectionEntry[] {
  const structuredSections = report.report_payload?.sections ?? [];
  if (structuredSections.length) {
    const hideExecutiveSummary = hasExecutiveSummary(report);
    return structuredSections.map((section: StructuredReportSection) => {
      const normalized = normalizeSectionContent(section);
      return {
        key: section.key,
        label: section.title,
        summary: normalized.summary,
        paragraphs: normalized.paragraphs,
        pendingChecks: section.pending_checks,
        expertRole: section.expert_role ?? "",
      };
    }).filter((section) => {
      if (!hideExecutiveSummary) {
        return true;
      }
      return !isSummarySection(structuredSections.find((item) => item.key === section.key || item.title === section.label) as StructuredReportSection);
    });
  }

  const legacySections = report.report_sections ?? {};
  return Object.entries(legacySections)
    .filter(([key]) => key !== "conclusion")
    .map(([key, value]) => ({
      key,
      label: LEGACY_SECTION_LABELS[key] ?? key,
      summary: summarizeText(value, 96),
      paragraphs: splitParagraphs(value),
      pendingChecks: [],
      expertRole: "",
    }));
}

export function getJudgmentSummary(judgment: ReportJudgment): string {
  return [judgment.verdict, judgment.explanation].filter(Boolean).join(" ");
}
