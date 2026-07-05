"use client";

import * as React from "react";
import * as ToastPrimitives from "@radix-ui/react-toast";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

type Toast = { id: string; title: string; description?: string; tone: "success" | "error" | "info" };

type ToastContextValue = { success: (title: string, description?: string) => void; error: (title: string, description?: string) => void; info: (title: string, description?: string) => void };
const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<Toast[]>([]);
  const push = React.useCallback((tone: Toast["tone"], title: string, description?: string) => {
    const id = crypto.randomUUID();
    setItems((current) => [...current, { id, title, description, tone }]);
    window.setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), 3600);
  }, []);
  const success = React.useCallback((title: string, description?: string) => push("success", title, description), [push]);
  const error = React.useCallback((title: string, description?: string) => push("error", title, description), [push]);
  const info = React.useCallback((title: string, description?: string) => push("info", title, description), [push]);
  return (
    <ToastContext.Provider value={{ success, error, info }}>
      <ToastPrimitives.Provider swipeDirection="right">
        {children}
        <ToastPrimitives.Viewport className="fixed bottom-4 right-4 z-50 flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
        <AnimatePresence>
          {items.map((item) => (
            <ToastPrimitives.Root key={item.id} asChild open>
              <motion.div
                initial={{ opacity: 0, y: 18, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.98 }}
                className="glass-panel flex items-start gap-3 rounded-lg p-4"
              >
                {item.tone === "success" ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-300" /> : item.tone === "error" ? <AlertCircle className="mt-0.5 h-5 w-5 text-red-300" /> : <Info className="mt-0.5 h-5 w-5 text-cyan-300" />}
                <div>
                  <ToastPrimitives.Title className="text-sm font-medium">{item.title}</ToastPrimitives.Title>
                  {item.description ? (
                    <ToastPrimitives.Description className="mt-1 text-xs text-muted-foreground">
                      {item.description}
                    </ToastPrimitives.Description>
                  ) : null}
                </div>
              </motion.div>
            </ToastPrimitives.Root>
          ))}
        </AnimatePresence>
      </ToastPrimitives.Provider>
    </ToastContext.Provider>
  );
}

export function Toaster() {
  return null;
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
