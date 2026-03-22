import { cn } from "@/lib/utils";
import type { ProjectStatus } from "@/types";

const config: Record<
  ProjectStatus,
  { label: string; bg: string; text: string; dot: string }
> = {
  pending:     { label: "等待解析", bg: "bg-bg-active", text: "text-text-muted", dot: "bg-text-muted" },
  parsed:      { label: "待翻译",   bg: "bg-info-muted", text: "text-info", dot: "bg-info" },
  translating: { label: "翻译中",   bg: "bg-warning-muted", text: "text-warning", dot: "bg-warning" },
  completed:   { label: "已完成",   bg: "bg-accent-muted", text: "text-accent", dot: "bg-accent" },
  failed:      { label: "失败",     bg: "bg-danger-muted", text: "text-danger", dot: "bg-danger" },
  cancelled:   { label: "已取消",   bg: "bg-bg-active", text: "text-text-muted", dot: "bg-text-muted" },
  error:       { label: "错误",     bg: "bg-danger-muted", text: "text-danger", dot: "bg-danger" },
};

interface StatusBadgeProps {
  status: ProjectStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const c = config[status] ?? config.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        c.bg,
        c.text,
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", c.dot)} />
      {c.label}
    </span>
  );
}
