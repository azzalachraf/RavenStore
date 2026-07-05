import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | string, currency = "USD") {
  const amount = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2
  }).format(Number.isFinite(amount) ? amount : 0);
}

export function compactNumber(value: number | string) {
  const amount = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-US", { notation: "compact" }).format(Number.isFinite(amount) ? amount : 0);
}

export function percentage(value: number | string) {
  const amount = typeof value === "string" ? Number(value) : value;
  return `${(Number.isFinite(amount) ? amount * 100 : 0).toFixed(1)}%`;
}

export function stableId(prefix: string) {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

