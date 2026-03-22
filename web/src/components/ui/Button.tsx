import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover active:bg-emerald-700 focus-visible:ring-accent/40",
  secondary:
    "bg-bg-elevated text-text-secondary border border-border hover:bg-bg-hover hover:text-text-primary hover:border-border-hover active:bg-bg-active focus-visible:ring-border-hover",
  danger:
    "bg-danger-muted text-danger hover:bg-danger/20 active:bg-danger/30 focus-visible:ring-danger/40",
  ghost:
    "text-text-secondary hover:text-text-primary hover:bg-bg-hover active:bg-bg-active focus-visible:ring-border-hover",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3.5 text-sm gap-2",
  lg: "h-10 px-5 text-sm gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = "primary", size = "md", loading, disabled, className, children, ...props },
    ref
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors duration-150 outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  )
);
Button.displayName = "Button";
