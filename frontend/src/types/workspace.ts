export type WorkspaceStatus = "idle" | "loading" | "success" | "error";

export interface AnalysisForm {
  companyCode: string;
  query: string;
  preferenceNote: string;
  topK: number;
}
