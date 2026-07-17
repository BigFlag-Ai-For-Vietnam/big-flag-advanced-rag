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
export interface DocumentDetail extends DocumentSummary {
  pages: PageOut[];
  chunks: ChunkOut[];
}
export interface Citation {
  document_id: string; title: string; chunk_index: number;
  score: number; final_content: string;
}

export async function uploadDocument(file: File): Promise<DocumentSummary> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/documents", form);
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
