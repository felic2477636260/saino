export type WorkspaceStatus = "idle" | "loading" | "success" | "error";
export type UploadMaterialType = "company" | "research" | "industry";

export interface AnalysisForm {
  templateId: string;
  materialType: UploadMaterialType;
  companyCode: string;
  query: string;
  preferenceNote: string;
  topK: number;
}
