import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

const styles = { info: [Info, "border-cyan-400/20 bg-cyan-400/[.07] text-cyan-100"], success: [CheckCircle2, "border-emerald-400/20 bg-emerald-400/[.07] text-emerald-100"], warning: [TriangleAlert, "border-amber-400/20 bg-amber-400/[.07] text-amber-100"], danger: [AlertCircle, "border-red-400/20 bg-red-400/[.07] text-red-100"] } as const;
export function Alert({ tone = "info", title, children, className }: { tone?: keyof typeof styles; title: string; children?: React.ReactNode; className?: string }) { const [Icon, style] = styles[tone]; return <div role="status" className={cn("flex gap-3 rounded-lg border p-3", style, className)}><Icon className="mt-0.5 h-4 w-4 shrink-0" /><div><div className="text-sm font-semibold">{title}</div>{children ? <div className="mt-1 text-xs leading-5 opacity-75">{children}</div> : null}</div></div>; }
