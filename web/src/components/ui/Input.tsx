import { type InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, className, ...props }, ref) => (
    <div className="flex flex-col gap-1">
      <input
        ref={ref}
        className={cn(
          "h-8 rounded-md border bg-bg-elevated px-3 text-sm text-text-primary placeholder:text-text-muted outline-none transition-colors",
          "border-border focus:border-accent focus:ring-1 focus:ring-accent/30",
          error && "border-danger focus:border-danger focus:ring-danger/30",
          className
        )}
        {...props}
      />
      {error && <span className="text-xs text-danger">{error}</span>}
    </div>
  )
);
Input.displayName = "Input";
