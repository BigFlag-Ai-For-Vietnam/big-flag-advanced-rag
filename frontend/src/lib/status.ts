import type { DocStatus } from "../api/client";

export interface StatusMeta {
  label: string;
  /** class cho pill (nền + chữ + viền), hoạt động ở cả 2 theme nhờ /15 opacity. */
  pill: string;
  dot: string;
  /** đang trong pipeline (hiển thị spinner). */
  busy: boolean;
}

export const STATUS_META: Record<DocStatus, StatusMeta> = {
  uploaded: { label: "Đã tải lên", pill: "bg-slate-500/12 text-slate-500 ring-slate-500/25", dot: "bg-slate-400", busy: true },
  parsing: { label: "Đang phân tích", pill: "bg-sky-500/12 text-sky-500 ring-sky-500/25", dot: "bg-sky-500", busy: true },
  parsed: { label: "Đã phân tích", pill: "bg-indigo-500/12 text-indigo-400 ring-indigo-500/25", dot: "bg-indigo-500", busy: true },
  chunking: { label: "Đang chia đoạn", pill: "bg-violet-500/12 text-violet-400 ring-violet-500/25", dot: "bg-violet-500", busy: true },
  indexing: { label: "Đang lập chỉ mục", pill: "bg-amber-500/12 text-amber-500 ring-amber-500/25", dot: "bg-amber-500", busy: true },
  indexed: { label: "Hoàn tất", pill: "bg-emerald-500/12 text-emerald-500 ring-emerald-500/25", dot: "bg-emerald-500", busy: false },
  failed: { label: "Lỗi", pill: "bg-rose-500/12 text-rose-500 ring-rose-500/25", dot: "bg-rose-500", busy: false },
};

/** Thứ tự các bước pipeline để vẽ stepper. */
export const PIPELINE_STAGES: { key: DocStatus; label: string }[] = [
  { key: "uploaded", label: "Tải lên" },
  { key: "parsing", label: "Phân tích (VLM)" },
  { key: "parsed", label: "Ghép trang" },
  { key: "chunking", label: "Chia đoạn + Contextual" },
  { key: "indexing", label: "Embedding + Index" },
  { key: "indexed", label: "Hoàn tất" },
];

export function stageIndex(status: DocStatus): number {
  return PIPELINE_STAGES.findIndex((s) => s.key === status);
}
