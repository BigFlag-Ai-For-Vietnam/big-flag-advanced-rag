import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { UploadCloud, LayoutGrid, MessagesSquare, Boxes, Columns2 } from "lucide-react";
import { getHealth } from "../api/client";
import ThemeToggle from "./ThemeToggle";
import { cn } from "../lib/cn";

const NAV = [
  { to: "/documents", label: "Tài liệu", icon: LayoutGrid },
  { to: "/upload", label: "Tải lên", icon: UploadCloud },
  { to: "/playground", label: "Playground", icon: MessagesSquare },
  { to: "/showcase", label: "Showcase Demo", icon: Columns2 },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let alive = true;
    const check = async () => {
      const ok = await getHealth();
      if (alive) setOnline(ok);
    };
    check();
    const t = window.setInterval(check, 15000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, []);

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r bg-surface px-4 py-5 md:flex">
        <div className="flex items-center gap-2.5 px-2">
          <span className="grid size-9 place-items-center rounded-xl bg-accent text-accent-fg">
            <Boxes className="size-5" />
          </span>
          <div className="leading-tight">
            <p className="font-bold text-fg">RAG Platform</p>
            <p className="font-mono text-[11px] text-faint">contextual retrieval</p>
          </div>
        </div>

        <nav className="mt-7 flex flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-muted hover:bg-surface-2 hover:text-fg"
                )
              }
            >
              <Icon className="size-4.5" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto flex items-center justify-between gap-2 rounded-lg border bg-surface-2/50 px-3 py-2.5">
          <div className="flex items-center gap-2 text-xs font-medium">
            <span
              className={cn(
                "size-2 rounded-full",
                online == null ? "bg-slate-400" : online ? "bg-emerald-500" : "bg-rose-500",
                online && "animate-pulse"
              )}
            />
            <span className="text-muted">
              {online == null ? "Đang kiểm tra…" : online ? "Backend online" : "Backend offline"}
            </span>
          </div>
          <ThemeToggle />
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b bg-surface/80 px-4 py-3 backdrop-blur md:hidden">
          <div className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded-lg bg-accent text-accent-fg">
              <Boxes className="size-4" />
            </span>
            <span className="font-bold">RAG Platform</span>
          </div>
          <ThemeToggle />
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b bg-surface px-3 py-2 md:hidden">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <main
          className={cn(
            "mx-auto w-full flex-1 px-4 py-6 sm:px-6 lg:py-10",
            location.pathname === "/showcase" ? "max-w-7xl" : "max-w-5xl"
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
