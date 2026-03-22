import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;       /* 0–100 */
  size?: "sm" | "md";
  className?: string;
}

export function ProgressBar({ value, size = "sm", className }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div
      className={cn(
        "w-full rounded-full bg-bg-active overflow-hidden",
        size === "sm" ? "h-1.5" : "h-2.5",
        className
      )}
    >
      <div
        className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
