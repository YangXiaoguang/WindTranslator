import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { BookOpen, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "项目", icon: BookOpen },
  { to: "/settings", label: "设置", icon: Settings },
] as const;

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-48 flex-shrink-0 border-r border-border bg-bg-elevated flex flex-col">
        <div className="h-12 flex items-center px-4 border-b border-border">
          <Link to="/" className="text-sm font-semibold text-text-primary tracking-tight">
            WindTranslator
          </Link>
        </div>
        <nav className="flex-1 px-2 py-2 space-y-0.5">
          {NAV.map(({ to, label, icon: Icon }) => {
            const active =
              to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-bg-active text-text-primary"
                    : "text-text-secondary hover:text-text-primary hover:bg-bg-hover"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="px-4 py-3 border-t border-border text-xs text-text-muted">
          v0.3.0
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
