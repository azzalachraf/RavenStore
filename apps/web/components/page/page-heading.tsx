import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function PageHeading({
  title,
  eyebrow,
  actions = []
}: {
  title: string;
  eyebrow: string;
  actions?: Array<{ label: string; value: number; icon: LucideIcon }>;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="text-xs font-medium text-muted-foreground">{eyebrow}</div>
        <h1 className="mt-1 text-2xl font-semibold">{title}</h1>
      </div>
      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <div key={action.label} className="glass-panel flex items-center gap-2 rounded-lg px-3 py-2 text-sm">
            <action.icon className="h-4 w-4 text-violet-200" />
            <span className="text-muted-foreground">{action.label}</span>
            <span className="font-semibold">{action.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const variant =
    normalized.includes("fail")
      ? "danger"
      : normalized.includes("pending")
        ? "warning"
        : normalized.includes("paid") || normalized.includes("complete") || normalized.includes("active")
          ? "success"
          : "default";
  return <Badge variant={variant}>{status}</Badge>;
}
