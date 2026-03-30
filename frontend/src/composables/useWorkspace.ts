import { computed, reactive, ref, watch } from "vue";

import {
  analyzeReport,
  clearRecentReports,
  clearSystemCache as clearSystemCacheRequest,
  fetchDocuments,
  fetchHealth,
  fetchPromptTemplates,
  fetchRecentReports,
  fetchReport,
  fetchSkills,
  fetchUploadCapabilities,
  reportPdfUrl,
  uploadDocuments,
} from "@/lib/api";
import type {
  HealthData,
  PromptTemplate,
  ReportDetailResponse,
  ReportHistoryItem,
  SkillCatalog,
  UploadCapabilityResponse,
  UploadedDocumentItem,
} from "@/types/api";
import type { AnalysisForm, UploadMaterialType, WorkspaceStatus } from "@/types/workspace";

const FORM_STORAGE_KEY = "saino.workspace.form";
const DEFAULT_TEMPLATE_ID = "custom";
const DEFAULT_MATERIAL_TYPE: UploadMaterialType = "company";

type NoticeTone = "success" | "info";
type UploadQueueStatus = "uploading" | "success" | "error";

interface NoticeState {
  tone: NoticeTone;
  message: string;
}

interface UploadQueueItem {
  id: string;
  name: string;
  status: UploadQueueStatus;
  detail?: string;
}

function readStoredForm(): AnalysisForm | null {
  try {
    const raw = window.localStorage.getItem(FORM_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<AnalysisForm>;
    if (
      (parsed.templateId !== undefined && typeof parsed.templateId !== "string") ||
      (parsed.materialType !== undefined && typeof parsed.materialType !== "string") ||
      typeof parsed.companyCode !== "string" ||
      typeof parsed.query !== "string" ||
      typeof parsed.preferenceNote !== "string" ||
      typeof parsed.topK !== "number"
    ) {
      return null;
    }

    return {
      templateId: parsed.templateId || DEFAULT_TEMPLATE_ID,
      materialType: (parsed.materialType as UploadMaterialType) || DEFAULT_MATERIAL_TYPE,
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
    templateId: DEFAULT_TEMPLATE_ID,
    materialType: DEFAULT_MATERIAL_TYPE,
    companyCode: "",
    query: "",
    preferenceNote: "",
    topK: 8,
  };

  const form = reactive<AnalysisForm>(initialForm);
  const status = ref<WorkspaceStatus>("idle");
  const cacheClearing = ref(false);
  const uploading = ref(false);
  const errorMessage = ref("");
  const notice = ref<NoticeState | null>(null);
  const report = ref<ReportDetailResponse | null>(null);
  const history = ref<ReportHistoryItem[]>([]);
  const health = ref<HealthData | null>(null);
  const skillCatalog = ref<SkillCatalog>({});
  const promptTemplates = ref<PromptTemplate[]>([]);
  const uploadedDocuments = ref<UploadedDocumentItem[]>([]);
  const uploadCapabilities = ref<UploadCapabilityResponse>({
    allowed_file_types: ["PDF", "TXT", "Markdown"],
    accept_extensions: [".pdf", ".txt", ".md"],
  });
  const uploadQueue = ref<UploadQueueItem[]>([]);
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

  watch(
    () => form.companyCode.trim(),
    async (companyCode) => {
      if (!companyCode) {
        uploadedDocuments.value = [];
        return;
      }
      try {
        uploadedDocuments.value = await fetchDocuments(companyCode);
      } catch {
        // Best effort only.
      }
    },
    { immediate: true },
  );

  const canSubmit = computed(() => form.companyCode.trim().length > 0 && form.query.trim().length > 0);
  const canUpload = computed(
    () => form.companyCode.trim().length > 0 && status.value !== "loading" && !uploading.value && !cacheClearing.value,
  );
  const currentPdfUrl = computed(() => (report.value ? reportPdfUrl(report.value.task_id) : ""));
  const busy = computed(() => status.value === "loading" || cacheClearing.value || uploading.value);
  const currentTemplate = computed<PromptTemplate | null>(() => {
    if (!promptTemplates.value.length) {
      return null;
    }
    return (
      promptTemplates.value.find((item) => item.template_id === form.templateId) ||
      promptTemplates.value.find((item) => item.is_custom) ||
      promptTemplates.value[0] ||
      null
    );
  });

  async function refreshMetadata(): Promise<void> {
    const [healthData, skills, templates, capabilities] = await Promise.all([
      fetchHealth(),
      fetchSkills(),
      fetchPromptTemplates(),
      fetchUploadCapabilities(),
    ]);
    health.value = healthData;
    skillCatalog.value = Object.fromEntries(skills.map((item) => [item.name, item]));
    promptTemplates.value = templates;
    uploadCapabilities.value = capabilities;

    if (!templates.some((item) => item.template_id === form.templateId)) {
      form.templateId = templates.find((item) => item.is_custom)?.template_id || templates[0]?.template_id || DEFAULT_TEMPLATE_ID;
    }
  }

  async function refreshHistory(): Promise<void> {
    history.value = await fetchRecentReports();
  }

  async function refreshDocuments(): Promise<void> {
    const companyCode = form.companyCode.trim();
    if (!companyCode) {
      uploadedDocuments.value = [];
      return;
    }
    uploadedDocuments.value = await fetchDocuments(companyCode);
  }

  async function bootstrap(): Promise<void> {
    const results = await Promise.allSettled([refreshMetadata(), refreshHistory(), refreshDocuments()]);
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
      await Promise.allSettled([refreshMetadata(), refreshHistory(), refreshDocuments()]);
    } catch (error) {
      errorMessage.value = getErrorMessage(error);
      status.value = "error";
      await Promise.allSettled([refreshMetadata(), refreshHistory(), refreshDocuments()]);
    }
  }

  async function uploadFiles(files: File[]): Promise<void> {
    const companyCode = form.companyCode.trim();
    if (!files.length || !companyCode || uploading.value) {
      return;
    }

    const queueItems = files.map<UploadQueueItem>((file, index) => ({
      id: `${Date.now()}-${index}-${file.name}`,
      name: file.name,
      status: "uploading",
      detail: "正在上传并纳入分析资料库",
    }));

    uploadQueue.value = queueItems;
    uploading.value = true;
    errorMessage.value = "";
    notice.value = null;

    try {
      const result = await uploadDocuments({
        files,
        companyCode,
        materialType: form.materialType,
        industryKey: currentTemplate.value?.industry_key || "generic",
      });
      const freshDocuments = await fetchDocuments(companyCode).catch(() => null);
      if (freshDocuments) {
        uploadedDocuments.value = freshDocuments;
      } else {
        const existing = new Map(uploadedDocuments.value.map((item) => [item.doc_id, item]));
        result.documents.forEach((item) => {
          existing.set(item.doc_id, item);
        });
        uploadedDocuments.value = Array.from(existing.values());
      }
      uploadQueue.value = queueItems.map((item) => ({
        ...item,
        status: "success",
        detail: "已上传，可用于后续分析",
      }));
      notice.value = {
        tone: "success",
        message: `已上传 ${result.uploaded_count} 个文件，当前公司共接入 ${uploadedDocuments.value.length} 份可检索资料。`,
      };
    } catch (error) {
      const message = getErrorMessage(error);
      errorMessage.value = message;
      uploadQueue.value = queueItems.map((item) => ({
        ...item,
        status: "error",
        detail: message,
      }));
    } finally {
      await refreshDocuments().catch(() => {
        // Best effort only. Upload status feedback stays unchanged if the refresh fails.
      });
      uploading.value = false;
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
      await Promise.allSettled([refreshMetadata(), refreshHistory(), refreshDocuments()]);
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

    const confirmed = window.confirm("确认删除全部历史分析记录吗？此操作不会删除已上传的原始资料。");
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
        "1. 已导入文档的解析记录与页面缓存",
        "2. 检索证据分块、临时索引与知识片段",
        "3. 上一轮分析的报告结果、中间结果与日志",
        "4. 当前前端表单、本地任务状态与界面残留数据",
        "",
        "不会清除：",
        "- 真实 API 配置",
        "- 已上传的原始资料文件",
        "",
        "清理后如要继续分析，原始资料仍在，但需要重新入库后再分析。",
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
      uploadedDocuments.value = [];
      uploadQueue.value = [];
      lastAction.value = null;
      form.templateId = DEFAULT_TEMPLATE_ID;
      form.materialType = DEFAULT_MATERIAL_TYPE;
      form.companyCode = "";
      form.query = "";
      form.preferenceNote = "";
      form.topK = 8;
      clearStoredForm();
      status.value = "idle";
      sidebarOpen.value = false;
      sidebarCollapsed.value = false;

      await Promise.allSettled([refreshMetadata(), refreshHistory(), refreshDocuments()]);

      notice.value = {
        tone: "success",
        message: `系统缓存已清理：删除了 ${result.cleared.parsed_documents} 份文档缓存、${result.cleared.evidence_chunks} 条证据分块和 ${result.cleared.analysis_tasks} 条分析记录。`,
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
    notice.value = null;
    status.value = "idle";
    sidebarOpen.value = false;
    sidebarCollapsed.value = false;
  }

  function clearInputs(): void {
    form.materialType = DEFAULT_MATERIAL_TYPE;
    form.companyCode = "";
    form.query = "";
    form.preferenceNote = "";
    form.topK = 8;
    uploadedDocuments.value = [];
    uploadQueue.value = [];
    errorMessage.value = "";
    if (!report.value) {
      status.value = "idle";
    }
  }

  function selectTemplate(templateId: string): void {
    form.templateId = templateId;
    errorMessage.value = "";
    if (!report.value) {
      status.value = "idle";
    }
  }

  function applyActiveTemplate(): void {
    const template = currentTemplate.value;
    if (!template) {
      return;
    }

    form.templateId = template.template_id;
    if (template.example_company_code) {
      form.companyCode = template.example_company_code;
    }
    form.query = template.query_template;
    form.preferenceNote = template.preference_template;
    errorMessage.value = "";
    if (!report.value) {
      status.value = "idle";
    }
  }

  function fillExample(): void {
    applyActiveTemplate();
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
    uploading,
    busy,
    canUpload,
    notice,
    report,
    history,
    health,
    skillCatalog,
    promptTemplates,
    currentTemplate,
    uploadedDocuments,
    uploadCapabilities,
    uploadQueue,
    sidebarOpen,
    sidebarCollapsed,
    errorMessage,
    lastAction,
    canSubmit,
    currentPdfUrl,
    bootstrap,
    analyze,
    uploadFiles,
    openReport,
    retry,
    clearHistory,
    clearSystemCache,
    refreshMetadata,
    refreshHistory,
    refreshDocuments,
    newAnalysis,
    clearInputs,
    fillExample,
    selectTemplate,
    applyActiveTemplate,
    toggleSidebar,
    closeSidebar,
    toggleSidebarCollapse,
  };
}
