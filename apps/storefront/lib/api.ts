import type { Category, Notification, Order, PaymentCreated, Product, SupportTicket, User } from "@/lib/types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(public messageKey: string, public status: number) { super(messageKey); }
}

async function request<T>(path: string, options: { method?: string; body?: unknown; token?: string | null; revalidate?: number; idempotent?: boolean } = {}) {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.idempotent) headers["Idempotency-Key"] = `web-${crypto.randomUUID()}`;
  const response = await fetch(`${baseUrl}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: options.revalidate === 0 ? "no-store" : undefined,
    next: options.revalidate === undefined ? undefined : { revalidate: options.revalidate }
  });
  if (!response.ok) {
    let key = "error.unexpected";
    try {
      const body = await response.json();
      key = body.error?.message_key ?? body.detail ?? key;
    } catch { key = response.statusText || key; }
    throw new ApiError(key, response.status);
  }
  return (response.status === 204 ? {} : await response.json()) as T;
}

export const api = {
  products: (params = "limit=24&offset=0", revalidate = 15) => request<Product[]>(`/products?${params}`, { revalidate }),
  product: (slug: string, revalidate = 15) => request<Product>(`/products/${encodeURIComponent(slug)}`, { revalidate }),
  categories: (revalidate = 30) => request<Category[]>("/categories", { revalidate }),
  translations: (locale: string, revalidate = 60) => request<Record<string, string>>(`/languages/${locale}/translations`, { revalidate }),
  register: (body: { email: string; password: string; display_name?: string; locale: string }) => request<{ access_token: string; refresh_token: string }>("/auth/register", { method: "POST", body, idempotent: true }),
  login: (body: { email: string; password: string }) => request<{ access_token: string; refresh_token: string }>("/auth/login", { method: "POST", body }),
  refresh: (refreshToken: string) => request<{ access_token: string; refresh_token: string }>("/auth/refresh", { method: "POST", body: { refresh_token: refreshToken } }),
  logout: (refreshToken: string) => request<void>("/auth/logout", { method: "POST", body: { refresh_token: refreshToken } }),
  me: (token: string) => request<User>("/users/me", { token, revalidate: 0 }),
  orders: (token: string) => request<Order[]>("/orders", { token, revalidate: 0 }),
  createOrder: (token: string, variantId: string) => request<Order>("/orders", { method: "POST", token, idempotent: true, body: { items: [{ product_variant_id: variantId, quantity: 1 }] } }),
  createPayment: (token: string, orderId: string, method: string) => request<PaymentCreated>("/payments/request", { method: "POST", token, idempotent: true, body: { order_id: orderId, method } }),
  verifyPayment: (paymentToken: string, txHash: string) => request<{ id: string; message_key: string }>("/payments/verify", { method: "POST", idempotent: true, body: { payment_token: paymentToken, tx_hash: txHash } }),
  referrals: (token: string) => request<Array<{ id: string; code: string; reward_amount: string; status: string }>>("/referral", { token, revalidate: 0 }),
  notifications: (token: string) => request<Notification[]>("/notifications", { token, revalidate: 0 }),
  supportTickets: (token: string) => request<SupportTicket[]>("/support/tickets", { token, revalidate: 0 }),
  createTicket: (token: string, body: { subject_key: string; message: string }) => request<SupportTicket>("/support/tickets", { method: "POST", token, idempotent: true, body }),
  updateSettings: (token: string, body: Record<string, unknown>) => request<Record<string, unknown>>("/users/me/settings", { method: "PATCH", token, idempotent: true, body })
};
