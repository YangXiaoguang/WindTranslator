import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import type { ChapterPreview } from "@/types";

interface ChapterListProps {
  chapters: ChapterPreview[];
  selectedIndices?: Set<number>;
  onToggle?: (index: number) => void;
  activeIndex?: number;
  onSelect?: (index: number) => void;
  selectable?: boolean;
}

export function ChapterList({
  chapters,
  selectedIndices,
  onToggle,
  activeIndex,
  onSelect,
  selectable = false,
}: ChapterListProps) {
  return (
    <div className="space-y-0.5">
      {chapters.map((ch) => {
        const isSelected = selectedIndices?.has(ch.index);
        const isActive = activeIndex === ch.index;
        const statusColor =
          ch.status === "completed"
            ? "bg-accent"
            : ch.status === "translating"
              ? "bg-warning"
              : ch.status === "failed"
                ? "bg-danger"
                : "bg-bg-active";

        return (
          <div
            key={ch.id}
            onClick={() => {
              if (selectable && onToggle) onToggle(ch.index);
              else if (onSelect) onSelect(ch.index);
            }}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm cursor-pointer transition-colors",
              isActive
                ? "bg-bg-active text-text-primary"
                : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
            )}
          >
            {selectable ? (
              <div
                className={cn(
                  "h-4 w-4 rounded border flex items-center justify-center flex-shrink-0 transition-colors",
                  isSelected
                    ? "bg-accent border-accent"
                    : "border-border hover:border-border-hover"
                )}
              >
                {isSelected && <Check className="h-3 w-3 text-white" />}
              </div>
            ) : (
              <span
                className={cn(
                  "h-2 w-2 rounded-full flex-shrink-0",
                  statusColor
                )}
              />
            )}
            <span className="font-mono text-xs text-text-muted w-6 text-right flex-shrink-0">
              {ch.index}
            </span>
            <span className="truncate">{ch.title || "（无标题）"}</span>
            <span className="ml-auto text-xs text-text-muted flex-shrink-0">
              {ch.block_count} 段
            </span>
          </div>
        );
      })}
    </div>
  );
}
