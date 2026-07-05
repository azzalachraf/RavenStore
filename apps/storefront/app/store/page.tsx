import type { Metadata } from "next";
import { api } from "@/lib/api";
import { StoreClient } from "@/components/store-client";

export const metadata: Metadata = { title: "Store", description: "Browse RavenStore digital subscriptions with live pricing and availability." };

export default async function StorePage() {
  const [products, categories] = await Promise.all([api.products("limit=24&offset=0", 10).catch(() => []), api.categories(30).catch(() => [])]);
  return <StoreClient initialProducts={products} categories={categories} />;
}
