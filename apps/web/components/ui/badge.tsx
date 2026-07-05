import * as React from "react";
import { cn } from "@/lib/utils";

const tone = {
  default: "border-white/10 bg-white/[0.06] text-muted-foreground",
  success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200",
  warning: "border-amber-400/20 bg-amber-400/10 text-amber-200",
  danger: "border-red-400/20 bg-red-400/10 text-red-200",
  violet: "border-violet-400/25 bg-violet-400/12 text-violet-200",
  cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200"
};

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: keyof typeof tone }) {
  return (
    <span
      className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium", tone[variant], className)}
      {...props}
    />
  );
}

