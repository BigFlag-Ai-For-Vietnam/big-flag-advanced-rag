import { CircleAlert, CircleCheck, FileText, Target } from "lucide-react";
import type { Citation, SubgoalCoverage } from "../api/client";

export function CitationList({ citations, compact = false }: { citations: Citation[]; compact?: boolean }) {
  return (
    <div>
      <p className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-fg">
        <FileText className="size-4 text-accent" /> Nguồn ({citations.length})
      </p>
      <div className="space-y-2">
        {citations.map((citation, index) => (
          <details key={`${citation.document_id}:${citation.chunk_index}:${index}`} className="rounded-xl border bg-surface shadow-sm">
            <summary className="flex cursor-pointer items-center gap-3 px-3.5 py-2.5">
              <span className="grid size-6 shrink-0 place-items-center rounded-md bg-accent-soft font-mono text-xs font-bold text-accent">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-fg">{citation.title}</span>
                <span className="font-mono text-xs text-faint">đoạn #{citation.chunk_index}</span>
              </span>
              <ScoreBar score={citation.score} compact={compact} />
            </summary>
            <p className="scrollbar-thin max-h-72 overflow-auto whitespace-pre-wrap border-t px-4 py-3 text-sm leading-relaxed text-muted">
              {citation.final_content}
            </p>
          </details>
        ))}
      </div>
    </div>
  );
}

export function CoveragePanel({ subgoals }: { subgoals: SubgoalCoverage[] }) {
  const done = subgoals.filter((subgoal) => subgoal.satisfied).length;
  return (
    <div>
      <p className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-fg">
        <Target className="size-4 text-accent" /> Độ phủ kế hoạch ({done}/{subgoals.length})
      </p>
      <div className="space-y-1.5">
        {subgoals.map((subgoal, index) => (
          <div key={index} className="flex items-start gap-2.5 rounded-lg border bg-surface px-3.5 py-2 text-sm">
            {subgoal.satisfied ? (
              <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-500" />
            ) : (
              <CircleAlert className="mt-0.5 size-4 shrink-0 text-amber-500" />
            )}
            <span className="min-w-0 flex-1">
              <span className="text-fg">{subgoal.description}</span>
              <span className="ml-2 font-mono text-xs text-faint">{subgoal.evidence_count} đoạn</span>
              {!subgoal.satisfied && subgoal.note && (
                <span className="mt-0.5 block text-xs text-amber-600 dark:text-amber-400">Thiếu: {subgoal.note}</span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreBar({ score, compact }: { score: number; compact: boolean }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  return (
    <span className="flex shrink-0 items-center gap-2" title={`Relevance ${score.toFixed(3)}`}>
      {!compact && (
        <span className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-2">
          <span className="block h-full rounded-full bg-highlight" style={{ width: `${pct}%` }} />
        </span>
      )}
      <span className="w-9 text-right font-mono text-xs tabular-nums text-highlight">
        {score.toFixed(2)}
      </span>
    </span>
  );
}
