import { useRef, useState } from "react";
import { Send, Sparkles, Quote, FileText } from "lucide-react";
import { API_BASE_URL, type Citation } from "../api/client";
import { cn } from "../lib/cn";

const SUGGESTIONS = [
  "Quyền lợi bảo hiểm chính là gì?",
  "Các trường hợp loại trừ bảo hiểm?",
  "Trách nhiệm của bên mua bảo hiểm?",
];

export default function PlaygroundPage() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const streaming = useRef(false);

  const ask = async (q?: string) => {
    const query = (q ?? question).trim();
    if (!query || busy) return;
    setBusy(true);
    setAsked(query);
    setAnswer("");
    setCitations([]);
    setError(null);
    streaming.current = true;

    try {
      const resp = await fetch(`${API_BASE_URL}/api/playground/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query, top_k: topK, stream: true }),
      });
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") continue;
          try {
            const evt = JSON.parse(data);
            if (evt.type === "citations") setCitations(evt.citations);
            else if (evt.type === "token") setAnswer((p) => p + evt.content);
            else if (evt.type === "error") setError(evt.message);
          } catch {
            /* skip */
          }
        }
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      streaming.current = false;
      setBusy(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">Playground</h1>
        <p className="mt-1.5 text-muted">Hỏi–đáp trên kho tri thức, có trích dẫn nguồn.</p>
      </header>

      {/* Composer */}
      <div className="rounded-2xl border bg-surface p-4 shadow-sm">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask();
          }}
          placeholder="Nhập câu hỏi về tài liệu đã index…  (Ctrl/⌘ + Enter để gửi)"
          className="min-h-24 w-full resize-y bg-transparent text-[15px] leading-relaxed text-fg outline-none placeholder:text-faint"
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t pt-3">
          <label className="flex items-center gap-2.5 text-sm text-muted">
            <span className="font-medium">top_k</span>
            <input
              type="range"
              min={1}
              max={12}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="accent-accent"
            />
            <span className="w-6 text-center font-mono tabular-nums text-fg">{topK}</span>
          </label>
          <button
            onClick={() => ask()}
            disabled={busy || !question.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
          >
            {busy ? <Sparkles className="size-4 animate-pulse" /> : <Send className="size-4" />}
            {busy ? "Đang trả lời…" : "Gửi câu hỏi"}
          </button>
        </div>
      </div>

      {/* Suggestions (khi chưa hỏi) */}
      {!asked && (
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQuestion(s);
                ask(s);
              }}
              className="rounded-full border bg-surface px-3.5 py-1.5 text-sm text-muted transition-colors hover:border-accent/40 hover:text-fg"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Answer */}
      {(asked || busy) && (
        <div className="mt-5 space-y-4">
          <div className="rounded-2xl border bg-surface p-5 shadow-sm">
            <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
              <Quote className="size-3.5" /> Câu hỏi
            </p>
            <p className="text-fg">{asked}</p>

            <div className="my-4 h-px bg-border" />

            <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
              <Sparkles className="size-3.5 text-accent" /> Trả lời
            </p>
            {error ? (
              <p className="text-sm font-medium text-rose-500">{error}</p>
            ) : (
              <div
                className={cn(
                  "whitespace-pre-wrap text-[15px] leading-relaxed text-fg",
                  busy && !answer && "text-muted",
                  busy && "caret-blink"
                )}
              >
                {answer || (busy ? "Đang truy hồi ngữ cảnh và soạn câu trả lời" : "")}
              </div>
            )}
          </div>

          {/* Citations */}
          {citations.length > 0 && (
            <div>
              <p className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-fg">
                <FileText className="size-4 text-accent" /> Nguồn ({citations.length})
              </p>
              <div className="space-y-2.5">
                {citations.map((c, i) => (
                  <details key={i} className="rounded-xl border bg-surface shadow-sm">
                    <summary className="flex cursor-pointer items-center gap-3 px-4 py-3">
                      <span className="grid size-6 shrink-0 place-items-center rounded-md bg-accent-soft font-mono text-xs font-bold text-accent">
                        {i + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-fg">{c.title}</span>
                        <span className="font-mono text-xs text-faint">đoạn #{c.chunk_index}</span>
                      </span>
                      <ScoreBar score={c.score} />
                    </summary>
                    <p className="scrollbar-thin max-h-72 overflow-auto whitespace-pre-wrap border-t px-4 py-3 text-sm leading-relaxed text-muted">
                      {c.final_content}
                    </p>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  return (
    <span className="flex shrink-0 items-center gap-2" title={`Relevance ${score.toFixed(3)}`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
        <span
          className="block h-full rounded-full bg-highlight"
          style={{ width: `${pct}%` }}
        />
      </span>
      <span className="w-9 text-right font-mono text-xs tabular-nums text-highlight">
        {score.toFixed(2)}
      </span>
    </span>
  );
}
