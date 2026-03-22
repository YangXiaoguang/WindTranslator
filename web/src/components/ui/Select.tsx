import { type SelectHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, className, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "h-8 rounded-md border border-border bg-bg-elevated px-3 text-sm text-text-primary outline-none transition-colors appearance-none cursor-pointer",
        "focus:border-accent focus:ring-1 focus:ring-accent/30",
        className
      )}
      {...props}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
);
Select.displayName = "Select";
