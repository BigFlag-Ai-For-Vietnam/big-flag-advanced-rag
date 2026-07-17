import { useRef, useState } from "react";
import { Send, Sparkles, Quote, FileText, Wrench, ListTree, Search } from "lucide-react";
import {
  API_BASE_URL,
  mcpRetrieve,
  type Citation,
  type McpRetrieveConfig,
  type ToolCallTrace,
} from "../api/client";
import { cn } from "../lib/cn";

const SUGGESTIONS = [
  "Quyền lợi bảo hiểm chính là gì?",
  "Các trường hợp loại trừ bảo hiểm?",
  "Trách nhiệm của bên mua bảo hiểm?",
];

export default function PlaygroundPage() {
  const [tab, setTab] = useState<"qa" | "mcp">("qa");
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

      {/* Tab switcher */}
      <div className="mb-4 inline-flex rounded-xl border bg-surface p-1">
        <button
          onClick={() => setTab("qa")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
            tab === "qa" ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"
          )}
        >
          <Sparkles className="size-3.5" /> Hỏi đáp
        </button>
        <button
          onClick={() => setTab("mcp")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm font-medium transition-colors",
            tab === "mcp" ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"
          )}
        >
          <Wrench className="size-3.5" /> MCP Playground
        </button>
      </div>

      {tab === "mcp" && <McpPlaygroundPanel />}

      {tab === "qa" && (
      <>
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
          {citations.length > 0 && <CitationList citations={citations} />}
        </div>
      )}
      </>
      )}
    </div>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  return (
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
  );
}

function McpPlaygroundPanel() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [normalizedQuestion, setNormalizedQuestion] = useState("");
  const [rewrittenQuestion, setRewrittenQuestion] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCallTrace[]>([]);
  const [config, setConfig] = useState<McpRetrieveConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const testRetrieve = async () => {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setAsked(q);
    setError(null);
    setCitations([]);
    setToolCalls([]);
    try {
      const res = await mcpRetrieve(q, topK);
      setCitations(res.citations);
      setNormalizedQuestion(res.normalized_question);
      setRewrittenQuestion(res.rewritten_question);
      setToolCalls(res.tool_calls);
      setConfig(res.config);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <p className="mb-4 text-sm text-muted">
        Gọi thẳng tool <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-xs">retrieve</code> của
        Retrieval Engine qua MCP — chỉ trả về citation thô, không sinh câu trả lời. Dùng để test/debug riêng
        chất lượng retrieval (đổi <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-xs">RETRIEVAL_ENABLE_*</code>{" "}
        trong .env rồi gọi lại để so sánh ảnh hưởng của từng bước).
      </p>

      <div className="rounded-2xl border bg-surface p-4 shadow-sm">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) testRetrieve();
          }}
          placeholder="Nhập câu hỏi để test retrieval…  (Ctrl/⌘ + Enter để gửi)"
          className="min-h-20 w-full resize-y bg-transparent text-[15px] leading-relaxed text-fg outline-none placeholder:text-faint"
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
            onClick={testRetrieve}
            disabled={busy || !question.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
          >
            {busy ? <Sparkles className="size-4 animate-pulse" /> : <Wrench className="size-4" />}
            {busy ? "Đang retrieve…" : "Test retrieve"}
          </button>
        </div>
      </div>

      {(asked || busy) && (
        <div className="mt-5 space-y-4">
          {config && (
            <div className="flex flex-wrap gap-2">
              <ConfigBadge label="normalize" on={config.normalize} />
              <ConfigBadge label="rewrite" on={config.rewrite} />
              <ConfigBadge label="rerank" on={config.rerank} />
              <span className="rounded-full border bg-surface px-3 py-1 font-mono text-xs text-muted">
                max_steps={config.agent_max_steps}
              </span>
            </div>
          )}

          {error ? (
            <div className="rounded-2xl border bg-surface p-5 shadow-sm">
              <p className="text-sm font-medium text-rose-500">{error}</p>
            </div>
          ) : busy ? (
            <p className="text-sm text-muted">Đang gọi Retrieval Engine…</p>
          ) : (
            <>
              <div className="rounded-2xl border bg-surface p-5 shadow-sm">
                <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
                  <ListTree className="size-3.5" /> Pipeline trace
                </p>
                <div className="space-y-2.5 text-sm">
                  <TraceRow label="Câu hỏi gốc" value={asked} />
                  <TraceRow label="Sau normalize" value={normalizedQuestion} muted={normalizedQuestion === asked} />
                  <TraceRow label="Sau rewrite" value={rewrittenQuestion} muted={rewrittenQuestion === normalizedQuestion} />
                </div>

                {toolCalls.length > 0 && (
                  <div className="mt-4 space-y-1.5 border-t pt-3">
                    {toolCalls.map((tc, i) => (
                      <div key={i} className="flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-2 text-xs">
                        <Search className="size-3.5 shrink-0 text-accent" />
                        <span className="font-mono font-semibold text-fg">{tc.tool}</span>
                        <span className="min-w-0 flex-1 truncate font-mono text-faint">
                          {JSON.stringify(tc.args)}
                        </span>
                        <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 font-mono text-faint">
                          {tc.hit_count} hit{tc.hit_count === 1 ? "" : "s"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {citations.length > 0 ? (
                <CitationList citations={citations} />
              ) : (
                <p className="text-sm text-muted">Không có citation nào (retrieval trả về rỗng).</p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TraceRow({ label, value, muted }: { label: string; value: string | null; muted?: boolean }) {
  return (
    <div className="flex gap-3">
      <span className="w-28 shrink-0 text-faint">{label}</span>
      <span className={cn("min-w-0 flex-1 break-words", muted ? "text-faint" : "text-fg")}>{value}</span>
    </div>
  );
}

function ConfigBadge({ label, on }: { label: string; on: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full border px-3 py-1 font-mono text-xs",
        on ? "border-accent/40 bg-accent-soft text-accent" : "bg-surface text-faint"
      )}
    >
      {label}: {on ? "ON" : "OFF"}
    </span>
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
