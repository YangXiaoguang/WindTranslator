import { cn } from "@/lib/utils";

interface Block {
  block_type: string;
  text: string;
  translated: string;
  status: string;
}

interface TranslationPreviewProps {
  blocks: Block[];
}

export function TranslationPreview({ blocks }: TranslationPreviewProps) {
  if (blocks.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted text-sm">
        选择章节查看翻译内容
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, i) => {
        const isHeading = block.block_type.startsWith("h");
        const isCompleted = block.status === "completed";
        const isTranslating = block.status === "translating";

        return (
          <div
            key={i}
            className={cn(
              "grid grid-cols-2 gap-4 rounded-md border border-border p-3",
              isHeading && "border-border-hover bg-bg-elevated"
            )}
          >
            {/* Original */}
            <div
              className={cn(
                "text-text-secondary leading-relaxed",
                isHeading ? "text-sm font-medium" : "text-sm",
              )}
              style={{ fontFamily: "var(--font-sans)" }}
            >
              {block.text}
            </div>

            {/* Translated */}
            <div
              className={cn(
                "leading-relaxed",
                isHeading ? "text-sm font-medium" : "text-sm",
              )}
              style={{ fontFamily: "var(--font-cn)" }}
            >
              {isCompleted ? (
                <span className="text-text-primary fade-in">
                  {block.translated}
                </span>
              ) : isTranslating ? (
                <div className="space-y-1.5">
                  <div className="skeleton h-4 w-full" />
                  <div className="skeleton h-4 w-3/4" />
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="h-4 w-full rounded bg-bg-active" />
                  <div className="h-4 w-2/3 rounded bg-bg-active" />
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
