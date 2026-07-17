import { Loader2 } from "lucide-react";
import type { DocStatus } from "../api/client";
import { STATUS_META } from "../lib/status";
import { cn } from "../lib/cn";

export default function StatusBadge({ status, className }: { status: DocStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset",
        meta.pill,
        className
      )}
    >
      {meta.busy ? (
        <Loader2 className="size-3 animate-spin" />
      ) : (
        <span className={cn("size-1.5 rounded-full", meta.dot)} />
      )}
      {meta.label}
    </span>
  );
}
