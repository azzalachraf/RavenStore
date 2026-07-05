"use client";

import Image from "next/image";
import Link from "next/link";
import * as React from "react";
import * as Accordion from "@radix-ui/react-accordion";
import { motion } from "framer-motion";
import {
  ArrowRight,
  ChevronDown,
  CircleCheck,
  Headphones,
  LockKeyhole,
  MessageSquare,
  Send,
  Sparkles,
  Zap,
} from "lucide-react";
import { useI18n } from "@/components/providers";
import { api } from "@/lib/api";
import { eventHub } from "@/lib/events";
import { ProductGrid } from "@/components/product-grid";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import type { Category, Product } from "@/lib/types";

export function LandingPage({
  initialProducts,
  categories,
}: {
  initialProducts: Product[];
  categories: Category[];
}) {
  const { t } = useI18n();
  const [products, setProducts] = React.useState(initialProducts);
  const [categoryRows, setCategoryRows] = React.useState(categories);
  React.useEffect(() => eventHub.subscribe((event) => {
    if (event.cache_tags.includes("products") || event.cache_tags.includes("inventory")) {
      void api.products("limit=8&offset=0&filter=featured", 0).then(setProducts).catch(() => undefined);
    }
    if (event.cache_tags.includes("categories")) {
      void api.categories(0).then(setCategoryRows).catch(() => undefined);
    }
  }), []);
  const telegram =
    process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/RavenStoreBot";
  const why = [
    {
      icon: Zap,
      title: "why.fast",
      body: "why.fastBody",
      tone: "text-amber-300",
    },
    {
      icon: LockKeyhole,
      title: "why.secure",
      body: "why.secureBody",
      tone: "text-emerald-300",
    },
    {
      icon: Headphones,
      title: "why.support",
      body: "why.supportBody",
      tone: "text-cyan-300",
    },
  ];
  return (
    <div className="overflow-hidden">
      <section className="relative min-h-[92svh] border-b border-border">
        <Image
          src="/images/ravenstore-hero.png"
          alt="RavenStore Telegram-first marketplace"
          fill
          priority
          sizes="100vw"
          className="object-cover object-[68%_center]"
        />
        <div className="hero-shade absolute inset-0" />
        <div className="particle-field pointer-events-none absolute inset-0 opacity-30" />
        <div className="relative mx-auto flex min-h-[92svh] w-full max-w-7xl items-center px-4 pb-24 pt-28">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65 }}
            className="w-full min-w-0 max-w-2xl"
          >
            <Badge tone="violet">
              <Sparkles className="me-1 h-3.5 w-3.5" />
              {t("hero.eyebrow")}
            </Badge>
            <h1 className="mt-5 max-w-xl break-words text-3xl font-semibold leading-[1.12] tracking-tight sm:text-5xl lg:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-zinc-300 sm:text-lg">
              {t("hero.body")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/store">
                <Button>
                  {t("hero.primary")}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <a href={telegram} target="_blank" rel="noreferrer">
                <Button variant="secondary">
                  <Send className="h-4 w-4" />
                  {t("hero.secondary")}
                </Button>
              </a>
            </div>
            <div className="mt-6 flex items-center gap-2 text-xs text-zinc-400">
              <CircleCheck className="h-4 w-4 text-emerald-300" />
              {t("hero.trust")}
            </div>
          </motion.div>
        </div>
        <div className="absolute bottom-0 left-1/2 w-full max-w-7xl -translate-x-1/2 px-4">
          <div className="glass grid grid-cols-2 gap-px overflow-hidden rounded-t-lg md:grid-cols-4">
            {[
              [products.length, "Products live"],
              [categoryRows.length, "Categories"],
              [3, "Payment rails"],
              [2, "Support surfaces"],
            ].map(([value, label], index) => (
              <motion.div key={label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .45 + index * .06 }} className="bg-black/10 px-4 py-4">
                <div className="text-xl font-semibold">{value}</div>
                <div className="text-xs text-muted-foreground">{label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-4 py-20">
        <SectionHead
          title={t("section.featured")}
          body={t("section.featuredBody")}
          action={
            <Link href="/store" className="text-sm text-violet-200">
              {t("common.viewAll")} <ArrowRight className="inline h-4 w-4" />
            </Link>
          }
        />
        <div className="mt-8">
          <ProductGrid products={products} />
        </div>
      </section>
      <section className="border-y border-border bg-white/[.018]">
        <div className="mx-auto max-w-7xl px-4 py-20">
          <SectionHead title={t("section.categories")} />
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {categoryRows.slice(0, 8).map((category, index) => (
              <motion.div key={category.id} whileHover={{ x: 4 }}>
                <Link href={`/store?category=${category.id}`}>
                  <Card className="flex items-center justify-between p-4">
                    <div>
                      <div className="text-xs text-muted-foreground">
                        0{index + 1}
                      </div>
                      <div className="mt-2 font-medium">
                        {t(category.name_key)}
                      </div>
                    </div>
                    <ArrowRight className="h-4 w-4 text-violet-200" />
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-4 py-20">
        <SectionHead title={t("section.why")} />
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {why.map((item) => (
            <Card key={item.title} className="p-5">
              <item.icon className={`h-6 w-6 ${item.tone}`} />
              <h3 className="mt-5 font-semibold">{t(item.title)}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t(item.body)}
              </p>
            </Card>
          ))}
        </div>
      </section>
      <section className="border-y border-border bg-white/[.018]">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-20 lg:grid-cols-2">
          <div>
            <SectionHead title={t("section.reviews")} />
            <Card className="mt-8">
              <EmptyState icon={MessageSquare} title="No verified reviews yet" description="Customer feedback will appear after completed purchases." />
            </Card>
          </div>
          <div>
            <SectionHead title={t("section.faq")} />
            <Accordion.Root
              type="single"
              collapsible
              className="mt-8 space-y-2"
            >
              {[
                [
                  "How does delivery work?",
                  "After payment verification, RavenStore queues automatic delivery to your account and Telegram notifications.",
                ],
                [
                  "Which payment methods are supported?",
                  "USDT TRC20, USDT BEP20 and Binance payment requests.",
                ],
                [
                  "Where can I get help?",
                  "Create a support ticket from Telegram or the customer portal and follow every reply.",
                ],
                [
                  "Does the website store products?",
                  "No. The FastAPI backend owns all catalog, order, payment and fulfillment data.",
                ],
              ].map(([question, answer], index) => (
                <Accordion.Item
                  key={question}
                  value={`faq-${index}`}
                  className="glass rounded-lg"
                >
                  <Accordion.Header>
                    <Accordion.Trigger className="flex w-full items-center justify-between gap-4 p-4 text-start text-sm font-medium">
                      {question}
                      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    </Accordion.Trigger>
                  </Accordion.Header>
                  <Accordion.Content className="px-4 pb-4 text-sm leading-6 text-muted-foreground">
                    {answer}
                  </Accordion.Content>
                </Accordion.Item>
              ))}
            </Accordion.Root>
          </div>
        </div>
      </section>
    </div>
  );
}

function SectionHead({
  title,
  body,
  action,
}: {
  title: string;
  body?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          {title}
        </h2>
        {body ? (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {body}
          </p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
