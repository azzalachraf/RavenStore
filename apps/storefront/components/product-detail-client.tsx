"use client";

import * as React from "react";
import Image from "next/image";
import Link from "next/link";
import * as Tabs from "@radix-ui/react-tabs";
import { motion } from "framer-motion";
import { Bot, CheckCircle2, Clock3, PackageCheck, ShieldCheck, ShoppingBag } from "lucide-react";
import { api } from "@/lib/api";
import { eventHub } from "@/lib/events";
import { useI18n } from "@/components/providers";
import { ProductGrid } from "@/components/product-grid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/types";
import { money } from "@/lib/utils";

export function ProductDetailClient({ initialProduct, recommendations }: { initialProduct: Product; recommendations: Product[] }) {
  const { t } = useI18n();
  const [product, setProduct] = React.useState(initialProduct);
  const [selectedImage, setSelectedImage] = React.useState(0);
  React.useEffect(() => {
    const refresh = () => void api.product(product.slug, 0).then(setProduct).catch(() => undefined);
    const timer = window.setInterval(refresh, 60000);
    const unsubscribe = eventHub.subscribe((event) => {
      if (event.cache_tags.includes("products") || event.cache_tags.includes("inventory")) refresh();
    });
    return () => { window.clearInterval(timer); unsubscribe(); };
  }, [product.slug]);
  const variant = product.variants.find((item) => item.is_active) ?? product.variants[0];
  const metadata = product.product_metadata ?? {};
  const stock = variant?.unlimited_stock ? t("product.available") : variant?.stock_available != null ? `${variant.stock_available} ${t("product.available")}` : Number(metadata.stock ?? 0) > 0 ? `${metadata.stock} ${t("product.available")}` : t("product.available");
  return <div className="mx-auto max-w-7xl px-4 pb-20 pt-28"><div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr]"><div><div className="relative aspect-square overflow-hidden rounded-lg border border-border bg-[#10121c]">{product.images[selectedImage]?.url ? <Image src={product.images[selectedImage].url} alt={t(product.name_key)} fill priority sizes="(max-width: 1024px) 100vw, 55vw" className="object-cover" /> : <div className="flex h-full items-center justify-center"><Bot className="h-24 w-24 text-violet-300/60" /></div>}</div>{product.images.length > 1 ? <div className="mt-3 grid grid-cols-5 gap-2">{product.images.map((image, index) => <button key={image.id ?? image.url} aria-label={`Image ${index + 1}`} onClick={() => setSelectedImage(index)} className={`relative aspect-square overflow-hidden rounded-md border ${selectedImage === index ? "border-violet-400" : "border-border"}`}><Image src={image.url} alt="" fill sizes="120px" className="object-cover" /></button>)}</div> : null}</div><motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }}><Badge tone="violet">{product.brand ?? "RavenStore"}</Badge><h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">{t(product.name_key)}</h1><p className="mt-4 text-base leading-7 text-muted-foreground">{product.description_key ? t(product.description_key) : ""}</p><div className="mt-6 text-3xl font-semibold">{variant ? money(variant.price_amount, variant.currency) : "—"}</div><div className="mt-6 grid grid-cols-2 gap-3"><Spec icon={Clock3} label={t("product.duration")} value={variant?.duration_days ? t("product.days", { days: variant.duration_days }) : t("product.instant")} /><Spec icon={ShieldCheck} label={t("product.warranty")} value={metadata.warranty_days ? t("product.days", { days: Number(metadata.warranty_days) }) : t("product.instant")} /><Spec icon={PackageCheck} label={t("product.stock")} value={stock} /><Spec icon={CheckCircle2} label={t("product.delivery")} value={variant?.delivery_type ?? t("product.instant")} /></div>{variant ? <Link href={`/checkout/${product.slug}`} className="mt-6 block"><Button className="w-full"><ShoppingBag className="h-4 w-4" />{t("product.buy")}</Button></Link> : <Button disabled className="mt-6 w-full">{t("product.unavailable")}</Button>}<a href={process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/RavenStoreBot"} target="_blank" rel="noreferrer" className="mt-3 block"><Button variant="secondary" className="w-full"><Bot className="h-4 w-4" />{t("nav.telegram")}</Button></a></motion.div></div><Tabs.Root defaultValue="description" className="mt-12"><Tabs.List className="flex gap-1 overflow-x-auto border-b border-border">{[["description", "product.description"], ["specs", "product.specifications"], ["reviews", "product.reviews"]].map(([value, key]) => <Tabs.Trigger key={value} value={value} className="whitespace-nowrap border-b-2 border-transparent px-4 py-3 text-sm text-muted-foreground data-[state=active]:border-violet-400 data-[state=active]:text-foreground">{t(key)}</Tabs.Trigger>)}</Tabs.List><Tabs.Content value="description" className="py-6 text-sm leading-7 text-muted-foreground">{product.description_key ? t(product.description_key) : t("product.description")}</Tabs.Content><Tabs.Content value="specs" className="py-6"><Card className="grid gap-3 p-4 sm:grid-cols-2">{Object.entries(metadata).map(([key, value]) => <div key={key} className="flex justify-between gap-4 border-b border-border py-2 text-sm"><span className="text-muted-foreground">{key}</span><span>{String(value)}</span></div>)}</Card></Tabs.Content><Tabs.Content value="reviews" className="py-6"><Card className="p-6 text-sm text-muted-foreground">Verified product reviews will appear when returned by the RavenStore API.</Card></Tabs.Content></Tabs.Root>{recommendations.length ? <section className="mt-14"><h2 className="text-2xl font-semibold">{t("product.recommendations")}</h2><div className="mt-6"><ProductGrid products={recommendations.slice(0, 4)} /></div></section> : null}</div>;
}

function Spec({ icon: Icon, label, value }: { icon: typeof Clock3; label: string; value: string }) { return <Card className="p-3"><Icon className="h-4 w-4 text-violet-200" /><div className="mt-2 text-xs text-muted-foreground">{label}</div><div className="mt-1 break-words text-sm font-medium">{value}</div></Card>; }
