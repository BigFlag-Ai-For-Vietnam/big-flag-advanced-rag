import { useEffect, useRef, useState } from "react";
import { AlertTriangle, Check, ChevronDown, Loader2, Minus, Search } from "lucide-react";
import type { ProgressEvent } from "../api/client";
import { cn } from "../lib/cn";

export default function AgentActivity({
  events, active, title = "Quá trình xử lý",
}: { events: ProgressEvent[]; active: boolean; title?: string }) {
  const [open, setOpen] = useState(false);
  const manuallyChanged = useRef(false);

  useEffect(() => {
    if (active) {
      if (!manuallyChanged.current) setOpen(true);
    } else {
      if (!manuallyChanged.current) setOpen(false);
      manuallyChanged.current = false;
    }
  }, [active]);

  if (!events.length) return null;
  const completed = events.filter((event) => event.status === "completed").length;
  const latest = events[events.length - 1];
  const failed = [...events].reverse().find((event) => event.status === "failed");
  const interrupted = !active && !failed && events.some((event) => event.status === "started");

  return (
    <details
      open={open}
      onToggle={(event) => {
        const next = event.currentTarget.open;
        if (next !== open) {
          manuallyChanged.current = true;
          setOpen(next);
        }
      }}
      className="overflow-hidden rounded-xl border bg-surface-2/40"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3.5 py-3 text-sm font-semibold text-fg">
        {active ? (
          <Loader2 className="size-4 animate-spin text-accent" />
        ) : failed || interrupted ? (
          <AlertTriangle className="size-4 text-amber-500" />
        ) : (
          <Check className="size-4 text-emerald-500" />
        )}
        <span className="min-w-0 flex-1 truncate">
          {active ? latest.label : failed ? failed.label : interrupted ? `${title} đã dừng` : `${title} · ${completed} bước hoàn tất`}
        </span>
        <ChevronDown className={cn("size-4 text-faint transition-transform", open && "rotate-180")} />
      </summary>
      <ol className="space-y-1.5 border-t px-3.5 py-3">
        {events.map((event) => <ActivityRow key={`${event.pipeline}:${event.seq}`} event={event} />)}
      </ol>
    </details>
  );
}

function ActivityRow({ event }: { event: ProgressEvent }) {
  const detail = event.detail;
  return (
    <li className="rounded-lg bg-surface px-3 py-2 text-xs">
      <div className="flex items-start gap-2">
        {event.status === "started" && <Loader2 className="mt-0.5 size-3.5 shrink-0 animate-spin text-accent" />}
        {event.status === "completed" && <Check className="mt-0.5 size-3.5 shrink-0 text-emerald-500" />}
        {event.status === "warning" && <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-500" />}
        {event.status === "failed" && <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-rose-500" />}
        {event.status === "skipped" && <Minus className="mt-0.5 size-3.5 shrink-0 text-faint" />}
        <span className="min-w-0 flex-1 text-fg">{event.label}</span>
        {event.duration_ms != null && <span className="shrink-0 font-mono text-faint">{formatMs(event.duration_ms)}</span>}
      </div>
      {(detail?.query || detail?.hit_count != null || detail?.graph_hit_count != null || detail?.note) && (
        <details className="mt-1.5 pl-5 text-faint">
          <summary className="inline-flex cursor-pointer items-center gap-1 font-medium text-muted">
            <Search className="size-3" /> Chi tiết
          </summary>
          <div className="mt-1 space-y-0.5 break-words font-mono text-[11px]">
            {detail.query && <p>query: {detail.query}</p>}
            {detail.hop != null && <p>hop: {detail.hop}</p>}
            {detail.hit_count != null && <p>KB hits: {detail.hit_count}</p>}
            {detail.graph_hit_count != null && <p>graph facts: {detail.graph_hit_count}</p>}
            {detail.note && <p>note: {detail.note}</p>}
          </div>
        </details>
      )}
    </li>
  );
}

function formatMs(value: number) {
  return value < 1000 ? `${value} ms` : `${(value / 1000).toFixed(1)} s`;
}
