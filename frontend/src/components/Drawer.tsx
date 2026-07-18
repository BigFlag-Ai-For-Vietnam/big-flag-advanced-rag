import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
}

/** Slide-over panel bên phải cho chi tiết document. */
export default function Drawer({ open, onClose, title, subtitle, children }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    if (open) {
      window.addEventListener("keydown", onKey);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  // Portal ra body: tránh bị "nhốt" bởi ancestor có transform (vd .animate-fade-in dùng
  // animation-fill-mode: both giữ lại transform: translateY(0) -> tạo containing block
  // khiến position:fixed bám vào cột nội dung thay vì viewport).
  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px] animate-fade-in"
        onClick={onClose}
      />
      <aside className="animate-slide-in absolute right-0 top-0 flex h-full w-[min(94vw,720px)] flex-col border-l bg-surface shadow-2xl">
        <header className="flex items-start justify-between gap-4 border-b px-6 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-bold text-fg">{title}</h2>
            {subtitle && <div className="mt-1 text-sm text-muted">{subtitle}</div>}
          </div>
          <button
            onClick={onClose}
            aria-label="Đóng"
            className="grid size-9 shrink-0 place-items-center rounded-lg border text-muted transition-colors hover:bg-surface-2 hover:text-fg"
          >
            <X className="size-4.5" />
          </button>
        </header>
        <div className="scrollbar-thin flex-1 overflow-y-auto px-6 py-5">{children}</div>
      </aside>
    </div>,
    document.body
  );
}
