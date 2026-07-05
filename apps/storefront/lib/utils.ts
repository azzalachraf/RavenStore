import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export function money(value: number | string, currency = "USD") {
  const amount = typeof value === "string" ? Number(value) : value;
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number.isFinite(amount) ? amount : 0);
}

export function statusTone(status: string) {
  const value = status.toLowerCase();
  if (value.includes("fail") || value.includes("cancel")) return "danger";
  if (value.includes("pending") || value.includes("queue")) return "warning";
  if (value.includes("paid") || value.includes("complete") || value.includes("active")) return "success";
  return "default";
}
