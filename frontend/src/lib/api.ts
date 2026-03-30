import type {
  AnalyzePayload,
  AnalyzeResponse,
  ApiEnvelope,
  HealthData,
  PromptTemplate,
  ReportDetailResponse,
  ReportHistoryItem,
  SkillInfo,
  SystemCacheClearResponse,
  UploadCapabilityResponse,
  UploadedDocumentItem,
  UploadDocumentResponse,
} from "@/types/api";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    ...init,
  });

  const text = await response.text();
  let payload: ApiEnvelope<T> | { detail?: string } | null = null;

  if (text) {
    try {
      payload = JSON.parse(text) as ApiEnvelope<T> | { detail?: string };
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const message =
      (payload && "message" in payload && typeof payload.message === "string" && payload.message) ||
      (payload && "detail" in payload && typeof payload.detail === "string" && payload.detail) ||
      response.statusText ||
      "请求失败";
    throw new Error(message);
  }

  if (!payload || !("data" in payload)) {
    throw new Error("接口返回格式异常");
  }

  return payload.data;
}

export function fetchHealth(): Promise<HealthData> {
  return request<HealthData>("/health");
}

export function fetchSkills(): Promise<SkillInfo[]> {
  return request<SkillInfo[]>("/skills");
}

export function fetchPromptTemplates(): Promise<PromptTemplate[]> {
  return request<PromptTemplate[]>("/prompt-templates");
}

export function fetchDocuments(companyCode: string): Promise<UploadedDocumentItem[]> {
  return request<UploadedDocumentItem[]>(`/documents?company_code=${encodeURIComponent(companyCode)}`);
}

export function fetchUploadCapabilities(): Promise<UploadCapabilityResponse> {
  return request<UploadCapabilityResponse>("/documents/capabilities");
}

export function fetchRecentReports(limit = 6): Promise<ReportHistoryItem[]> {
  return request<ReportHistoryItem[]>(`/reports/recent?limit=${limit}`);
}

export function clearRecentReports(): Promise<{ deleted: number }> {
  return request<{ deleted: number }>("/reports/recent", {
    method: "DELETE",
  });
}

export function clearSystemCache(): Promise<SystemCacheClearResponse> {
  return request<SystemCacheClearResponse>("/system/cache", {
    method: "DELETE",
  });
}

export function fetchReport(taskId: string): Promise<ReportDetailResponse> {
  return request<ReportDetailResponse>(`/reports/${taskId}`);
}

export function analyzeReport(payload: AnalyzePayload): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadDocuments(payload: {
  files: File[];
  companyCode: string;
  companyName?: string;
  materialType: string;
  industryKey: string;
}): Promise<UploadDocumentResponse> {
  const formData = new FormData();
  payload.files.forEach((file) => {
    formData.append("files", file);
  });
  formData.append("company_code", payload.companyCode);
  formData.append("company_name", payload.companyName || "");
  formData.append("material_type", payload.materialType);
  formData.append("industry_key", payload.industryKey);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
    headers: {
      Accept: "application/json",
    },
  });

  const text = await response.text();
  let payloadBody: ApiEnvelope<UploadDocumentResponse> | { detail?: string } | null = null;
  if (text) {
    try {
      payloadBody = JSON.parse(text) as ApiEnvelope<UploadDocumentResponse> | { detail?: string };
    } catch {
      payloadBody = null;
    }
  }

  if (!response.ok) {
    const message =
      (payloadBody && "message" in payloadBody && typeof payloadBody.message === "string" && payloadBody.message) ||
      (payloadBody && "detail" in payloadBody && typeof payloadBody.detail === "string" && payloadBody.detail) ||
      response.statusText ||
      "上传失败";
    throw new Error(message);
  }

  if (!payloadBody || !("data" in payloadBody)) {
    throw new Error("上传接口返回格式异常");
  }

  return payloadBody.data;
}

export function reportPdfUrl(taskId: string): string {
  return `${API_BASE_URL}/reports/${taskId}/pdf`;
}
