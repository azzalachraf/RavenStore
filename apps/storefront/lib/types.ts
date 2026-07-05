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
  currency: string;
  is_active: boolean;
  stock_available?: number | null;
  unlimited_stock?: boolean;
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
  images: Array<{ id?: UUID; url: string; alt_key?: string | null; sort_order?: number }>;
  created_at?: string;
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
  status: string;
  total_amount: string;
  currency: string;
  created_at?: string;
  items: Array<{ id: UUID; product_id: UUID; product_variant_id: UUID; quantity: number; snapshot: Record<string, unknown> }>;
};

export type PaymentCreated = {
  payment: { id: UUID; order_id: UUID; provider: string; network: string; status: string; amount: string; currency: string; payment_address?: string | null; expires_at: string };
  payment_token: string;
};

export type User = { id: UUID; email: string; display_name?: string | null; status: string; locale: string; last_login_at?: string | null };
export type Notification = { id: UUID; title_key: string; body_key: string; status: string; channel: string; created_at: string; payload: Record<string, unknown> };
export type SupportTicket = { id: UUID; subject_key: string; status: string; priority: string; created_at: string };
