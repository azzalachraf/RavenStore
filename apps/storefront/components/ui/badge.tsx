import * as React from "react";
import { cn } from "@/lib/utils";
const tones = { default: "border-white/10 bg-white/[.06] text-muted-foreground", success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200", warning: "border-amber-400/20 bg-amber-400/10 text-amber-200", danger: "border-red-400/20 bg-red-400/10 text-red-200", violet: "border-violet-400/25 bg-violet-400/12 text-violet-200" };
export function Badge({ tone = "default", className, ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) { return <span className={cn("inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium", tones[tone], className)} {...props} />; }
