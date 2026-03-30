export type WorkspaceStatus = "idle" | "loading" | "success" | "error";

export interface AnalysisForm {
  templateId: string;
  companyCode: string;
  query: string;
  preferenceNote: string;
  topK: number;
}
