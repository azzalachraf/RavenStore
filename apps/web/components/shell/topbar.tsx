"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { motion } from "framer-motion";
import Link from "next/link";
import { Bell, Bolt, ChevronRight, Inbox, KeyRound, Menu, Plus, Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdminToken } from "@/lib/hooks";
import { navItems } from "@/components/shell/nav-items";
import { EmptyState } from "@/components/ui/empty-state";

export function Topbar({ onCommand }: { onCommand: () => void }) {
  const pathname = usePathname();
  const { token, setToken } = useAdminToken();
  const segments = pathname.split("/").filter(Boolean);
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-3 z-40 mx-3 mt-3 rounded-lg border border-white/[0.075] bg-[#0b0d15]/78 p-3 shadow-panel backdrop-blur-2xl"
    >
      <div className="flex flex-wrap items-center gap-3">
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <Button variant="outline" size="icon" className="lg:hidden" aria-label="Open navigation">
              <Menu className="h-4 w-4" />
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Content align="start" className="glass-panel z-50 grid max-h-[70vh] w-72 gap-1 overflow-y-auto rounded-lg p-2">
            {navItems.map((item) => (
              <DropdownMenu.Item key={item.href} asChild>
                <Link href={item.href} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm outline-none focus:bg-white/[0.07]">
                  <item.icon className="h-4 w-4 text-violet-200" />
                  {item.label}
                </Link>
              </DropdownMenu.Item>
            ))}
          </DropdownMenu.Content>
        </DropdownMenu.Root>
        <div className="flex min-w-[180px] items-center gap-1 text-sm text-muted-foreground">
          <span>Admin</span>
          {segments.length ? <ChevronRight className="h-3 w-3" /> : null}
          <span className="text-foreground">{segments[0] ?? "Dashboard"}</span>
        </div>
        <button
          onClick={onCommand}
          className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-md border border-border bg-white/[0.04] px-3 text-left text-sm text-muted-foreground transition hover:bg-white/[0.07]"
        >
          <Search className="h-4 w-4" />
          <span className="truncate">Search products, orders, customers...</span>
          <kbd className="ml-auto rounded border border-white/10 bg-white/[0.06] px-1.5 py-0.5 text-[10px]">Ctrl K</kbd>
        </button>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <Button variant="outline" size="icon" aria-label="Notifications">
              <Bell className="h-4 w-4" />
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Content align="end" className="glass-panel z-50 w-80 rounded-lg p-2">
            <EmptyState icon={Inbox} title="You're all caught up" description="New operational alerts will appear here in real time." className="min-h-44" />
          </DropdownMenu.Content>
        </DropdownMenu.Root>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <Button>
              <Bolt className="h-4 w-4" />
              Actions
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Content align="end" className="glass-panel z-50 w-56 rounded-lg p-2">
            {([{ label: "Create product", href: "/products" }, { label: "Verify payment", href: "/payments" }, { label: "Upload inventory", href: "/delivery" }, { label: "Export analytics", href: "/analytics" }] as const).map((item) => <DropdownMenu.Item key={item.label} asChild><Link href={item.href} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm outline-none transition focus:bg-white/[0.07]"><Plus className="h-4 w-4 text-violet-200" />{item.label}</Link></DropdownMenu.Item>)}
          </DropdownMenu.Content>
        </DropdownMenu.Root>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <Button variant={token ? "secondary" : "outline"} size="icon" aria-label="API token">
              <KeyRound className="h-4 w-4" />
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Content align="end" className="glass-panel z-50 w-96 rounded-lg p-3">
            <div className="mb-2 text-xs text-muted-foreground">Admin API token</div>
            <Input
              type="password"
              defaultValue={token ?? ""}
              placeholder="Paste JWT access token"
              onBlur={(event) => setToken(event.currentTarget.value || null)}
            />
          </DropdownMenu.Content>
        </DropdownMenu.Root>
      </div>
    </motion.header>
  );
}
