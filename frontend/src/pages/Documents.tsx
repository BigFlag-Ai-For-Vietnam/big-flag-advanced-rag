import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import {
  FileText, Trash2, RefreshCw, Eye, FileStack, UploadCloud,
  GitBranch, Ban, RotateCcw, X, Clock, Archive, ChevronDown, ChevronRight,
  ArrowRight, Database, SearchCheck, Info, Check, Network,
} from "lucide-react";
import {
  deleteDocument, getDocument, listDocuments, rebuildDocumentGraph, reprocessDocument,
  supersedeDocument, expireDocument, reactivateDocument, getVersionChain,
  type DocumentDetail, type DocumentSummary, type Lifecycle, type VersionChainItem,
} from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { GraphStatusBadge } from "../components/GraphStatus";
import Drawer from "../components/Drawer";
import CatalogTree from "../components/CatalogTree";
import { useToast } from "../lib/toast";
import { cn } from "../lib/cn";

const fmtDate = (s: string | null) => (s ? new Date(s).toLocaleDateString("vi-VN") : "–");
const docLabel = (d?: DocumentSummary | DocumentDetail | null) => d?.doc_no || d?.title || "Văn bản không còn tồn tại";
const today = () => new Date().toISOString().slice(0, 10);

export default function DocumentsPage() {
  const toast = useToast();
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [tab, setTab] = useState<"pages" | "chunks" | "catalog">("chunks");
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [superseding, setSuperseding] = useState<DocumentSummary | null>(null); // văn bản đang chọn bản thay thế
  const [replacement, setReplacement] = useState<DocumentSummary | null>(null);
  const [replacementDate, setReplacementDate] = useState("");
  const [replacementScope, setReplacementScope] = useState<"full" | "partial">("full");
  const [replacementNote, setReplacementNote] = useState("");
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [chain, setChain] = useState<VersionChainItem[]>([]);

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
    setChain([]);
    setDetail(await getDocument(id));
    try {
      setChain(await getVersionChain(id));
    } catch {
      /* timeline optional */
    }
  };

  const onExpire = async (d: DocumentSummary) => {
    if (!confirm(`Đánh dấu "${d.title}" HẾT HIỆU LỰC? (sẽ bị loại khỏi tìm kiếm)`)) return;
    setPendingId(d.id);
    try {
      await expireDocument(d.id);
      toast.push("info", "Đã đánh dấu hết hiệu lực.");
      refresh();
    } catch {
      toast.push("error", "Không thể cập nhật.");
    } finally {
      setPendingId(null);
    }
  };

  const onReactivate = async (d: DocumentSummary) => {
    setPendingId(d.id);
    try {
      await reactivateDocument(d.id);
      toast.push("success", "Đã kích hoạt lại (còn hiệu lực).");
      refresh();
    } catch {
      toast.push("error", "Không thể cập nhật.");
    } finally {
      setPendingId(null);
    }
  };

  const startSupersede = (doc: DocumentSummary) => {
    setSuperseding(doc);
    setReplacement(null);
    setReplacementDate("");
    setReplacementScope("full");
    setReplacementNote("");
  };

  const closeSupersede = () => {
    setSuperseding(null);
    setReplacement(null);
  };

  const selectReplacement = (doc: DocumentSummary) => {
    setReplacement(doc);
    setReplacementDate(doc.effective_date?.slice(0, 10) || today());
  };

  const doSupersede = async () => {
    if (!superseding || !replacement) return;
    if (replacementScope === "partial" && !replacementNote.trim()) {
      toast.push("error", "Cần ghi rõ phần vẫn còn hiệu lực khi thay thế một phần.");
      return;
    }
    setPendingId(superseding.id);
    try {
      const note = replacementScope === "partial"
        ? `Thay thế một phần: ${replacementNote.trim()}`
        : replacementNote.trim() || undefined;
      await supersedeDocument(superseding.id, replacement.id, {
        note,
        effectiveDate: replacementDate || undefined,
      });
      toast.push("success", `"${docLabel(superseding)}" đã được thay thế bởi "${docLabel(replacement)}".`);
      closeSupersede();
      await refresh();
    } catch {
      toast.push("error", "Thay thế thất bại.");
    } finally {
      setPendingId(null);
    }
  };

  const onDelete = async (d: DocumentSummary) => {
    if (!confirm(`Xoá "${d.title}"? (kèm pages, chunks, vectors trong Qdrant và Knowledge Graph)`)) return;
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

  const onGraphBuild = async (d: DocumentSummary) => {
    if (d.graph_status === "ready" && !confirm(`Build lại Knowledge Graph cho "${d.title}"? Graph cũ sẽ bị thay thế và thao tác này dùng LLM/token.`)) return;
    setPendingId(d.id);
    try {
      await rebuildDocumentGraph(d.id);
      toast.push("info", d.graph_status === "failed" ? "Đang retry Knowledge Graph…" : "Đang build Knowledge Graph…");
      await refresh();
    } catch (e: any) {
      toast.push("error", e?.response?.data?.detail || "Không thể build Knowledge Graph.");
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

  const activeDocs = docs.filter((d) => d.is_active);
  const archivedDocs = docs.filter((d) => !d.is_active);
  const retrievableDocs = activeDocs.filter((d) => d.status === "indexed");
  const activeChunks = retrievableDocs.reduce((sum, d) => sum + d.chunk_count, 0);
  const docsById = new Map(docs.map((d) => [d.id, d]));
  const detailSupersededBy = detail?.superseded_by_id
    ? docsById.get(detail.superseded_by_id)
    : undefined;
  const detailSupersedes = detail?.supersedes_id
    ? docsById.get(detail.supersedes_id)
    : undefined;
  const replacementCandidates = docs.filter(
    (d) => d.id !== superseding?.id && d.is_active && d.status === "indexed" && !d.supersedes_id,
  );

  return (
    <div className="animate-fade-in">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tài liệu</h1>
          <p className="mt-1.5 text-muted">
            Quản lý tài liệu đang được dùng để trả lời và hồ sơ đã lưu trữ.
          </p>
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
        <StatTile
          icon={SearchCheck}
          label="Đang tham gia retrieval"
          value={retrievableDocs.length}
          hint={`${activeChunks} chunks · ${activeDocs.length} tài liệu đang hiệu lực`}
          tone="emerald"
        />
        <StatTile
          icon={Archive}
          label="Tài liệu lưu trữ"
          value={archivedDocs.length}
          hint="Không được dùng để tạo câu trả lời"
          tone="amber"
        />
        <StatTile
          icon={FileStack}
          label="Tổng hồ sơ"
          value={docs.length}
          hint="Vẫn giữ pages, chunks và PDF để đối chiếu"
          tone="accent"
        />
      </div>

      {/* Danh sách được tách theo trạng thái tham gia retrieval. */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-[76px] animate-pulse rounded-xl border bg-surface-2/60" />
          ))}
        </div>
      ) : docs.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-6">
          <DocumentSection
            title="Đang hiệu lực"
            description="Các tài liệu trong nhóm này được phép tham gia dense search, BM25 và catalog retrieval."
            docs={activeDocs}
            docsById={docsById}
            pendingId={pendingId}
            onView={openDetail}
            onSupersede={startSupersede}
            onExpire={onExpire}
            onReactivate={onReactivate}
            onReprocess={onReprocess}
            onGraphBuild={onGraphBuild}
            onDelete={onDelete}
          />

          <section className="rounded-2xl border bg-surface/60">
            <button
              type="button"
              onClick={() => setArchiveOpen((value) => !value)}
              className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors hover:bg-surface-2/50"
              aria-expanded={archiveOpen}
            >
              <span className="grid size-9 place-items-center rounded-lg bg-amber-500/10 text-amber-500">
                <Archive className="size-4.5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2 font-semibold text-fg">
                  Lưu trữ
                  <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs tabular-nums text-muted">
                    {archivedDocs.length}
                  </span>
                </span>
                <span className="mt-0.5 block text-xs text-muted">
                  Vẫn giữ để xem lịch sử, nhưng bị loại khỏi retrieval mặc định.
                </span>
              </span>
              {archiveOpen ? <ChevronDown className="size-4 text-muted" /> : <ChevronRight className="size-4 text-muted" />}
            </button>
            {archiveOpen && (
              <div className="border-t p-3">
                <DocumentRows
                  docs={archivedDocs}
                  docsById={docsById}
                  pendingId={pendingId}
                  archived
                  onView={openDetail}
                  onSupersede={startSupersede}
                  onExpire={onExpire}
                  onReactivate={onReactivate}
                  onReprocess={onReprocess}
                  onGraphBuild={onGraphBuild}
                  onDelete={onDelete}
                />
              </div>
            )}
          </section>
        </div>
      )}

      {/* Detail drawer */}
      <Drawer
        open={!!detail}
        onClose={() => setDetail(null)}
        title={detail?.title}
        subtitle={
          detail && (
            <span className="flex items-center gap-2">
              {detail.status === "indexed" ? (
                <span className="inline-flex items-center gap-1.5 text-xs text-muted">
                  <Database className="size-3.5" /> Đã xử lý và lưu trữ
                </span>
              ) : (
                <StatusBadge status={detail.status} />
              )}
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
            {detail.graph_error_message && (
              <pre className="mb-4 overflow-x-auto whitespace-pre-wrap rounded-lg bg-rose-500/10 p-3 font-mono text-xs text-rose-500 ring-1 ring-inset ring-rose-500/25">
                Knowledge Graph: {detail.graph_error_message}
              </pre>
            )}

            {/* Hiệu lực + timeline phiên bản */}
            <div className="mb-4 rounded-xl border bg-surface-2/40 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
                  <VersionBadge lifecycle={detail.lifecycle} />
                  {detail.doc_no && <span className="font-mono">{detail.doc_no}</span>}
                  <span className="text-faint">·</span>
                  <span>Hiệu lực: {fmtDate(detail.effective_date)}</span>
                  {detail.expiry_date && <span>→ hết: {fmtDate(detail.expiry_date)}</span>}
                </div>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset",
                    detail.is_active
                      ? "bg-emerald-500/10 text-emerald-500 ring-emerald-500/25"
                      : "bg-amber-500/10 text-amber-500 ring-amber-500/25",
                  )}
                >
                  {detail.is_active ? <SearchCheck className="size-3.5" /> : <Ban className="size-3.5" />}
                  {detail.is_active ? "Được dùng trong retrieval" : "Không dùng trong retrieval"}
                </span>
              </div>

              {(detailSupersededBy || detailSupersedes) && (
                <div className="mt-3 grid gap-2 border-t pt-3 sm:grid-cols-2">
                  {detailSupersededBy && (
                    <RelationLink
                      label="Được thay thế bởi"
                      document={detailSupersededBy}
                      onClick={() => openDetail(detailSupersededBy.id)}
                    />
                  )}
                  {detailSupersedes && (
                    <RelationLink
                      label="Thay thế cho"
                      document={detailSupersedes}
                      onClick={() => openDetail(detailSupersedes.id)}
                    />
                  )}
                </div>
              )}

              {detail.supersession_note && (
                <div className="mt-3 flex gap-2 rounded-lg bg-amber-500/10 p-2.5 text-xs text-amber-600 ring-1 ring-inset ring-amber-500/20 dark:text-amber-400">
                  <Info className="mt-0.5 size-3.5 shrink-0" />
                  <p>
                    <span className="font-semibold">Ghi chú thay thế:</span> {detail.supersession_note}
                    {detail.supersession_note.startsWith("Thay thế một phần:") && (
                      <span className="mt-1 block">
                        Retrieval hiện vẫn loại ở cấp toàn bộ tài liệu; ngoại lệ này mới chỉ được lưu để đối chiếu.
                      </span>
                    )}
                  </p>
                </div>
              )}
              {chain.length > 1 && (
                <ol className="mt-3 space-y-2 border-t pt-3">
                  {chain.map((v) => (
                    <li key={v.id} className="flex items-center gap-2 text-xs">
                      <Clock className="size-3.5 shrink-0 text-faint" />
                      <span className="tabular-nums text-muted">{fmtDate(v.effective_date)}</span>
                      {v.version_label && (
                        <span className="font-mono text-faint">{v.version_label}</span>
                      )}
                      <span className={cn("truncate", v.id === detail.id && "font-semibold text-fg")}>
                        {v.doc_no || v.title}
                      </span>
                      <VersionBadge lifecycle={v.lifecycle} />
                    </li>
                  ))}
                </ol>
              )}
            </div>

            {/* Tabs */}
            <div className="mb-4 inline-flex rounded-lg border bg-surface-2/50 p-1">
              <TabBtn active={tab === "chunks"} onClick={() => setTab("chunks")}>
                Chunks ({detail.chunks.length})
              </TabBtn>
              <TabBtn active={tab === "pages"} onClick={() => setTab("pages")}>
                Trang ({detail.pages.length})
              </TabBtn>
              <TabBtn active={tab === "catalog"} onClick={() => setTab("catalog")}>
                Catalog ({detail.catalog?.tree.length ?? 0})
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
            ) : tab === "catalog" ? (
              <div className="space-y-3">
                {detail.focus_entities && detail.focus_entities.length > 0 && (
                  <p className="text-xs text-faint">
                    Facet đã chỉ định: {detail.focus_entities.join(" · ")}
                  </p>
                )}
                {detail.catalog && detail.catalog.tree.length > 0 ? (
                  <div className="rounded-lg border bg-surface p-4">
                    <CatalogTree nodes={detail.catalog.tree} />
                  </div>
                ) : (
                  <p className="py-8 text-center text-sm text-muted">
                    Chưa có catalog (chỉ sinh sau khi tài liệu được xử lý xong).
                  </p>
                )}
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

      {superseding && (
        <SupersedeModal
          oldDocument={superseding}
          candidates={replacementCandidates}
          selected={replacement}
          effectiveDate={replacementDate}
          scope={replacementScope}
          note={replacementNote}
          busy={pendingId === superseding.id}
          onClose={closeSupersede}
          onSelect={selectReplacement}
          onBack={() => setReplacement(null)}
          onEffectiveDateChange={setReplacementDate}
          onScopeChange={setReplacementScope}
          onNoteChange={setReplacementNote}
          onConfirm={doSupersede}
        />
      )}
    </div>
  );
}

interface DocumentRowsProps {
  docs: DocumentSummary[];
  docsById: Map<string, DocumentSummary>;
  pendingId: string | null;
  archived?: boolean;
  onView: (id: string) => void;
  onSupersede: (doc: DocumentSummary) => void;
  onExpire: (doc: DocumentSummary) => void;
  onReactivate: (doc: DocumentSummary) => void;
  onReprocess: (doc: DocumentSummary) => void;
  onGraphBuild: (doc: DocumentSummary) => void;
  onDelete: (doc: DocumentSummary) => void;
}

function DocumentSection({
  title,
  description,
  ...rowsProps
}: DocumentRowsProps & { title: string; description: string }) {
  return (
    <section>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 font-semibold text-fg">
            {title}
            <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs tabular-nums text-emerald-500">
              {rowsProps.docs.length}
            </span>
          </h2>
          <p className="mt-0.5 text-xs text-muted">{description}</p>
        </div>
      </div>
      <DocumentRows {...rowsProps} />
    </section>
  );
}

function DocumentRows({
  docs,
  docsById,
  pendingId,
  archived = false,
  onView,
  onSupersede,
  onExpire,
  onReactivate,
  onReprocess,
  onGraphBuild,
  onDelete,
}: DocumentRowsProps) {
  if (!docs.length) {
    return (
      <div className="rounded-xl border border-dashed px-4 py-8 text-center text-sm text-muted">
        {archived ? "Chưa có tài liệu lưu trữ." : "Chưa có tài liệu đang hiệu lực."}
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {docs.map((doc) => {
        const supersededBy = doc.superseded_by_id ? docsById.get(doc.superseded_by_id) : undefined;
        const supersedes = doc.supersedes_id ? docsById.get(doc.supersedes_id) : undefined;
        const pending = pendingId === doc.id;
        return (
          <li
            key={doc.id}
            className={cn(
              "rounded-xl border bg-surface p-4 shadow-sm transition-colors hover:border-accent/40",
              archived && "border-dashed bg-surface-2/25",
            )}
          >
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <span
                  className={cn(
                    "grid size-11 shrink-0 place-items-center rounded-lg",
                    archived ? "bg-amber-500/10 text-amber-500" : "bg-accent-soft text-accent",
                  )}
                >
                  {archived ? <Archive className="size-5" /> : <FileText className="size-5" />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 font-semibold text-fg">
                    {doc.doc_no && (
                      <span className="shrink-0 rounded-md bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted">
                        {doc.doc_no}
                      </span>
                    )}
                    <span className="truncate">{doc.title}</span>
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
                    <span className="tabular-nums">{doc.page_count ?? "–"} trang</span>
                    <span className="text-faint">·</span>
                    <span className="tabular-nums">{doc.chunk_count} chunks</span>
                    {doc.effective_date && (
                      <>
                        <span className="text-faint">·</span>
                        <span className="tabular-nums">Hiệu lực từ {fmtDate(doc.effective_date)}</span>
                      </>
                    )}
                  </div>
                  {(supersededBy || supersedes) && (
                    <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted">
                      <GitBranch className="size-3.5 text-amber-500" />
                      {supersededBy ? "Được thay thế bởi" : "Đang thay thế"}
                      <button
                        type="button"
                        onClick={() => onView((supersededBy || supersedes)!.id)}
                        className="font-semibold text-accent hover:underline"
                      >
                        {docLabel(supersededBy || supersedes)}
                      </button>
                    </p>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 xl:justify-end">
                <VersionBadge lifecycle={doc.lifecycle} />
                {doc.status === "indexed" ? (
                  <span className="inline-flex items-center gap-1 text-xs text-faint" title="Pipeline đã hoàn tất">
                    <Check className="size-3.5" /> Đã index
                  </span>
                ) : (
                  <StatusBadge status={doc.status} />
                )}
                <GraphStatusBadge
                  status={doc.graph_status}
                  eligible={doc.graph_eligible}
                  enabled={doc.graph_build_enabled}
                />
              </div>
            </div>

            <div className="mt-3 flex flex-col gap-3 border-t pt-3 md:flex-row md:items-center md:justify-between">
              <p
                className={cn(
                  "inline-flex items-center gap-1.5 text-xs font-medium",
                  doc.is_active ? "text-emerald-500" : "text-amber-500",
                )}
              >
                {doc.is_active ? <SearchCheck className="size-3.5" /> : <Archive className="size-3.5" />}
                {doc.is_active
                  ? "Được dùng để tạo câu trả lời"
                  : "Chỉ lưu để xem lịch sử · không tham gia retrieval"}
              </p>
              <div className="flex flex-wrap gap-2">
                <ActionButton icon={Eye} label="Xem chi tiết" disabled={pending} onClick={() => onView(doc.id)} />
                {doc.graph_eligible && (
                  <ActionButton
                    icon={Network}
                    label={doc.graph_status === "ready" ? "Build lại KG" : doc.graph_status === "failed" ? "Retry KG" : doc.graph_status === "building" ? "Đang build KG" : "Build KG"}
                    disabled={pending || !doc.graph_build_enabled || doc.graph_status === "building" || doc.status !== "indexed"}
                    spinning={doc.graph_status === "building"}
                    onClick={() => onGraphBuild(doc)}
                  />
                )}
                {doc.is_active && (
                  <>
                    <ActionButton icon={GitBranch} label="Chọn bản thay thế" disabled={pending} onClick={() => onSupersede(doc)} />
                    <ActionButton icon={Ban} label="Hết hiệu lực" tone="warning" disabled={pending} onClick={() => onExpire(doc)} />
                  </>
                )}
                {doc.lifecycle === "expired" && (
                  <ActionButton icon={RotateCcw} label="Kích hoạt lại" tone="success" disabled={pending} onClick={() => onReactivate(doc)} />
                )}
                <ActionButton
                  icon={RefreshCw}
                  label="Chạy lại pipeline"
                  disabled={pending}
                  spinning={pending}
                  onClick={() => onReprocess(doc)}
                />
                <ActionButton icon={Trash2} label="Xóa" tone="danger" disabled={pending} onClick={() => onDelete(doc)} />
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function RelationLink({
  label,
  document,
  onClick,
}: {
  label: string;
  document: DocumentSummary;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-w-0 items-center gap-2 rounded-lg border bg-surface px-3 py-2 text-left transition-colors hover:border-accent/40"
    >
      <GitBranch className="size-4 shrink-0 text-amber-500" />
      <span className="min-w-0 flex-1">
        <span className="block text-[11px] uppercase tracking-wide text-faint">{label}</span>
        <span className="block truncate text-xs font-semibold text-fg">{docLabel(document)}</span>
      </span>
      <ChevronRight className="size-3.5 shrink-0 text-faint" />
    </button>
  );
}

function ActionButton({
  icon: Icon,
  label,
  onClick,
  tone = "default",
  disabled,
  spinning,
}: {
  icon: any;
  label: string;
  onClick: () => void;
  tone?: "default" | "warning" | "success" | "danger";
  disabled?: boolean;
  spinning?: boolean;
}) {
  const tones = {
    default: "text-muted hover:border-accent/30 hover:bg-accent-soft hover:text-fg",
    warning: "text-amber-500 hover:border-amber-500/30 hover:bg-amber-500/10",
    success: "text-emerald-500 hover:border-emerald-500/30 hover:bg-emerald-500/10",
    danger: "text-rose-500 hover:border-rose-500/30 hover:bg-rose-500/10",
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors disabled:pointer-events-none disabled:opacity-40",
        tones[tone],
      )}
    >
      <Icon className={cn("size-3.5", spinning && "animate-spin")} />
      {label}
    </button>
  );
}

function SupersedeModal({
  oldDocument,
  candidates,
  selected,
  effectiveDate,
  scope,
  note,
  busy,
  onClose,
  onSelect,
  onBack,
  onEffectiveDateChange,
  onScopeChange,
  onNoteChange,
  onConfirm,
}: {
  oldDocument: DocumentSummary;
  candidates: DocumentSummary[];
  selected: DocumentSummary | null;
  effectiveDate: string;
  scope: "full" | "partial";
  note: string;
  busy: boolean;
  onClose: () => void;
  onSelect: (doc: DocumentSummary) => void;
  onBack: () => void;
  onEffectiveDateChange: (value: string) => void;
  onScopeChange: (value: "full" | "partial") => void;
  onNoteChange: (value: string) => void;
  onConfirm: () => void;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return createPortal(
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="supersede-title"
        className="max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-2xl border bg-surface shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-500">Quản lý hiệu lực</p>
            <h2 id="supersede-title" className="mt-1 text-lg font-bold text-fg">
              {selected ? "Xác nhận thay thế văn bản" : "Chọn văn bản thay thế"}
            </h2>
            <p className="mt-1 truncate text-sm text-muted">Bản cũ: {docLabel(oldDocument)}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="grid size-9 shrink-0 place-items-center rounded-lg border text-muted hover:bg-surface-2 hover:text-fg"
            aria-label="Đóng"
          >
            <X className="size-4" />
          </button>
        </header>

        {!selected ? (
          <div>
            <div className="flex gap-2 border-b bg-accent-soft px-5 py-3 text-xs text-muted">
              <Info className="mt-0.5 size-3.5 shrink-0 text-accent" />
              Chỉ hiển thị tài liệu đang hiệu lực, đã index và chưa thay thế một văn bản khác.
            </div>
            <ul className="scrollbar-thin max-h-[60vh] divide-y overflow-y-auto">
              {candidates.length === 0 ? (
                <li className="px-5 py-10 text-center text-sm text-muted">
                  Không có văn bản phù hợp để chọn làm bản thay thế.
                </li>
              ) : (
                candidates.map((candidate) => (
                  <li key={candidate.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(candidate)}
                      className="flex w-full items-center gap-3 px-5 py-3.5 text-left transition-colors hover:bg-surface-2"
                    >
                      <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                        <FileText className="size-4.5" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-fg">{docLabel(candidate)}</span>
                        <span className="mt-0.5 block text-xs text-muted">
                          {candidate.page_count ?? "–"} trang · {candidate.chunk_count} chunks · Hiệu lực {fmtDate(candidate.effective_date)}
                        </span>
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-accent">
                        Chọn <ChevronRight className="size-3.5" />
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        ) : (
          <div className="scrollbar-thin max-h-[72vh] overflow-y-auto p-5">
            <div className="grid items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
              <DocumentChoice label="Bản cũ — chuyển vào lưu trữ" document={oldDocument} tone="amber" />
              <ArrowRight className="mx-auto size-5 rotate-90 text-faint sm:rotate-0" />
              <DocumentChoice label="Bản mới — tiếp tục retrieval" document={selected} tone="emerald" />
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-fg">Ngày bản mới có hiệu lực</span>
                <input
                  type="date"
                  required
                  value={effectiveDate}
                  onChange={(event) => onEffectiveDateChange(event.target.value)}
                  className="w-full rounded-lg border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-accent"
                />
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-semibold text-fg">Phạm vi thay thế</span>
                <select
                  value={scope}
                  onChange={(event) => onScopeChange(event.target.value as "full" | "partial")}
                  className="w-full rounded-lg border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-accent"
                >
                  <option value="full">Toàn bộ tài liệu</option>
                  <option value="partial">Một phần / có ngoại lệ</option>
                </select>
              </label>
            </div>

            <label className="mt-4 block">
              <span className="mb-1.5 block text-xs font-semibold text-fg">
                {scope === "partial" ? "Phần vẫn còn hiệu lực (bắt buộc)" : "Ghi chú kiểm toán (không bắt buộc)"}
              </span>
              <textarea
                value={note}
                onChange={(event) => onNoteChange(event.target.value)}
                rows={3}
                placeholder={scope === "partial" ? "Ví dụ: Giữ hiệu lực Phụ lục 02 — Danh mục hệ thống trọng yếu" : "Lý do hoặc căn cứ thay thế…"}
                className="scrollbar-thin w-full resize-y rounded-lg border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-accent"
              />
            </label>

            <div className="mt-4 flex gap-2 rounded-lg bg-amber-500/10 p-3 text-xs text-amber-600 ring-1 ring-inset ring-amber-500/20 dark:text-amber-400">
              <Info className="mt-0.5 size-4 shrink-0" />
              <p>
                Bản cũ vẫn được giữ trong SQLite, Qdrant và kho PDF để đối chiếu, nhưng toàn bộ chunks sẽ bị loại khỏi retrieval mặc định.
                {scope === "partial" && (
                  <strong className="mt-1 block">
                    Hiện hệ thống chưa lọc đến cấp chunk; ngoại lệ chỉ được lưu làm ghi chú và chưa tự giữ phần đó trong retrieval.
                  </strong>
                )}
              </p>
            </div>

            <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
              <button
                type="button"
                onClick={onBack}
                disabled={busy}
                className="rounded-lg border px-3.5 py-2 text-sm font-medium text-muted hover:bg-surface-2 hover:text-fg disabled:opacity-40"
              >
                Chọn lại bản mới
              </button>
              <button
                type="button"
                onClick={onConfirm}
                disabled={busy || !effectiveDate || (scope === "partial" && !note.trim())}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600 disabled:pointer-events-none disabled:opacity-40"
              >
                {busy ? <RefreshCw className="size-4 animate-spin" /> : <GitBranch className="size-4" />}
                Xác nhận thay thế
              </button>
            </footer>
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

function DocumentChoice({
  label,
  document,
  tone,
}: {
  label: string;
  document: DocumentSummary;
  tone: "amber" | "emerald";
}) {
  return (
    <div
      className={cn(
        "min-w-0 rounded-xl border p-3",
        tone === "amber" ? "border-amber-500/25 bg-amber-500/8" : "border-emerald-500/25 bg-emerald-500/8",
      )}
    >
      <p className={cn("text-[11px] font-semibold uppercase tracking-wide", tone === "amber" ? "text-amber-500" : "text-emerald-500")}>
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-fg">{docLabel(document)}</p>
      <p className="mt-0.5 text-xs text-muted">{document.chunk_count} chunks</p>
    </div>
  );
}

function VersionBadge({ lifecycle }: { lifecycle: Lifecycle }) {
  const map: Record<Lifecycle, { label: string; cls: string }> = {
    active: {
      label: "● Đang hiệu lực",
      cls: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-emerald-500/25",
    },
    superseded: {
      label: "↳ Bị thay thế",
      cls: "bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-amber-500/25",
    },
    expired: {
      label: "◌ Hết hiệu lực",
      cls: "bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 ring-zinc-500/25",
    },
  };
  const { label, cls } = map[lifecycle] ?? map.active;
  return (
    <span
      className={cn(
        "shrink-0 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        cls
      )}
    >
      {label}
    </span>
  );
}

function StatTile({
  icon: Icon,
  label,
  value,
  hint,
  tone = "muted",
}: {
  icon: any;
  label: string;
  value: number;
  hint?: string;
  tone?: "muted" | "emerald" | "amber" | "accent";
}) {
  const toneCls =
    tone === "emerald"
      ? "text-emerald-500"
      : tone === "amber"
        ? "text-amber-500"
        : tone === "accent"
          ? "text-accent"
          : "text-muted";
  return (
    <div className="rounded-xl border bg-surface p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted">
        <Icon className={cn("size-4", toneCls)} />
        {label}
      </div>
      <p className="mt-1.5 text-2xl font-bold tabular-nums">{value}</p>
      {hint && <p className="mt-1 text-xs leading-relaxed text-faint">{hint}</p>}
    </div>
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
