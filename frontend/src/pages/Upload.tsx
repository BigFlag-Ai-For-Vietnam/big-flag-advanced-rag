import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight, RotateCcw } from "lucide-react";
import { getStatus, uploadDocument, type DocStatus } from "../api/client";
import { STATUS_META } from "../lib/status";
import Dropzone from "../components/Dropzone";
import PipelineStepper from "../components/PipelineStepper";
import { useToast } from "../lib/toast";
import { cn } from "../lib/cn";

const TERMINAL: DocStatus[] = ["indexed", "failed"];

export default function UploadPage() {
  const nav = useNavigate();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [status, setStatus] = useState<DocStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => () => void (timer.current && window.clearInterval(timer.current)), []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const s = await getStatus(id);
        setStatus(s.status);
        setError(s.error_message);
        if (TERMINAL.includes(s.status)) {
          if (timer.current) window.clearInterval(timer.current);
          if (s.status === "indexed") toast.push("success", "Xử lý tài liệu hoàn tất!");
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
      const doc = await uploadDocument(file);
      setDocId(doc.id);
      setStatus(doc.status);
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
                Tài liệu đã sẵn sàng để hỏi–đáp.
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
              <PipelineStepper status={status} />
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
