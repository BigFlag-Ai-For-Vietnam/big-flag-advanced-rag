import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight, RotateCcw, Tags } from "lucide-react";
import {
  getCatalogPresets,
  getStatus,
  uploadDocument,
  type CatalogPreset,
  type DocStatus,
  type GraphStatus,
} from "../api/client";
import { STATUS_META } from "../lib/status";
import Dropzone from "../components/Dropzone";
import PipelineStepper from "../components/PipelineStepper";
import GraphStatusPanel from "../components/GraphStatus";
import { useToast } from "../lib/toast";
import { cn } from "../lib/cn";

const TERMINAL: DocStatus[] = ["indexed", "failed"];

// Chuyển textarea (mỗi dòng 1 facet) <-> mảng.
const linesToList = (t: string) => t.split("\n").map((s) => s.trim()).filter(Boolean);

export default function UploadPage() {
  const nav = useNavigate();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [status, setStatus] = useState<DocStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [graphStatus, setGraphStatus] = useState<GraphStatus>("not_built");
  const [graphError, setGraphError] = useState<string | null>(null);
  const [graphEligible, setGraphEligible] = useState(false);
  const [graphEnabled, setGraphEnabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  // Catalog config: category preset + danh sách facet-entities (sửa được).
  const [presets, setPresets] = useState<CatalogPreset[]>([]);
  const [category, setCategory] = useState<string>("");
  const [entitiesText, setEntitiesText] = useState<string>("");

  useEffect(() => {
    getCatalogPresets()
      .then((ps) => {
        setPresets(ps);
        if (ps.length) {
          setCategory(ps[0].key);
          setEntitiesText(ps[0].entities.join("\n"));
        }
      })
      .catch(() => {});
  }, []);

  const onCategoryChange = (key: string) => {
    setCategory(key);
    const preset = presets.find((p) => p.key === key);
    // prefill facet-entities theo preset (user vẫn sửa được sau đó)
    if (preset) setEntitiesText(preset.entities.join("\n"));
  };

  useEffect(() => () => void (timer.current && window.clearInterval(timer.current)), []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const s = await getStatus(id);
        setStatus(s.status);
        setError(s.error_message);
        setGraphStatus(s.graph_status);
        setGraphError(s.graph_error_message);
        setGraphEligible(s.graph_eligible);
        setGraphEnabled(s.graph_build_enabled);
        const vectorTerminal = TERMINAL.includes(s.status);
        const graphExpected = s.graph_eligible && s.graph_build_enabled;
        const graphTerminal = !graphExpected
          || s.graph_status === "ready"
          || s.graph_status === "failed"
          || (s.status === "failed" && s.graph_status === "not_built");
        if (vectorTerminal && graphTerminal) {
          if (timer.current) window.clearInterval(timer.current);
          if (s.status === "indexed" && s.graph_status === "ready")
            toast.push("success", "Vector Store và Knowledge Graph đã sẵn sàng!");
          else if (s.status === "indexed")
            toast.push("success", "Vector Store đã sẵn sàng.");
          if (s.status === "failed") toast.push("error", "Pipeline gặp lỗi khi xử lý.");
        }
      } catch {
        /* transient */
      }
    }, 1800);
  };

  const onUpload = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const doc = await uploadDocument(file, {
        category: category || null,
        focusEntities: linesToList(entitiesText),
      });
      setDocId(doc.id);
      setStatus(doc.status);
      setGraphStatus(doc.graph_status);
      setGraphError(doc.graph_error_message);
      setGraphEligible(doc.graph_eligible);
      setGraphEnabled(doc.graph_build_enabled);
      toast.push("info", "Đã tải lên, pipeline bắt đầu chạy…");
      poll(doc.id);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || String(e);
      setError(msg);
      toast.push("error", msg);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    if (timer.current) window.clearInterval(timer.current);
    setFile(null);
    setDocId(null);
    setStatus(null);
    setError(null);
    setGraphStatus("not_built");
    setGraphError(null);
    setGraphEligible(false);
    setGraphEnabled(false);
  };

  const done = status === "indexed";

  return (
    <div className="animate-fade-in">
      <header className="mb-7">
        <h1 className="text-2xl font-bold tracking-tight">Tải lên tài liệu</h1>
        <p className="mt-1.5 text-muted">
          Upload PDF → phân tích bằng VLM → chia đoạn + contextual → lập chỉ mục vào Qdrant.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-5">
        {/* Upload card */}
        <section className="lg:col-span-3">
          <div className="rounded-2xl border bg-surface p-5 shadow-sm">
            <Dropzone file={file} onFile={setFile} disabled={busy || (!!status && !done && status !== "failed")} />

            {/* Catalog config: category + facet-entities (dùng để sinh catalog) */}
            <div className="mt-5 border-t pt-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-fg">
                <Tags className="size-4 text-accent" /> Loại tài liệu & facet cần tách
              </div>
              <label className="mb-3 block">
                <span className="mb-1.5 block text-xs font-medium text-muted">Loại tài liệu (preset)</span>
                <select
                  value={category}
                  onChange={(e) => onCategoryChange(e.target.value)}
                  disabled={busy}
                  className="w-full rounded-lg border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-accent"
                >
                  {presets.map((p) => (
                    <option key={p.key} value={p.key}>{p.label}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-muted">
                  Facet-entities LLM cần focus (mỗi dòng 1 facet — sửa tuỳ ý)
                </span>
                <textarea
                  value={entitiesText}
                  onChange={(e) => setEntitiesText(e.target.value)}
                  disabled={busy}
                  rows={6}
                  className="scrollbar-thin w-full resize-y rounded-lg border bg-surface px-3 py-2 text-sm leading-relaxed text-fg outline-none focus:border-accent"
                />
              </label>
              <p className="mt-1.5 text-xs text-faint">
                Catalog sinh từ các facet này (chỉ tên mục, không có số liệu) sẽ đính vào tài liệu để agent trả lời chính xác hơn.
              </p>
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={onUpload}
                disabled={!file || busy || (!!status && !TERMINAL.includes(status))}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all",
                  "hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
                )}
              >
                <Sparkles className="size-4" />
                {busy ? "Đang tải lên…" : "Bắt đầu xử lý"}
              </button>
              {(docId || file) && (
                <button
                  onClick={reset}
                  className="inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-surface-2 hover:text-fg"
                >
                  <RotateCcw className="size-4" />
                  Làm mới
                </button>
              )}
            </div>
          </div>

          {done && (
            <div className="animate-fade-in mt-4 flex items-center justify-between gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3.5">
              <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                Vector Store đã sẵn sàng để hỏi–đáp
                {graphEligible && graphEnabled && graphStatus === "building"
                  ? "; Knowledge Graph vẫn đang được bổ sung."
                  : "."}
              </p>
              <button
                onClick={() => nav("/playground")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-semibold text-white transition-transform hover:scale-[1.02]"
              >
                Tới Playground <ArrowRight className="size-4" />
              </button>
            </div>
          )}

          {error && (
            <div className="animate-fade-in mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3">
              <p className="text-sm font-semibold text-rose-500">Chi tiết lỗi</p>
              <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap font-mono text-xs text-rose-500/90">
                {error}
              </pre>
            </div>
          )}
        </section>

        {/* Pipeline progress */}
        <section className="lg:col-span-2">
          <div className="rounded-2xl border bg-surface p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Tiến trình</h2>
              {status && (
                <span className={cn("font-mono text-xs", STATUS_META[status] && "text-muted")}>
                  {docId?.slice(0, 8)}
                </span>
              )}
            </div>
            {status ? (
              <div className="space-y-5">
                <div>
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Vector Store</p>
                  <PipelineStepper status={status} />
                </div>
                <div className="border-t pt-4">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">Knowledge Graph</p>
                  <GraphStatusPanel
                    status={graphStatus}
                    eligible={graphEligible}
                    enabled={graphEnabled}
                    error={graphError}
                  />
                </div>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted">
                Chọn một file PDF và bắt đầu để theo dõi pipeline tại đây.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
