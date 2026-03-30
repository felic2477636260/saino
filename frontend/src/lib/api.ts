import type {
  AnalyzePayload,
  AnalyzeResponse,
  ApiEnvelope,
  HealthData,
  ReportDetailResponse,
  ReportHistoryItem,
  SkillInfo,
  SystemCacheClearResponse,
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

export function reportPdfUrl(taskId: string): string {
  return `${API_BASE_URL}/reports/${taskId}/pdf`;
}
