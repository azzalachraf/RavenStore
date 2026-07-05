"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Modal({ open, onOpenChange, title, children }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; children: React.ReactNode }) {
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-50 bg-black/65 backdrop-blur-sm" /><Dialog.Content asChild><motion.div initial={{ opacity: 0, y: 20, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} className="glass fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[520px] max-w-[calc(100vw-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg p-5"><div className="flex items-center justify-between"><Dialog.Title className="text-lg font-semibold">{title}</Dialog.Title><Dialog.Close asChild><Button variant="ghost" size="icon" aria-label="Close"><X className="h-4 w-4" /></Button></Dialog.Close></div><div className="mt-5">{children}</div></motion.div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
