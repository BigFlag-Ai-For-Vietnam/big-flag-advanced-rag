import { Check, Loader2, AlertTriangle } from "lucide-react";
import type { DocStatus } from "../api/client";
import { PIPELINE_STAGES, stageIndex } from "../lib/status";
import { cn } from "../lib/cn";

/** Timeline dọc thể hiện tiến trình pipeline (uploaded -> indexed) hoặc trạng thái lỗi. */
export default function PipelineStepper({ status }: { status: DocStatus }) {
  const failed = status === "failed";
  const current = failed ? -1 : stageIndex(status);
  const done = status === "indexed";

  return (
    <ol className="relative flex flex-col">
      {PIPELINE_STAGES.map((stage, i) => {
        const isDone = !failed && (done || i < current);
        const isActive = !failed && !done && i === current;
        const isLast = i === PIPELINE_STAGES.length - 1;

        const state = isDone ? "done" : isActive ? "active" : "pending";
        return (
          <li key={stage.key} className="flex gap-3.5 pb-6 last:pb-0">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "grid size-8 shrink-0 place-items-center rounded-full ring-1 transition-colors",
                  state === "done" && "bg-emerald-500 text-white ring-emerald-500",
                  state === "active" && "bg-accent text-accent-fg ring-accent",
                  state === "pending" && "bg-surface-2 text-faint ring-border"
                )}
              >
                {state === "done" ? (
                  <Check className="size-4" strokeWidth={3} />
                ) : state === "active" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <span className="text-xs font-semibold tabular-nums">{i + 1}</span>
                )}
              </span>
              {!isLast && (
                <span
                  className={cn(
                    "mt-1 w-px flex-1 transition-colors",
                    isDone ? "bg-emerald-500/50" : "bg-border"
                  )}
                />
              )}
            </div>
            <div className="pt-1">
              <p
                className={cn(
                  "text-sm font-semibold",
                  state === "pending" ? "text-faint" : "text-fg"
                )}
              >
                {stage.label}
              </p>
              {isActive && <p className="mt-0.5 text-xs text-accent">Đang xử lý…</p>}
            </div>
          </li>
        );
      })}

      {failed && (
        <li className="mt-1 flex items-center gap-2 rounded-lg bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-500 ring-1 ring-inset ring-rose-500/25">
          <AlertTriangle className="size-4" />
          Pipeline gặp lỗi
        </li>
      )}
    </ol>
  );
}
