import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText, Trash2, RefreshCw, Eye, FileStack, Boxes, UploadCloud, Layers,
} from "lucide-react";
import {
  deleteDocument, getDocument, listDocuments, reprocessDocument,
  type DocumentDetail, type DocumentSummary,
} from "../api/client";
import StatusBadge from "../components/StatusBadge";
import Drawer from "../components/Drawer";
import { useToast } from "../lib/toast";
import { cn } from "../lib/cn";

export default function DocumentsPage() {
  const toast = useToast();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [tab, setTab] = useState<"pages" | "chunks">("chunks");
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setDocs(await listDocuments());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, 4000); // theo dõi trạng thái pipeline
    return () => window.clearInterval(t);
  }, []);

  const openDetail = async (id: string) => {
    setTab("chunks");
    setDetail(await getDocument(id));
  };

  const onDelete = async (d: DocumentSummary) => {
    if (!confirm(`Xoá "${d.title}"? (kèm pages, chunks và vectors trong Qdrant)`)) return;
    setPendingId(d.id);
    try {
      await deleteDocument(d.id);
      if (detail?.id === d.id) setDetail(null);
      toast.push("success", "Đã xoá tài liệu.");
      refresh();
    } catch {
      toast.push("error", "Xoá thất bại.");
    } finally {
      setPendingId(null);
    }
  };

  const onReprocess = async (d: DocumentSummary) => {
    setPendingId(d.id);
    try {
      await reprocessDocument(d.id);
      toast.push("info", "Đang chạy lại pipeline…");
      refresh();
    } catch {
      toast.push("error", "Không thể chạy lại.");
    } finally {
      setPendingId(null);
    }
  };

  const totalChunks = docs.reduce((s, d) => s + d.chunk_count, 0);
  const indexed = docs.filter((d) => d.status === "indexed").length;

  return (
    <div className="animate-fade-in">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tài liệu</h1>
          <p className="mt-1.5 text-muted">Kho tri thức đã nạp vào hệ thống.</p>
        </div>
        <Link
          to="/upload"
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 active:scale-[0.98]"
        >
          <UploadCloud className="size-4" /> Tải lên PDF
        </Link>
      </header>

      {/* Stat tiles */}
      <div className="mb-6 grid grid-cols-3 gap-3">
        <StatTile icon={FileStack} label="Tài liệu" value={docs.length} />
        <StatTile icon={Boxes} label="Đã index" value={indexed} tone="emerald" />
        <StatTile icon={Layers} label="Tổng chunks" value={totalChunks} tone="accent" />
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-[76px] animate-pulse rounded-xl border bg-surface-2/60" />
          ))}
        </div>
      ) : docs.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="space-y-3">
          {docs.map((d) => (
            <li
              key={d.id}
              className="group flex items-center gap-4 rounded-xl border bg-surface p-4 shadow-sm transition-colors hover:border-accent/40"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                <FileText className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-fg">{d.title}</p>
                <p className="mt-0.5 flex items-center gap-2 text-xs text-muted">
                  <span className="tabular-nums">{d.page_count ?? "–"} trang</span>
                  <span className="text-faint">·</span>
                  <span className="tabular-nums">{d.chunk_count} chunks</span>
                </p>
              </div>
              <StatusBadge status={d.status} />
              <div className="flex items-center gap-1">
                <IconBtn label="Xem" onClick={() => openDetail(d.id)}>
                  <Eye className="size-4" />
                </IconBtn>
                <IconBtn
                  label="Chạy lại"
                  disabled={pendingId === d.id}
                  onClick={() => onReprocess(d)}
                >
                  <RefreshCw className={cn("size-4", pendingId === d.id && "animate-spin")} />
                </IconBtn>
                <IconBtn label="Xoá" danger disabled={pendingId === d.id} onClick={() => onDelete(d)}>
                  <Trash2 className="size-4" />
                </IconBtn>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Detail drawer */}
      <Drawer
        open={!!detail}
        onClose={() => setDetail(null)}
        title={detail?.title}
        subtitle={
          detail && (
            <span className="flex items-center gap-2">
              <StatusBadge status={detail.status} />
              <span className="font-mono text-xs text-faint">{detail.id.slice(0, 8)}</span>
            </span>
          )
        }
      >
        {detail && (
          <>
            {detail.error_message && (
              <pre className="mb-4 overflow-x-auto whitespace-pre-wrap rounded-lg bg-rose-500/10 p-3 font-mono text-xs text-rose-500 ring-1 ring-inset ring-rose-500/25">
                {detail.error_message}
              </pre>
            )}

            {/* Tabs */}
            <div className="mb-4 inline-flex rounded-lg border bg-surface-2/50 p-1">
              <TabBtn active={tab === "chunks"} onClick={() => setTab("chunks")}>
                Chunks ({detail.chunks.length})
              </TabBtn>
              <TabBtn active={tab === "pages"} onClick={() => setTab("pages")}>
                Trang ({detail.pages.length})
              </TabBtn>
            </div>

            {tab === "pages" ? (
              <div className="space-y-2.5">
                {detail.pages.map((p) => (
                  <details key={p.id} className="group rounded-lg border bg-surface">
                    <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-sm font-medium">
                      <span>Trang {p.page_number}</span>
                      <span className="font-mono text-xs text-faint">
                        {(p.parsed_text ?? "").length} ký tự
                      </span>
                    </summary>
                    <pre className="scrollbar-thin max-h-96 overflow-auto whitespace-pre-wrap border-t px-4 py-3 font-mono text-xs leading-relaxed text-muted">
                      {p.parsed_text || "(trống)"}
                    </pre>
                  </details>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {detail.chunks.map((c) => (
                  <div key={c.id} className="rounded-lg border bg-surface p-4">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="rounded-md bg-accent-soft px-2 py-0.5 font-mono text-xs font-semibold text-accent">
                        chunk #{c.chunk_index}
                      </span>
                      <span className="font-mono text-xs text-faint">
                        {c.raw_text.length} ký tự · ~{c.token_count} từ
                      </span>
                    </div>
                    {c.contextual_prefix && (
                      <p className="mark-context mb-2 rounded px-2.5 py-1.5 text-sm leading-snug">
                        <span className="font-semibold">Câu định vị: </span>
                        {c.contextual_prefix}
                      </p>
                    )}
                    <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted">
                      {c.raw_text}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  tone = "muted",
}: {
  icon: any;
  label: string;
  value: number;
  tone?: "muted" | "emerald" | "accent";
}) {
  const toneCls =
    tone === "emerald" ? "text-emerald-500" : tone === "accent" ? "text-accent" : "text-muted";
  return (
    <div className="rounded-xl border bg-surface p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted">
        <Icon className={cn("size-4", toneCls)} />
        {label}
      </div>
      <p className="mt-1.5 text-2xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

function IconBtn({
  children,
  label,
  onClick,
  danger,
  disabled,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className={cn(
        "grid size-9 place-items-center rounded-lg border text-muted transition-colors disabled:opacity-40",
        danger ? "hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-500" : "hover:bg-surface-2 hover:text-fg"
      )}
    >
      {children}
    </button>
  );
}

function TabBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-surface text-fg shadow-sm" : "text-muted hover:text-fg"
      )}
    >
      {children}
    </button>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed bg-surface py-16 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-surface-2 text-muted">
        <FileStack className="size-7" />
      </span>
      <p className="mt-4 font-semibold text-fg">Chưa có tài liệu nào</p>
      <p className="mt-1 text-sm text-muted">Tải lên một PDF để bắt đầu xây dựng kho tri thức.</p>
      <Link
        to="/upload"
        className="mt-5 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110"
      >
        <UploadCloud className="size-4" /> Tải lên PDF
      </Link>
    </div>
  );
}
