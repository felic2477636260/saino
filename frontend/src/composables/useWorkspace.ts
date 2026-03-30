import { computed, reactive, ref, watch } from "vue";

import { EXAMPLE_COMPANY, EXAMPLE_QUERY } from "@/constants/example";
import {
  analyzeReport,
  clearRecentReports,
  clearSystemCache as clearSystemCacheRequest,
  fetchHealth,
  fetchRecentReports,
  fetchReport,
  fetchSkills,
  reportPdfUrl,
} from "@/lib/api";
import type { HealthData, ReportDetailResponse, ReportHistoryItem, SkillCatalog } from "@/types/api";
import type { AnalysisForm, WorkspaceStatus } from "@/types/workspace";

const FORM_STORAGE_KEY = "saino.workspace.form";

type NoticeTone = "success" | "info";

interface NoticeState {
  tone: NoticeTone;
  message: string;
}

function readStoredForm(): AnalysisForm | null {
  try {
    const raw = window.localStorage.getItem(FORM_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<AnalysisForm>;
    if (
      typeof parsed.companyCode !== "string" ||
      typeof parsed.query !== "string" ||
      typeof parsed.preferenceNote !== "string" ||
      typeof parsed.topK !== "number"
    ) {
      return null;
    }
    return {
      companyCode: parsed.companyCode,
      query: parsed.query,
      preferenceNote: parsed.preferenceNote,
      topK: parsed.topK,
    };
  } catch {
    return null;
  }
}

function writeStoredForm(form: AnalysisForm): void {
  try {
    window.localStorage.setItem(FORM_STORAGE_KEY, JSON.stringify(form));
  } catch {
    // Ignore storage failures.
  }
}

function clearStoredForm(): void {
  try {
    window.localStorage.removeItem(FORM_STORAGE_KEY);
  } catch {
    // Ignore storage failures.
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "请求失败，请稍后再试。";
}

export function useWorkspace() {
  const initialForm = readStoredForm() || {
    companyCode: "",
    query: "",
    preferenceNote: "",
    topK: 8,
  };

  const form = reactive<AnalysisForm>(initialForm);
  const status = ref<WorkspaceStatus>("idle");
  const cacheClearing = ref(false);
  const errorMessage = ref("");
  const notice = ref<NoticeState | null>(null);
  const report = ref<ReportDetailResponse | null>(null);
  const history = ref<ReportHistoryItem[]>([]);
  const health = ref<HealthData | null>(null);
  const skillCatalog = ref<SkillCatalog>({});
  const sidebarOpen = ref(false);
  const sidebarCollapsed = ref(false);
  const lastAction = ref<{ type: "analyze" } | { type: "load-report"; taskId: string } | null>(null);

  watch(
    form,
    (value) => {
      writeStoredForm(value);
    },
    { deep: true },
  );

  const canSubmit = computed(() => form.companyCode.trim().length > 0 && form.query.trim().length > 0);
  const currentPdfUrl = computed(() => (report.value ? reportPdfUrl(report.value.task_id) : ""));
  const busy = computed(() => status.value === "loading" || cacheClearing.value);

  async function refreshMetadata(): Promise<void> {
    const [healthData, skills] = await Promise.all([fetchHealth(), fetchSkills()]);
    health.value = healthData;
    skillCatalog.value = Object.fromEntries(skills.map((item) => [item.name, item]));
  }

  async function refreshHistory(): Promise<void> {
    history.value = await fetchRecentReports();
  }

  async function bootstrap(): Promise<void> {
    const results = await Promise.allSettled([refreshMetadata(), refreshHistory()]);
    const rejected = results.find((item) => item.status === "rejected");
    if (rejected && rejected.status === "rejected") {
      errorMessage.value = getErrorMessage(rejected.reason);
    }
  }

  async function analyze(): Promise<void> {
    if (!canSubmit.value || busy.value) {
      return;
    }

    status.value = "loading";
    errorMessage.value = "";
    notice.value = null;
    lastAction.value = { type: "analyze" };

    try {
      const response = await analyzeReport({
        company_code: form.companyCode.trim(),
        query: form.query.trim(),
        preference_note: form.preferenceNote.trim(),
        top_k: form.topK,
      });
      report.value = await fetchReport(response.task_id);
      status.value = "success";
      await Promise.allSettled([refreshMetadata(), refreshHistory()]);
    } catch (error) {
      errorMessage.value = getErrorMessage(error);
      status.value = "error";
      await Promise.allSettled([refreshMetadata(), refreshHistory()]);
    }
  }

  async function openReport(taskId: string): Promise<void> {
    if (busy.value) {
      return;
    }

    const fallbackStatus: WorkspaceStatus = report.value ? "success" : "error";
    status.value = "loading";
    errorMessage.value = "";
    notice.value = null;
    lastAction.value = { type: "load-report", taskId };

    try {
      report.value = await fetchReport(taskId);
      status.value = "success";
      sidebarOpen.value = false;
      sidebarCollapsed.value = false;
      await refreshHistory();
    } catch (error) {
      errorMessage.value = getErrorMessage(error);
      status.value = fallbackStatus;
    }
  }

  async function retry(): Promise<void> {
    if (!lastAction.value) {
      await Promise.allSettled([refreshMetadata(), refreshHistory()]);
      return;
    }
    if (lastAction.value.type === "analyze") {
      await analyze();
      return;
    }
    await openReport(lastAction.value.taskId);
  }

  async function clearHistory(): Promise<void> {
    if (busy.value) {
      return;
    }

    const confirmed = window.confirm("确认删除全部历史分析记录吗？此操作不会删除 data/raw 下的原始 PDF 文件。");
    if (!confirmed) {
      return;
    }

    status.value = "loading";
    errorMessage.value = "";
    notice.value = null;

    try {
      await clearRecentReports();
      history.value = [];
      report.value = null;
      lastAction.value = null;
      status.value = "idle";
      sidebarCollapsed.value = false;
    } catch (error) {
      errorMessage.value = getErrorMessage(error);
      status.value = report.value ? "success" : "error";
    }
  }

  async function clearSystemCache(): Promise<void> {
    if (busy.value) {
      return;
    }

    const confirmed = window.confirm(
      [
        "确认清理系统缓存？",
        "",
        "将会清除：",
        "1. 已导入文档的解析记录与页缓存",
        "2. 检索证据分块、临时索引与知识片段",
        "3. 上一轮分析的报告结果、中间结果与日志",
        "4. 当前前端表单、本地任务状态与界面残留数据",
        "",
        "不会清除：",
        "- ARK_API_KEY / ARK_BASE_URL / MODEL_NAME 等真实 API 配置",
        "- data/raw 下的原始 PDF 文件",
        "",
        "清理后若要继续分析，请先重新导入文件或重新执行 ingest。",
      ].join("\n"),
    );

    if (!confirmed) {
      return;
    }

    cacheClearing.value = true;
    errorMessage.value = "";
    notice.value = null;

    try {
      const result = await clearSystemCacheRequest();

      report.value = null;
      history.value = [];
      lastAction.value = null;
      form.companyCode = "";
      form.query = "";
      form.preferenceNote = "";
      form.topK = 8;
      clearStoredForm();
      status.value = "idle";
      sidebarOpen.value = false;
      sidebarCollapsed.value = false;

      await Promise.allSettled([refreshMetadata(), refreshHistory()]);

      notice.value = {
        tone: "success",
        message: `系统缓存已清理：删除了 ${result.cleared.parsed_documents} 份文档缓存、${result.cleared.evidence_chunks} 条证据分块和 ${result.cleared.analysis_tasks} 条分析记录。真实 API 配置与原始 PDF 文件未被删除。`,
      };
    } catch (error) {
      errorMessage.value = getErrorMessage(error);
      status.value = report.value ? "success" : "error";
    } finally {
      cacheClearing.value = false;
    }
  }

  function newAnalysis(): void {
    report.value = null;
    errorMessage.value = "";
    status.value = "idle";
    sidebarOpen.value = false;
    sidebarCollapsed.value = false;
  }

  function clearInputs(): void {
    form.companyCode = "";
    form.query = "";
    form.preferenceNote = "";
    form.topK = 8;
    errorMessage.value = "";
    if (!report.value) {
      status.value = "idle";
    }
  }

  function fillExample(): void {
    form.companyCode = EXAMPLE_COMPANY;
    form.query = EXAMPLE_QUERY;
    form.preferenceNote = "先给结论和评分，重点看经营质量、现金流与风险，报告简洁一点。";
    errorMessage.value = "";
    if (!report.value) {
      status.value = "idle";
    }
  }

  function toggleSidebar(): void {
    sidebarOpen.value = !sidebarOpen.value;
  }

  function closeSidebar(): void {
    sidebarOpen.value = false;
  }

  function toggleSidebarCollapse(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  return {
    form,
    status,
    cacheClearing,
    busy,
    notice,
    report,
    history,
    health,
    skillCatalog,
    sidebarOpen,
    sidebarCollapsed,
    errorMessage,
    lastAction,
    canSubmit,
    currentPdfUrl,
    bootstrap,
    analyze,
    openReport,
    retry,
    clearHistory,
    clearSystemCache,
    refreshMetadata,
    refreshHistory,
    newAnalysis,
    clearInputs,
    fillExample,
    toggleSidebar,
    closeSidebar,
    toggleSidebarCollapse,
  };
}
