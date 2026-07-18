import { AlertTriangle, Check, CircleDashed, Loader2, Network } from "lucide-react";
import type { GraphStatus } from "../api/client";
import { cn } from "../lib/cn";

const META: Record<GraphStatus, { label: string; tone: string }> = {
  not_built: { label: "Chưa build", tone: "text-faint bg-surface-2 ring-border" },
  building: { label: "Đang build", tone: "text-accent bg-accent/10 ring-accent/30" },
  ready: { label: "Sẵn sàng", tone: "text-emerald-500 bg-emerald-500/10 ring-emerald-500/30" },
  failed: { label: "Thất bại", tone: "text-rose-500 bg-rose-500/10 ring-rose-500/30" },
};

export function GraphStatusBadge({
  status,
  eligible,
  enabled,
}: {
  status: GraphStatus;
  eligible: boolean;
  enabled: boolean;
}) {
  const meta = !eligible
    ? { label: "KG không áp dụng", tone: "text-faint bg-surface-2 ring-border" }
    : !enabled
      ? { label: "KG chưa bật", tone: "text-amber-500 bg-amber-500/10 ring-amber-500/30" }
      : { label: `KG · ${META[status].label}`, tone: META[status].tone };
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ring-1 ring-inset", meta.tone)}>
      {status === "building" && eligible && enabled ? <Loader2 className="size-3 animate-spin" /> : <Network className="size-3" />}
      {meta.label}
    </span>
  );
}

export default function GraphStatusPanel({
  status,
  eligible,
  enabled,
  error,
}: {
  status: GraphStatus;
  eligible: boolean;
  enabled: boolean;
  error: string | null;
}) {
  let icon = <CircleDashed className="size-5 text-faint" />;
  let title = "Chờ tạo Knowledge Graph";
  let description = "Graph sẽ bắt đầu sau khi hệ thống tạo xong chunks.";
  let tone = "border-border bg-surface-2/50";

  if (!eligible) {
    title = "Không áp dụng Knowledge Graph";
    description = "Loại tài liệu này không thuộc KG_CATEGORIES.";
  } else if (!enabled) {
    title = "Knowledge Graph chưa được bật";
    description = "Kiểm tra KG_ENABLE_BUILD và Neo4j credentials.";
    tone = "border-amber-500/30 bg-amber-500/10";
  } else if (status === "building") {
    icon = <Loader2 className="size-5 animate-spin text-accent" />;
    title = "Đang build Knowledge Graph";
    description = "Vector Store có thể sẵn sàng trước khi bước này hoàn tất.";
    tone = "border-accent/30 bg-accent/10";
  } else if (status === "ready") {
    icon = <Check className="size-5 text-emerald-500" />;
    title = "Knowledge Graph sẵn sàng";
    description = "Entity và relationship đã được ghi vào Neo4j.";
    tone = "border-emerald-500/30 bg-emerald-500/10";
  } else if (status === "failed") {
    icon = <AlertTriangle className="size-5 text-rose-500" />;
    title = "Knowledge Graph build thất bại";
    description = error || "Có thể retry riêng từ trang Documents.";
    tone = "border-rose-500/30 bg-rose-500/10";
  }

  return (
    <div className={cn("rounded-xl border p-3.5", tone)}>
      <div className="flex gap-3">
        <span className="mt-0.5">{icon}</span>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-fg">{title}</p>
          <p className="mt-0.5 break-words text-xs leading-relaxed text-muted">{description}</p>
        </div>
      </div>
    </div>
  );
}
