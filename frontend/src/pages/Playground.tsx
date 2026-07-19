import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, Quote, Network, Wrench, ListTree, Search, Square } from "lucide-react";
import {
  API_BASE_URL,
  type CatalogInfo,
  type Citation,
  type GraphFact,
  type McpRetrieveConfig,
  type SubgoalCoverage,
  type ToolCallTrace,
  type ProgressEvent,
  type McpRetrieveResponse,
} from "../api/client";
import { cn } from "../lib/cn";
import CatalogTree from "../components/CatalogTree";
import { CitationList, CoveragePanel } from "../components/RetrievalEvidence";
import GraphEvidence from "../components/GraphEvidence";
import AgentActivity from "../components/AgentActivity";
import AnswerMarkdown from "../components/AnswerMarkdown";
import { consumeSse } from "../lib/sse";
import { upsertProgress } from "../lib/progress";
import { useSmoothText } from "../lib/useSmoothText";

const SUGGESTIONS = [
  "Mật khẩu đăng nhập hệ thống nội bộ tối thiểu bao nhiêu ký tự?",
  "Phiên làm việc tự động khóa sau bao nhiêu phút?",
  "Hồ sơ nhận biết khách hàng (KYC) phải lưu trữ bao lâu?",
  "DDB có được dùng dữ liệu khách hàng để huấn luyện AI không?",
];

export default function PlaygroundPage() {
  const [tab, setTab] = useState<"qa" | "mcp">("qa");
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [graphFacts, setGraphFacts] = useState<GraphFact[]>([]);
  const [catalogs, setCatalogs] = useState<CatalogInfo[]>([]);
  const [coverage, setCoverage] = useState<SubgoalCoverage[]>([]);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const smoothAnswer = useSmoothText((text) => setAnswer((previous) => previous + text));

  useEffect(() => {
    if (tab !== "qa") controllerRef.current?.abort();
  }, [tab]);
  useEffect(() => () => controllerRef.current?.abort(), []);

  const ask = async (q?: string) => {
    const query = (q ?? question).trim();
    if (!query || busy) return;
    setBusy(true);
    setAsked(query);
    setAnswer("");
    setCitations([]);
    setGraphFacts([]);
    setCatalogs([]);
    setCoverage([]);
    setProgress([]);
    setError(null);
    smoothAnswer.reset();
    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      await consumeSse(
        `${API_BASE_URL}/api/playground/query`,
        { question: query, top_k: topK, stream: true },
        controller.signal,
        (evt) => {
          if (evt.type === "progress") setProgress((old) => upsertProgress(old, evt));
          else if (evt.type === "citations") setCitations(evt.citations);
          else if (evt.type === "graph_facts") setGraphFacts(evt.graph_facts);
          else if (evt.type === "catalogs") setCatalogs(evt.catalogs);
          else if (evt.type === "coverage") setCoverage(evt.subgoals);
          else if (evt.type === "token") smoothAnswer.push(evt.content ?? "");
          else if (evt.type === "error") setError(evt.message);
        },
      );
      smoothAnswer.flush();
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setError(e?.message || String(e));
    } finally {
      smoothAnswer.flush();
      setBusy(false);
      controllerRef.current = null;
    }
  };

  const cancel = () => {
    controllerRef.current?.abort();
    smoothAnswer.flush();
    setBusy(false);
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
            onClick={() => busy ? cancel() : ask()}
            disabled={!busy && !question.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
          >
            {busy ? <Square className="size-3.5 fill-current" /> : <Send className="size-4" />}
            {busy ? "Hủy" : "Gửi câu hỏi"}
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

            <AgentActivity events={progress} active={busy} />

            <p className="mb-3 mt-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
              <Sparkles className="size-3.5 text-accent" /> Trả lời
            </p>
            {error ? (
              <p className="text-sm font-medium text-rose-500">{error}</p>
            ) : (
              <div
                className={cn(
                  busy && !answer && "text-muted",
                  busy && "caret-blink"
                )}
              >
                {answer
                  ? <AnswerMarkdown content={answer} citations={citations} />
                  : (busy ? "Đang truy hồi ngữ cảnh và soạn câu trả lời" : "")}
              </div>
            )}
          </div>

          {/* Coverage (agentic planning: mỗi sub-goal đã đủ bằng chứng chưa) */}
          {coverage.length > 0 && <CoveragePanel subgoals={coverage} />}

          {graphFacts.length > 0 && <GraphEvidence facts={graphFacts} />}

          {/* Catalog (bản đồ mục lục agent dùng để đánh giá độ đầy đủ) */}
          {catalogs.length > 0 && (
            <div>
              <p className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-fg">
                <Network className="size-4 text-accent" /> Catalog tài liệu ({catalogs.length})
              </p>
              <div className="space-y-2.5">
                {catalogs.map((cat) => (
                  <details key={cat.document_id} className="rounded-xl border bg-surface shadow-sm">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-fg">
                      {cat.title}
                      <span className="ml-2 font-mono text-xs text-faint">
                        {cat.catalog.tree.length} facet
                      </span>
                    </summary>
                    <div className="border-t px-4 py-3">
                      <CatalogTree nodes={cat.catalog.tree} />
                    </div>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Citations */}
          {citations.length > 0 && <CitationList citations={citations} />}
        </div>
      )}
      </>
      )}
    </div>
  );
}

function McpPlaygroundPanel() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [graphFacts, setGraphFacts] = useState<GraphFact[]>([]);
  const [normalizedQuestion, setNormalizedQuestion] = useState("");
  const [rewrittenQuestion, setRewrittenQuestion] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCallTrace[]>([]);
  const [subgoals, setSubgoals] = useState<SubgoalCoverage[]>([]);
  const [config, setConfig] = useState<McpRetrieveConfig | null>(null);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [asked, setAsked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const smoothAnswer = useSmoothText((text) => setAnswer((previous) => previous + text));

  useEffect(() => () => controllerRef.current?.abort(), []);

  const testRetrieve = async () => {
    const q = question.trim();
    if (!q || busy) return;
    setBusy(true);
    setAsked(q);
    setError(null);
    setCitations([]);
    setGraphFacts([]);
    setNormalizedQuestion("");
    setRewrittenQuestion("");
    setToolCalls([]);
    setSubgoals([]);
    setConfig(null);
    setProgress([]);
    setAnswer("");
    smoothAnswer.reset();
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      await consumeSse(
        `${API_BASE_URL}/api/playground/mcp-retrieve/stream`,
        { question: q, top_k: topK },
        controller.signal,
        (event) => {
          if (event.type === "progress") {
            setProgress((old) => upsertProgress(old, event));
          } else if (event.type === "retrieve_result") {
            const res = event as McpRetrieveResponse & { type: "retrieve_result" };
            setCitations(res.citations);
            setGraphFacts(res.graph_facts ?? []);
            setNormalizedQuestion(res.normalized_question);
            setRewrittenQuestion(res.rewritten_question);
            setToolCalls(res.tool_calls);
            setSubgoals(res.subgoals);
            setConfig(res.config);
          } else if (event.type === "token") {
            smoothAnswer.push(event.content ?? "");
          } else if (event.type === "error") {
            setError(event.message);
          }
        },
      );
      smoothAnswer.flush();
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setError(e?.response?.data?.detail || e?.message || String(e));
    } finally {
      smoothAnswer.flush();
      setBusy(false);
      controllerRef.current = null;
    }
  };

  const cancel = () => {
    controllerRef.current?.abort();
    smoothAnswer.flush();
    setBusy(false);
  };

  return (
    <div className="animate-fade-in">
      <p className="mb-4 text-sm text-muted">
        Gọi thẳng tool <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-xs">retrieve</code> của
        Retrieval Engine qua MCP, hiển thị trace/evidence rồi stream câu trả lời. Dùng để test/debug
        chất lượng retrieval (đổi <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-xs">RETRIEVAL_ENABLE_*</code>{" "}
        trong .env rồi chạy lại để so sánh ảnh hưởng của từng bước).
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
            onClick={busy ? cancel : testRetrieve}
            disabled={!busy && !question.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
          >
            {busy ? <Square className="size-3.5 fill-current" /> : <Wrench className="size-4" />}
            {busy ? "Hủy" : "Chạy qua MCP"}
          </button>
        </div>
      </div>

      {(asked || busy) && (
        <div className="mt-5 space-y-4">
          <AgentActivity events={progress} active={busy} title="Retrieval trace" />
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

          <div className="rounded-2xl border bg-surface p-5 shadow-sm">
            <p className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
              <Sparkles className="size-3.5 text-accent" /> Trả lời
            </p>
            {error ? (
              <p className="text-sm font-medium text-rose-500">{error}</p>
            ) : answer ? (
              <AnswerMarkdown content={answer} citations={citations} anchorPrefix="mcp-citation" />
            ) : (
              <p className="text-sm text-muted">
                {busy ? "Đang truy hồi bằng chứng và soạn câu trả lời…" : "Không nhận được nội dung trả lời."}
              </p>
            )}
          </div>

          {(normalizedQuestion || rewrittenQuestion || toolCalls.length > 0) && (
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
                      <span className="min-w-0 flex-1 truncate font-mono text-faint">{JSON.stringify(tc.args)}</span>
                      <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 font-mono text-faint">
                        {tc.hit_count} hit{tc.hit_count === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {subgoals.length > 0 && <CoveragePanel subgoals={subgoals} />}
          {graphFacts.length > 0 && <GraphEvidence facts={graphFacts} />}
          {citations.length > 0 ? (
            <CitationList citations={citations} anchorPrefix="mcp-citation" />
          ) : !busy && !error && (
            <p className="text-sm text-muted">Không có citation nào (retrieval trả về rỗng).</p>
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
