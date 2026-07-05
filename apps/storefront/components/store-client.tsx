"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Search, SlidersHorizontal } from "lucide-react";
import { api } from "@/lib/api";
import { eventHub } from "@/lib/events";
import { useI18n } from "@/components/providers";
import { ProductGrid } from "@/components/product-grid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { Category, Product } from "@/lib/types";

export function StoreClient({ initialProducts, categories: initialCategories }: { initialProducts: Product[]; categories: Category[] }) {
  const { t } = useI18n();
  const [products, setProducts] = React.useState(initialProducts);
  const [categories, setCategories] = React.useState(initialCategories);
  const [query, setQuery] = React.useState("");
  const [category, setCategory] = React.useState("all");
  const [filter, setFilter] = React.useState("all");
  const [page, setPage] = React.useState(1);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    const refreshProducts = () => void api.products("limit=24&offset=0", 0).then(setProducts).catch(() => undefined);
    const refreshCategories = () => void api.categories(0).then(setCategories).catch(() => undefined);
    const timer = window.setInterval(() => { refreshProducts(); refreshCategories(); }, 60000);
    const unsubscribe = eventHub.subscribe((event) => {
      if (event.cache_tags.includes("products") || event.cache_tags.includes("inventory")) refreshProducts();
      if (event.cache_tags.includes("categories")) refreshCategories();
    });
    return () => { window.clearInterval(timer); unsubscribe(); };
  }, []);

  const visible = React.useMemo(() => {
    let rows = products.filter((product) => category === "all" || product.category_id === category).filter((product) => !query || `${product.name_key} ${product.brand ?? ""} ${product.description_key ?? ""}`.toLowerCase().includes(query.toLowerCase()));
    if (filter === "featured") rows = rows.filter((product) => Boolean(product.product_metadata?.featured));
    if (filter === "newest") rows = [...rows].sort((a, b) => (b.created_at ?? "").localeCompare(a.created_at ?? ""));
    if (filter === "popular") rows = [...rows].sort((a, b) => Number(b.product_metadata?.sales ?? 0) - Number(a.product_metadata?.sales ?? 0));
    return rows;
  }, [category, filter, products, query]);

  const loadMore = async () => {
    setLoading(true);
    try { const next = await api.products(`limit=24&offset=${page * 24}`, 0); setProducts((current) => [...current, ...next.filter((item) => !current.some((row) => row.id === item.id))]); setPage((value) => value + 1); } finally { setLoading(false); }
  };

  return <div className="mx-auto min-h-screen max-w-7xl px-4 pb-20 pt-28"><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}><div className="text-sm text-violet-200">RavenStore API catalog</div><h1 className="mt-2 text-4xl font-semibold tracking-tight">{t("store.title")}</h1><p className="mt-3 max-w-2xl text-muted-foreground">{t("store.body")}</p></motion.div><div className="glass sticky top-24 z-20 mt-8 rounded-lg p-3"><div className="flex flex-wrap gap-2"><div className="relative min-w-[240px] flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("store.search")} className="pl-9" /></div><select aria-label={t("section.categories")} value={category} onChange={(event) => setCategory(event.target.value)} className="h-11 rounded-md border border-border bg-[#10121a] px-3 text-sm"><option value="all">{t("store.all")}</option>{categories.map((item) => <option key={item.id} value={item.id}>{t(item.name_key)}</option>)}</select><SlidersHorizontal className="my-auto h-4 w-4 text-muted-foreground" /></div><div className="mt-3 flex flex-wrap gap-2">{[["all", "store.all"], ["featured", "store.featured"], ["popular", "store.popular"], ["newest", "store.newest"]].map(([value, key]) => <Button key={value} size="sm" variant={filter === value ? "primary" : "ghost"} onClick={() => setFilter(value)}>{t(key)}</Button>)}</div></div><div className="mt-8">{visible.length ? <ProductGrid products={visible} /> : <div className="glass rounded-lg p-12 text-center text-muted-foreground">{t("store.empty")}</div>}</div><div className="mt-8 text-center"><Button variant="secondary" disabled={loading} onClick={() => void loadMore()}>{loading ? t("common.loading") : t("common.continue")}</Button></div></div>;
}
