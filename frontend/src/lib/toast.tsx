import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "./cn";

type ToastKind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastCtx {
  push: (kind: ToastKind, message: string) => void;
}

const Ctx = createContext<ToastCtx | null>(null);

let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (kind: ToastKind, message: string) => {
      const id = ++counter;
      setToasts((t) => [...t, { id, kind, message }]);
      window.setTimeout(() => remove(id), 4200);
    },
    [remove]
  );

  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[min(92vw,360px)] flex-col gap-2.5">
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </Ctx.Provider>
  );
}

const ICONS = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
} as const;

const TONE = {
  success: "text-emerald-500",
  error: "text-rose-500",
  info: "text-accent",
} as const;

function ToastCard({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const Icon = ICONS[toast.kind];
  return (
    <div className="animate-slide-in pointer-events-auto flex items-start gap-3 rounded-xl border bg-surface p-3.5 shadow-lg shadow-black/5 ring-1 ring-black/[0.02]">
      <Icon className={cn("mt-0.5 size-5 shrink-0", TONE[toast.kind])} />
      <p className="flex-1 text-sm leading-snug text-fg">{toast.message}</p>
      <button
        onClick={onClose}
        aria-label="Đóng"
        className="rounded-md p-0.5 text-faint transition-colors hover:text-fg"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}

export function useToast(): ToastCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast phải nằm trong <ToastProvider>");
  return ctx;
}
