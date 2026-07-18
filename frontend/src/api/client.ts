import axios from "axios";

// ?? (không phải ||): chuỗi rỗng là giá trị hợp lệ = same-origin (chạy sau nginx 80/443).
// Fallback :8000 chỉ dành cho dev local không Docker (uvicorn --reload).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

export type DocStatus =
  | "uploaded" | "parsing" | "parsed" | "chunking" | "indexing" | "indexed" | "failed";

export type Lifecycle = "active" | "superseded" | "expired";

export interface DocumentSummary {
  id: string;
  title: string;
  original_filename: string;
  status: DocStatus;
  category: string | null;
  page_count: number | null;
  chunk_count: number;
  error_message: string | null;
  // --- versioning / hiệu lực ---
  doc_no: string | null;
  version_label: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  is_active: boolean;
  supersedes_id: string | null;
  superseded_by_id: string | null;
  supersession_note: string | null;
  lifecycle: Lifecycle;
  created_at: string;
  updated_at: string;
}

export interface PageOut { id: string; page_number: number; parsed_text: string | null; }
export interface ChunkOut {
  id: string; chunk_index: number; raw_text: string;
  contextual_prefix: string | null; final_content: string;
  qdrant_point_id: string | null; token_count: number | null;
}

export interface CatalogNode { name: string; children: CatalogNode[]; }
export interface Catalog { tree: CatalogNode[]; }
export interface CatalogInfo { document_id: string; title: string; catalog: Catalog; }
export interface CatalogPreset { key: string; label: string; entities: string[]; }

export interface DocumentDetail extends DocumentSummary {
  focus_entities: string[] | null;
  catalog: Catalog | null;
  pages: PageOut[];
  chunks: ChunkOut[];
}
export interface Citation {
  document_id: string; title: string; chunk_index: number;
  score: number; final_content: string;
}
export interface McpRetrieveConfig {
  normalize: boolean; rewrite: boolean; rerank: boolean; agent_max_steps: number;
}
export interface ToolCallTrace {
  tool: string; args: Record<string, unknown>; hit_count: number;
}
export interface SubgoalCoverage {
  description: string; query: string; satisfied: boolean; note: string; evidence_count: number;
}
export interface McpRetrieveResponse {
  citations: Citation[];
  normalized_question: string;
  rewritten_question: string;
  tool_calls: ToolCallTrace[];
  subgoals: SubgoalCoverage[];
  config: McpRetrieveConfig;
}

export interface UploadOptions {
  category?: string | null;
  focusEntities?: string[];
}

export async function uploadDocument(file: File, opts: UploadOptions = {}): Promise<DocumentSummary> {
  const form = new FormData();
  form.append("file", file);
  if (opts.category) form.append("category", opts.category);
  if (opts.focusEntities && opts.focusEntities.length)
    form.append("focus_entities", JSON.stringify(opts.focusEntities));
  const { data } = await api.post("/api/documents", form);
  return data;
}

export async function getCatalogPresets(): Promise<CatalogPreset[]> {
  const { data } = await api.get("/api/catalog-presets");
  return data;
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const { data } = await api.get("/api/documents", { params: { page: 1, page_size: 100 } });
  return data.items;
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const { data } = await api.get(`/api/documents/${id}`);
  return data;
}

export async function getStatus(id: string): Promise<DocumentSummary> {
  const { data } = await api.get(`/api/documents/${id}/status`);
  return data;
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/api/documents/${id}`);
}

export async function reprocessDocument(id: string): Promise<void> {
  await api.post(`/api/documents/${id}/reprocess`);
}

// --- versioning / hiệu lực ---
export interface VersionChainItem {
  id: string;
  title: string;
  doc_no: string | null;
  version_label: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  is_active: boolean;
  lifecycle: Lifecycle;
}

export async function supersedeDocument(
  oldId: string,
  newDocumentId: string,
  options: { note?: string; effectiveDate?: string } = {},
): Promise<DocumentSummary[]> {
  const { data } = await api.post(`/api/documents/${oldId}/supersede`, {
    new_document_id: newDocumentId,
    note: options.note || null,
    effective_date: options.effectiveDate
      ? `${options.effectiveDate}T00:00:00`
      : null,
  });
  return data;
}

export async function expireDocument(id: string): Promise<DocumentSummary> {
  const { data } = await api.post(`/api/documents/${id}/expire`);
  return data;
}

export async function reactivateDocument(id: string): Promise<DocumentSummary> {
  const { data } = await api.post(`/api/documents/${id}/reactivate`);
  return data;
}

export async function getVersionChain(id: string): Promise<VersionChainItem[]> {
  const { data } = await api.get(`/api/documents/${id}/versions`);
  return data.items;
}

export async function mcpRetrieve(question: string, top_k: number): Promise<McpRetrieveResponse> {
  const { data } = await api.post("/api/playground/mcp-retrieve", { question, top_k });
  return data;
}

export async function getHealth(): Promise<boolean> {
  try {
    const { data } = await api.get("/api/health", { timeout: 4000 });
    return data?.status === "ok";
  } catch {
    return false;
  }
}

export const API_BASE_URL = BASE_URL;
