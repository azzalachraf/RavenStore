"use client";

import * as TooltipPrimitive from "@radix-ui/react-tooltip";

export function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return <TooltipPrimitive.Provider delayDuration={350}><TooltipPrimitive.Root><TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger><TooltipPrimitive.Portal><TooltipPrimitive.Content sideOffset={7} className="z-[100] rounded-md border border-white/10 bg-[#11131c] px-2 py-1 text-xs text-foreground shadow-float animate-in fade-in zoom-in-95">{label}<TooltipPrimitive.Arrow className="fill-[#11131c]" /></TooltipPrimitive.Content></TooltipPrimitive.Portal></TooltipPrimitive.Root></TooltipPrimitive.Provider>;
}
