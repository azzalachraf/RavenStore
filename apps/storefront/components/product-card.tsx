"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowUpRight, Bot, CheckCircle2, CircleOff } from "lucide-react";
import { useI18n } from "@/components/providers";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Product } from "@/lib/types";
import { money } from "@/lib/utils";

export function ProductCard({ product }: { product: Product }) {
  const { t } = useI18n();
  const variant = product.variants.find((item) => item.is_active) ?? product.variants[0];
  const image = product.images?.[0]?.url;
  const featured = Boolean(product.product_metadata?.featured);
  const available = Boolean(variant && (variant.unlimited_stock || variant.stock_available == null || variant.stock_available > 0));
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 260, damping: 24 }}>
      <Link href={`/products/${product.slug}`}>
        <Card className="group overflow-hidden">
          <div className="relative aspect-[4/3] overflow-hidden border-b border-border bg-[#10121c]">
            {image ? <Image src={image} alt={t(product.name_key)} fill sizes="(max-width: 768px) 100vw, 33vw" className="object-cover transition duration-500 group-hover:scale-[1.035]" /> : <div className="flex h-full items-center justify-center"><Bot className="h-16 w-16 text-violet-300/60" /></div>}
            {featured ? <Badge tone="violet" className="absolute left-3 top-3">{t("store.featured")}</Badge> : null}
            <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/55 to-transparent opacity-0 transition group-hover:opacity-100" />
          </div>
          <div className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0"><h3 className="truncate font-semibold">{t(product.name_key)}</h3><p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{product.description_key ? t(product.description_key) : product.brand}</p></div>
              <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-violet-200" />
            </div>
            <div className="mt-4 flex items-end justify-between gap-3">
              <div className="text-lg font-semibold">{variant ? money(variant.price_amount, variant.currency) : "—"}</div>
              <div className={`flex items-center gap-1 text-xs ${available ? "text-emerald-300" : "text-amber-300"}`}>
                {available ? <CheckCircle2 className="h-3.5 w-3.5" /> : <CircleOff className="h-3.5 w-3.5" />}
                {available ? t("product.available") : t("product.unavailable")}
              </div>
            </div>
          </div>
        </Card>
      </Link>
    </motion.div>
  );
}
