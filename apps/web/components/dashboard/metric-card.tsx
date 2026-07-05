"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { AnimatedCounter } from "@/components/dashboard/animated-counter";

export function MetricCard({
  label,
  value,
  icon: Icon,
  tone = "violet",
  formatter,
  delta
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  tone?: "violet" | "success" | "warning" | "danger" | "cyan";
  formatter?: (value: number) => string;
  delta?: string;
}) {
  const tones = { violet: "border-violet-400/20 bg-violet-400/10 text-violet-200", success: "border-emerald-400/20 bg-emerald-400/10 text-emerald-200", warning: "border-amber-400/20 bg-amber-400/10 text-amber-200", danger: "border-red-400/20 bg-red-400/10 text-red-200", cyan: "border-cyan-400/20 bg-cyan-400/10 text-cyan-200" };
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ type: "spring", stiffness: 260, damping: 22 }}>
      <Card className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="mt-2 text-2xl font-semibold tracking-tight">
              <AnimatedCounter value={value} formatter={formatter} />
            </div>
          </div>
          <div className={`rounded-md border p-2 ${tones[tone]}`}>
            <Icon className="h-4 w-4" />
          </div>
        </div>
        {delta ? (
          <Badge variant={tone} className="mt-4">
            {delta}
          </Badge>
        ) : null}
      </Card>
    </motion.div>
  );
}
