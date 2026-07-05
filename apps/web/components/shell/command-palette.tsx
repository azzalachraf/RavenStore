"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { navItems } from "@/components/shell/nav-items";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
        <Dialog.Content asChild>
          <motion.div
            initial={{ opacity: 0, y: 22, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            className="glass-panel fixed left-1/2 top-[15vh] z-50 w-[640px] max-w-[calc(100vw-2rem)] -translate-x-1/2 overflow-hidden rounded-lg"
          >
            <Command className="bg-transparent">
              <div className="flex items-center gap-3 border-b border-border px-4">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Command.Input
                  autoFocus
                  className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                  placeholder="Search actions, pages, records..."
                />
              </div>
              <Command.List className="max-h-[420px] overflow-y-auto p-2">
                <Command.Empty className="px-3 py-8 text-center text-sm text-muted-foreground">No results</Command.Empty>
                <Command.Group heading="Navigate" className="text-xs text-muted-foreground">
                  {navItems.slice(0, 16).map((item) => (
                    <Command.Item
                      key={item.href}
                      value={item.label}
                      onSelect={() => {
                        router.push(item.href);
                        onOpenChange(false);
                      }}
                      className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-foreground aria-selected:bg-white/[0.07]"
                    >
                      <item.icon className="h-4 w-4 text-muted-foreground" />
                      {item.label}
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

