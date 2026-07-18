import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, BrainCircuit, CheckCircle2, ChevronDown, CircleAlert,
  Database, GitCompareArrows, Loader2, Search, Send, Sparkles, Square,
} from "lucide-react";
import {
  API_BASE_URL,
  type CatalogInfo,
  type Citation,
  type GraphFact,
  type ShowcaseMetrics,
  type ShowcasePipeline,
  type ShowcaseTraceStep,
  type SubgoalCoverage,
  type ToolCallTrace,
  type ProgressEvent,
} from "../api/client";
import { CitationList, CoveragePanel } from "../components/RetrievalEvidence";
import GraphEvidence from "../components/GraphEvidence";
import { cn } from "../lib/cn";
import { SHOWCASE_PRESETS } from "./showcasePresets";
import AgentActivity from "../components/AgentActivity";
import AnswerMarkdown from "../components/AnswerMarkdown";
import { consumeSse } from "../lib/sse";
import { upsertProgress } from "../lib/progress";

type RunStatus = "idle" | "retrieving" | "generating" | "done" | "error" | "cancelled";

interface PipelineResult {
  status: RunStatus;
  answer: string;
  error: string | null;
  citations: Citation[];
  graphFacts: GraphFact[];
  catalogs: CatalogInfo[];
  subgoals: SubgoalCoverage[];
  toolCalls: ToolCallTrace[];
  trace: ShowcaseTraceStep[];
  normalizedQuestion: string;
  rewrittenQuestion: string;
  metrics: ShowcaseMetrics;
  progress: ProgressEvent[];
}

const emptyMetrics = (): ShowcaseMetrics => ({
  retrieval_ms: null, first_token_ms: null, total_ms: null, citation_count: 0,
});

const emptyResult = (): PipelineResult => ({
  status: "idle",
  answer: "",
  error: null,
  citations: [],
  graphFacts: [],
  catalogs: [],
  subgoals: [],
  toolCalls: [],
  trace: [],
  normalizedQuestion: "",
  rewrittenQuestion: "",
  metrics: emptyMetrics(),
  progress: [],
});

const PIPELINES: ShowcasePipeline[] = ["advanced", "raw"];

export default function ShowcasePage() {
  const [selectedId, setSelectedId] = useState(SHOWCASE_PRESETS[0].id);
  const selectedPreset = useMemo(
    () => SHOWCASE_PRESETS.find((preset) => preset.id === selectedId) ?? null,
    [selectedId],
  );
  const [question, setQuestion] = useState(SHOWCASE_PRESETS[0].question);
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<Record<ShowcasePipeline, PipelineResult>>({
    advanced: emptyResult(), raw: emptyResult(),
  });
  const [busy, setBusy] = useState(false);
  const [runFinished, setRunFinished] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);
  const startedAtRef = useRef(0);
  const pendingAnswerRef = useRef<Record<ShowcasePipeline, string>>({ advanced: "", raw: "" });
  const flushTimersRef = useRef<Record<ShowcasePipeline, number | null>>({ advanced: null, raw: null });

  useEffect(() => {
    if (!busy) return;
    const timer = window.setInterval(() => setElapsed(Date.now() - startedAtRef.current), 100);
    return () => window.clearInterval(timer);
  }, [busy]);

  useEffect(() => () => {
    controllerRef.current?.abort();
    for (const pipeline of PIPELINES) {
      const timer = flushTimersRef.current[pipeline];
      if (timer != null) window.clearTimeout(timer);
    }
  }, []);

  const updatePipeline = (pipeline: ShowcasePipeline, update: (old: PipelineResult) => PipelineResult) => {
    setResults((current) => ({ ...current, [pipeline]: update(current[pipeline]) }));
  };

  const flushAnswer = (pipeline: ShowcasePipeline) => {
    const timer = flushTimersRef.current[pipeline];
    if (timer != null) window.clearTimeout(timer);
    flushTimersRef.current[pipeline] = null;
    const text = pendingAnswerRef.current[pipeline];
    if (!text) return;
    pendingAnswerRef.current[pipeline] = "";
    updatePipeline(pipeline, (old) => ({ ...old, answer: old.answer + text }));
  };

  const queueAnswer = (pipeline: ShowcasePipeline, text: string) => {
    pendingAnswerRef.current[pipeline] += text;
    if (flushTimersRef.current[pipeline] == null) {
      flushTimersRef.current[pipeline] = window.setTimeout(() => flushAnswer(pipeline), 40);
    }
  };

  const handleEvent = (event: any) => {
    const pipeline = event.pipeline as ShowcasePipeline | undefined;
    if (pipeline && !PIPELINES.includes(pipeline)) return;
    if (event.type === "progress" && pipeline) {
      updatePipeline(pipeline, (old) => ({
        ...old,
        progress: upsertProgress(old.progress, event as ProgressEvent),
      }));
    } else if (event.type === "pipeline_context" && pipeline) {
      updatePipeline(pipeline, (old) => ({
        ...old,
        status: "generating",
        citations: event.citations ?? [],
        graphFacts: event.graph_facts ?? [],
        catalogs: event.catalogs ?? [],
        subgoals: event.subgoals ?? [],
        toolCalls: event.tool_calls ?? [],
        trace: event.trace ?? [],
        normalizedQuestion: event.normalized_question ?? "",
        rewrittenQuestion: event.rewritten_question ?? "",
        metrics: {
          ...old.metrics,
          retrieval_ms: event.retrieval_ms ?? null,
          citation_count: event.citations?.length ?? 0,
        },
      }));
    } else if (event.type === "pipeline_token" && pipeline) {
      updatePipeline(pipeline, (old) => ({ ...old, status: "generating" }));
      queueAnswer(pipeline, event.content ?? "");
    } else if (event.type === "pipeline_done" && pipeline) {
      flushAnswer(pipeline);
      updatePipeline(pipeline, (old) => ({
        ...old,
        status: "done",
        metrics: {
          retrieval_ms: event.retrieval_ms ?? old.metrics.retrieval_ms,
          first_token_ms: event.first_token_ms ?? null,
          total_ms: event.total_ms ?? null,
          citation_count: event.citation_count ?? old.citations.length,
        },
      }));
    } else if (event.type === "pipeline_error" && pipeline) {
      flushAnswer(pipeline);
      updatePipeline(pipeline, (old) => ({
        ...old, status: "error", error: event.message || "Pipeline gặp lỗi.",
        metrics: { ...old.metrics, total_ms: event.total_ms ?? null },
      }));
    } else if (event.type === "run_done") {
      setRunFinished(true);
    }
  };

  const runComparison = async () => {
    const query = question.trim();
    if (!query || busy) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    startedAtRef.current = Date.now();
    setElapsed(0);
    setRunFinished(false);
    setBusy(true);
    pendingAnswerRef.current = { advanced: "", raw: "" };
    setResults({
      advanced: { ...emptyResult(), status: "retrieving" },
      raw: { ...emptyResult(), status: "retrieving" },
    });

    try {
      await consumeSse(
        `${API_BASE_URL}/api/showcase/compare`,
        { question: query, top_k: topK },
        controller.signal,
        handleEvent,
      );
      PIPELINES.forEach(flushAnswer);
    } catch (error: any) {
      if (error?.name === "AbortError") return;
      setResults((current) => {
        const next = { ...current };
        for (const pipeline of PIPELINES) {
          if (["retrieving", "generating"].includes(next[pipeline].status)) {
            next[pipeline] = { ...next[pipeline], status: "error", error: error?.message || String(error) };
          }
        }
        return next;
      });
    } finally {
      if (!controller.signal.aborted) setRunFinished(true);
      setBusy(false);
      controllerRef.current = null;
    }
  };

  const cancel = () => {
    controllerRef.current?.abort();
    PIPELINES.forEach(flushAnswer);
    setResults((current) => {
      const next = { ...current };
      for (const pipeline of PIPELINES) {
        if (["retrieving", "generating"].includes(next[pipeline].status)) {
          next[pipeline] = { ...next[pipeline], status: "cancelled" };
        }
      }
      return next;
    });
    setRunFinished(false);
    setBusy(false);
  };

  const choosePreset = (id: string) => {
    const preset = SHOWCASE_PRESETS.find((item) => item.id === id);
    if (!preset) return;
    setSelectedId(id);
    setQuestion(preset.question);
    setRunFinished(false);
  };

  return (
    <div className="animate-fade-in">
      <header className="mb-6">
        <div className="flex items-center gap-2 text-sm font-semibold text-accent">
          <GitCompareArrows className="size-4" /> Side-by-side RAG comparison
        </div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">Showcase Demo</h1>
        <p className="mt-1.5 max-w-3xl text-muted">
          Cùng một câu hỏi, cùng model — so sánh planner/catalog/hybrid retrieval với dense vector RAG one-shot.
        </p>
      </header>

      <section className="rounded-2xl border bg-surface p-4 shadow-sm sm:p-5">
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <label className="block">
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-faint">Kịch bản demo</span>
            <span className="relative block">
              <select
                value={selectedId}
                onChange={(event) => choosePreset(event.target.value)}
                disabled={busy}
                className="w-full appearance-none rounded-xl border bg-surface-2 px-3.5 py-3 pr-9 text-sm font-medium text-fg outline-none"
              >
                {!selectedPreset && <option value="">Câu hỏi tùy chỉnh</option>}
                {SHOWCASE_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>{preset.title} — {preset.category}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-3.5 size-4 text-faint" />
            </span>
            {selectedPreset && <p className="mt-2 text-xs leading-relaxed text-muted">{selectedPreset.painPoint}</p>}
          </label>

          <div>
            <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-faint">Câu hỏi chung</span>
            <textarea
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value);
                if (event.target.value !== selectedPreset?.question) setSelectedId("");
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) runComparison();
              }}
              disabled={busy}
              className="min-h-24 w-full resize-y rounded-xl border bg-transparent px-3.5 py-3 text-[15px] leading-relaxed text-fg outline-none placeholder:text-faint"
              placeholder="Nhập câu hỏi tùy ý…"
            />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <label className="flex items-center gap-2.5 text-sm text-muted">
            <span className="font-medium">top_k</span>
            <input type="range" min={1} max={12} value={topK} disabled={busy}
              onChange={(event) => setTopK(Number(event.target.value))} className="accent-accent" />
            <span className="w-6 text-center font-mono tabular-nums text-fg">{topK}</span>
          </label>
          {busy ? (
            <button onClick={cancel} className="inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold text-fg hover:bg-surface-2">
              <Square className="size-3.5 fill-current" /> Hủy ({formatMs(elapsed)})
            </button>
          ) : (
            <button onClick={runComparison} disabled={!question.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-all hover:brightness-110 disabled:pointer-events-none disabled:opacity-50">
              <Send className="size-4" /> Chạy so sánh
            </button>
          )}
        </div>
      </section>

      <div className="mt-6 grid items-start gap-5 lg:grid-cols-2">
        <PipelineCard pipeline="advanced" result={results.advanced} liveElapsed={elapsed} />
        <PipelineCard pipeline="raw" result={results.raw} liveElapsed={elapsed} />
      </div>

      {runFinished && selectedPreset && question.trim() === selectedPreset.question && (
        <section className="mt-6 rounded-2xl border border-amber-400/40 bg-amber-50 p-5 shadow-sm dark:bg-amber-950/20">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            <CheckCircle2 className="size-4" /> Đáp án kỳ vọng
          </p>
          <p className="mt-3 whitespace-pre-wrap text-[15px] leading-relaxed text-amber-950 dark:text-amber-100">
            {selectedPreset.expected}
          </p>
        </section>
      )}
    </div>
  );
}

function PipelineCard({ pipeline, result, liveElapsed }: {
  pipeline: ShowcasePipeline; result: PipelineResult; liveElapsed: number;
}) {
  const advanced = pipeline === "advanced";
  const active = result.status === "retrieving" || result.status === "generating";
  return (
    <section className={cn(
      "overflow-hidden rounded-2xl border bg-surface shadow-sm",
      advanced && "border-accent/35 ring-1 ring-accent/10",
    )}>
      <header className={cn("border-b p-4", advanced ? "bg-accent-soft" : "bg-surface-2/60")}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex gap-3">
            <span className={cn("grid size-10 place-items-center rounded-xl", advanced ? "bg-accent text-accent-fg" : "bg-surface text-muted")}>
              {advanced ? <BrainCircuit className="size-5" /> : <Database className="size-5" />}
            </span>
            <div>
              <h2 className="font-bold text-fg">{advanced ? "Advanced RAG" : "Raw Vector RAG"}</h2>
              <p className="mt-0.5 text-xs text-muted">
                {advanced ? "Planner + Catalog + Hybrid Retrieval" : "Dense top-k + One-shot Generation"}
              </p>
            </div>
          </div>
          <StatusBadge status={result.status} />
        </div>
      </header>

      <div className="space-y-5 p-4 sm:p-5">
        <MetricRow metrics={result.metrics} liveElapsed={active ? liveElapsed : null} />
        <AgentActivity events={result.progress} active={active} title="Pipeline trace" />
        {result.error ? (
          <div className="flex gap-2 rounded-xl border border-rose-300/50 bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/20 dark:text-rose-300">
            <CircleAlert className="mt-0.5 size-4 shrink-0" /> {result.error}
          </div>
        ) : (
          <div>
            <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-faint">
              <Sparkles className="size-3.5 text-accent" /> Câu trả lời
            </p>
            <div className={cn("min-h-28", active && "caret-blink")}>
              {result.answer
                ? <AnswerMarkdown content={result.answer} citations={result.citations} anchorPrefix={`${pipeline}-citation`} />
                : statusCopy(result.status)}
            </div>
          </div>
        )}

        {advanced && (result.toolCalls.length > 0 || result.rewrittenQuestion) && (
          <details className="rounded-xl border bg-surface-2/40" open>
            <summary className="cursor-pointer px-3.5 py-3 text-sm font-semibold text-fg">Pipeline trace</summary>
            <div className="space-y-2 border-t px-3.5 py-3 text-xs">
              {result.normalizedQuestion && result.normalizedQuestion !== result.rewrittenQuestion && (
                <p><span className="text-faint">Normalize:</span> <span className="text-fg">{result.normalizedQuestion}</span></p>
              )}
              {result.rewrittenQuestion && <p><span className="text-faint">Rewrite:</span> <span className="text-fg">{result.rewrittenQuestion}</span></p>}
              {result.toolCalls.map((call, index) => (
                <div key={index} className="flex items-center gap-2 rounded-lg bg-surface px-2.5 py-2">
                  <Search className="size-3.5 shrink-0 text-accent" />
                  <span className="font-mono font-semibold text-fg">{call.tool}</span>
                  <span className="min-w-0 flex-1 truncate font-mono text-faint">{JSON.stringify(call.args)}</span>
                  <span className="font-mono text-faint">{call.hit_count} hits</span>
                </div>
              ))}
              {result.catalogs.length > 0 && <p className="text-faint">Catalogs loaded: {result.catalogs.length}</p>}
            </div>
          </details>
        )}

        {!advanced && result.trace.length > 0 && (
          <div className="space-y-1.5">
            {result.trace.map((step) => (
              <div key={step.stage} className="flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-2 text-xs text-muted">
                <Activity className="size-3.5 text-accent" /> {step.label}
                {step.hit_count != null && <span className="ml-auto font-mono">{step.hit_count} hits</span>}
              </div>
            ))}
          </div>
        )}

        {result.subgoals.length > 0 && <CoveragePanel subgoals={result.subgoals} />}
        {advanced && <GraphEvidence facts={result.graphFacts} />}
        {result.citations.length > 0 && (
          <CitationList citations={result.citations} compact anchorPrefix={`${pipeline}-citation`} />
        )}
      </div>
    </section>
  );
}

function MetricRow({ metrics, liveElapsed }: { metrics: ShowcaseMetrics; liveElapsed: number | null }) {
  const values = [
    ["Retrieve", metrics.retrieval_ms],
    ["First token", metrics.first_token_ms],
    ["Total", metrics.total_ms ?? liveElapsed],
    ["Sources", metrics.citation_count],
  ] as const;
  return (
    <div className="grid grid-cols-4 gap-2">
      {values.map(([label, value]) => (
        <div key={label} className="rounded-lg bg-surface-2 px-2 py-2 text-center">
          <p className="truncate text-[10px] uppercase tracking-wide text-faint">{label}</p>
          <p className="mt-0.5 font-mono text-xs font-semibold text-fg">
            {label === "Sources" ? value ?? 0 : formatMs(value)}
          </p>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status }: { status: RunStatus }) {
  const copy: Record<RunStatus, string> = {
    idle: "Sẵn sàng", retrieving: "Retrieving", generating: "Generating",
    done: "Hoàn tất", error: "Lỗi", cancelled: "Đã hủy",
  };
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
      status === "done" && "border-emerald-300/60 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/20 dark:text-emerald-300",
      status === "error" && "border-rose-300/60 bg-rose-50 text-rose-700 dark:bg-rose-950/20 dark:text-rose-300",
      ["retrieving", "generating"].includes(status) && "border-accent/30 bg-accent-soft text-accent",
      ["idle", "cancelled"].includes(status) && "bg-surface text-muted",
    )}>
      {["retrieving", "generating"].includes(status) && <Loader2 className="size-3 animate-spin" />}
      {status === "done" && <CheckCircle2 className="size-3" />}
      {copy[status]}
    </span>
  );
}

function statusCopy(status: RunStatus) {
  if (status === "idle") return "Chọn một kịch bản hoặc nhập câu hỏi để bắt đầu.";
  if (status === "retrieving") return "Đang truy hồi và chuẩn bị ngữ cảnh";
  if (status === "generating") return "Đang chờ token đầu tiên";
  if (status === "cancelled") return "Lần chạy đã được hủy.";
  return "Không có nội dung trả lời.";
}

function formatMs(value: number | null) {
  if (value == null) return "—";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}
