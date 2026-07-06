export type UUID = string;

export type ProductVariant = {
  id: UUID;
  product_id: UUID;
  sku: string;
  name_key: string;
  duration_days?: number | null;
  region?: string | null;
  delivery_type: string;
  price_amount: string;
  cost_amount: string;
  currency: string;
  is_active: boolean;
  stock_available?: number | null;
  unlimited_stock?: boolean;
};

export type ProductImage = {
  id?: UUID;
  product_id?: UUID;
  url: string;
  alt_key?: string | null;
  sort_order?: number;
};

export type Product = {
  id: UUID;
  category_id: UUID;
  slug: string;
  name_key: string;
  description_key?: string | null;
  status: string;
  brand?: string | null;
  product_metadata: Record<string, unknown>;
  variants: ProductVariant[];
  images: ProductImage[];
  created_at?: string;
  updated_at?: string;
};

export type Category = {
  id: UUID;
  parent_id?: UUID | null;
  slug: string;
  name_key: string;
  description_key?: string | null;
  sort_order: number;
  is_active: boolean;
};

export type Order = {
  id: UUID;
  order_number: string;
  user_id: UUID;
  status: string;
  total_amount: string;
  cost_amount?: string;
  currency: string;
  created_at?: string;
  items?: Array<{ id: UUID; snapshot: Record<string, unknown>; quantity: number }>;
};

export type Payment = {
  id: UUID;
  order_id: UUID;
  provider: string;
  network: string;
  status: string;
  amount: string;
  currency: string;
};

export type User = {
  id: UUID;
  email: string;
  display_name?: string | null;
  status: string;
  locale: string;
  created_at?: string;
  wallet_balance?: number;
};

export type ActivityLog = {
  id: UUID;
  action: string;
  resource_type: string;
  resource_id?: UUID | null;
  created_at?: string;
  activity_metadata?: Record<string, unknown>;
};

export type AnalyticsSummary = {
  revenue: string;
  profit: string;
  orders: number;
  visitors: number;
  telegram_users: number;
  website_users: number;
  best_selling_products: Array<Record<string, unknown>>;
  top_categories: Array<Record<string, unknown>>;
  conversion_rate: string;
  payment_statistics: Record<string, number>;
};

export type SecurityOverview = {
  window_hours: number;
  failed_logins: number;
  suspicious_events: number;
  webhook_failures: number;
  payment_anomalies: number;
  system_errors: number;
  api_metrics: Record<string, number>;
  workers: Record<string, string>;
  recent_events: Array<{
    id: UUID;
    event_type: string;
    severity: string;
    outcome: string;
    actor_user_id?: UUID | null;
    trace_id?: string | null;
    created_at: string;
  }>;
};
