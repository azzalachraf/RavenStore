import type { AnalyticsSummary, Category, Order, Payment, Product, User, ActivityLog, SecurityOverview } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ApiError = {
  messageKey: string;
  status: number;
};

export class RavenApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  async analyticsSummary() {
    return this.request<AnalyticsSummary>("/analytics/summary");
  }

  async products() {
    return this.request<Product[]>("/admin/products");
  }

  async createProduct(payload: Partial<Product>) {
    return this.request<Product>("/products", { method: "POST", body: payload, idempotent: true });
  }

  async updateProduct(id: string, payload: Partial<Product>) {
    return this.request<Product>(`/products/${id}`, { method: "PATCH", body: payload, idempotent: true });
  }

  async createVariant(payload: Record<string, unknown>) {
    return this.request<Product["variants"][number]>("/products/variants", { method: "POST", body: payload, idempotent: true });
  }

  async updateVariant(id: string, payload: Record<string, unknown>) {
    return this.request<Product["variants"][number]>(`/products/variants/${id}`, { method: "PATCH", body: payload, idempotent: true });
  }

  async updateInventory(variantId: string, payload: { quantity_available: number; unlimited_stock: boolean; low_stock_threshold?: number }) {
    return this.request(`/admin/variants/${variantId}/inventory`, { method: "PATCH", body: payload, idempotent: true });
  }

  async deleteProduct(id: string) {
    return this.request<Product>(`/products/${id}`, { method: "DELETE", idempotent: true });
  }

  async uploadProductImage(productId: string, file: File) {
    const body = new FormData();
    body.append("file", file);
    return this.request<Product["images"][number]>(`/admin/products/${productId}/images`, {
      method: "POST",
      body,
      idempotent: true
    });
  }

  async categories() {
    return this.request<Category[]>("/categories");
  }

  async createCategory(payload: Partial<Category>) {
    return this.request<Category>("/categories", { method: "POST", body: payload, idempotent: true });
  }

  async adminOrders() {
    return this.request<Order[]>("/admin/orders");
  }

  async payments() {
    return this.request<Payment[]>("/admin/payments");
  }

  async customers() {
    return this.request<User[]>("/admin/users");
  }

  async adjustWallet(userId: string, payload: { amount: number; description?: string }) {
    return this.request(`/admin/users/${userId}/wallet/adjust`, { method: "POST", body: payload, idempotent: true });
  }

  async activity() {
    return this.request<ActivityLog[]>("/admin/activity");
  }

  async eventHealth() {
    return this.request<{
      redis: string;
      outbox_pending: number;
      dead_letters: number;
      failed_deliveries: number;
      stale_consumers: number;
      transport_metrics: Record<string, Record<string, number>>;
    }>("/events/health");
  }

  async securityOverview() {
    return this.request<SecurityOverview>("/admin/security/overview");
  }

  async settings() {
    return this.request<Array<{ id: string; key: string; value: Record<string, unknown>; is_secret: boolean }>>("/settings");
  }

  async updateSetting(key: string, value: Record<string, unknown>, isSecret = false) {
    return this.request(`/settings/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: { value, is_secret: isSecret },
      idempotent: true
    });
  }

  async translations(language: string) {
    return this.request<Record<string, string>>(`/languages/${language}/translations`);
  }

  async updateTranslation(language: string, key: string, value: string) {
    return this.request(`/languages/${encodeURIComponent(language)}/translations/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: { value },
      idempotent: true
    });
  }

  private async request<T>(path: string, options: { method?: string; body?: unknown; idempotent?: boolean } = {}): Promise<T> {
    const isFormData = options.body instanceof FormData;
    const headers: Record<string, string> = { "X-Request-ID": crypto.randomUUID() };
    if (!isFormData) headers["Content-Type"] = "application/json";
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (options.idempotent) headers["Idempotency-Key"] = `web-${crypto.randomUUID()}`;
    const requestBody: BodyInit | undefined = options.body
      ? isFormData
        ? (options.body as FormData)
        : JSON.stringify(options.body)
      : undefined;
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: requestBody,
      cache: "no-store"
    });
    if (!response.ok) {
      let messageKey = "error.unexpected";
      try {
        const body = await response.json();
        messageKey = body.error?.message_key ?? body.detail ?? messageKey;
      } catch {
        messageKey = response.statusText || messageKey;
      }
      throw { messageKey, status: response.status } satisfies ApiError;
    }
    if (response.status === 204) return {} as T;
    return response.json() as Promise<T>;
  }
}

export const ravenApi = new RavenApiClient();
