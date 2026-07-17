import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: BASE_URL });

export type DocStatus =
  | "uploaded" | "parsing" | "parsed" | "chunking" | "indexing" | "indexed" | "failed";

export interface DocumentSummary {
  id: string;
  title: string;
  original_filename: string;
  status: DocStatus;
  category: string | null;
  page_count: number | null;
  chunk_count: number;
  error_message: string | null;
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

export async function getHealth(): Promise<boolean> {
  try {
    const { data } = await api.get("/api/health", { timeout: 4000 });
    return data?.status === "ok";
  } catch {
    return false;
  }
}

export const API_BASE_URL = BASE_URL;
