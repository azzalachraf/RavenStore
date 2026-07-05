"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight, Command, Feather, Radio } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { navItems } from "@/components/shell/nav-items";
import { Tooltip } from "@/components/ui/tooltip";

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  return (
    <motion.aside
      animate={{ width: collapsed ? 84 : 264 }}
      transition={{ type: "spring", stiffness: 260, damping: 28 }}
      className="sticky top-0 hidden h-screen shrink-0 border-r border-white/[0.065] bg-[#090b12]/82 px-3 py-4 backdrop-blur-2xl lg:block"
    >
      <div className="flex items-center justify-between px-2">
        <Link href="/" className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md border border-violet-300/20 bg-violet-500 text-primary-foreground shadow-glow">
            <Feather className="h-4 w-4" />
          </div>
          {!collapsed ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div className="text-sm font-semibold">RavenStore</div>
              <div className="text-xs text-muted-foreground">Control Plane</div>
            </motion.div>
          ) : null}
        </Link>
        <Button variant="ghost" size="icon" onClick={onToggle} aria-label="Toggle sidebar">
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>
      <div className="mt-6 space-y-1">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Tooltip label={item.label} key={item.href}>
            <Link
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "group relative flex h-10 items-center gap-3 rounded-md px-3 text-sm text-muted-foreground transition duration-200 hover:bg-white/[0.055] hover:text-foreground",
                active && "bg-violet-400/[.1] text-violet-100"
              )}
            >
              {active ? <motion.span layoutId="sidebar-active" className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-violet-400" /> : null}
              <Icon className={cn("h-4 w-4 shrink-0 transition-colors", active && "text-violet-300")} />
              {!collapsed ? <span className="truncate">{item.label}</span> : null}
            </Link>
            </Tooltip>
          );
        })}
      </div>
      <div className="absolute bottom-4 left-3 right-3 rounded-lg border border-white/[0.07] bg-white/[0.025] p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><Radio className="h-3.5 w-3.5 text-emerald-300" />{!collapsed ? <span>Live control plane</span> : null}</div>
        {!collapsed ? <div className="mt-2 flex items-center gap-2 border-t border-white/[0.06] pt-2 text-[11px] text-muted-foreground"><Command className="h-3.5 w-3.5" /><span>Ctrl K to navigate</span></div> : null}
      </div>
    </motion.aside>
  );
}
