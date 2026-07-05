import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({ title, description, icon: Icon = Inbox, action, className }: { title: string; description?: string; icon?: LucideIcon; action?: React.ReactNode; className?: string }) {
  return <div className={cn("flex min-h-52 flex-col items-center justify-center px-6 py-10 text-center", className)}><div className="flex h-10 w-10 items-center justify-center rounded-lg border border-violet-400/20 bg-violet-400/10 text-violet-200"><Icon className="h-5 w-5" /></div><h3 className="mt-4 text-sm font-semibold">{title}</h3>{description ? <p className="mt-1 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p> : null}{action ? <div className="mt-4">{action}</div> : null}</div>;
}
