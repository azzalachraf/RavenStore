"use client";

import * as React from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, CheckCircle2, Copy, Landmark, LockKeyhole, Network, Send, WalletCards } from "lucide-react";
import { api } from "@/lib/api";
import { AuthDialog } from "@/components/auth-dialog";
import { useAuth, useI18n, useToast } from "@/components/providers";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import type { PaymentCreated, Product } from "@/lib/types";
import { money } from "@/lib/utils";

const methods = [
  { value: "binance", key: "checkout.binance", icon: Landmark },
  { value: "usdt_trc20", key: "checkout.trc20", icon: Network },
  { value: "usdt_bep20", key: "checkout.bep20", icon: WalletCards },
] as const;

export function CheckoutClient({ product }: { product: Product }) {
  const { t } = useI18n();
  const { token } = useAuth();
  const { success } = useToast();
  const [authOpen, setAuthOpen] = React.useState(false);
  const [method, setMethod] = React.useState("binance");
  const [payment, setPayment] = React.useState<PaymentCreated | null>(null);
  const [paymentId, setPaymentId] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [queued, setQueued] = React.useState(false);
  const variant = product.variants.find((item) => item.is_active) ?? product.variants[0];
  const progress = !payment ? 33 : queued ? 100 : 66;

  const create = async () => {
    if (!token) { setAuthOpen(true); return; }
    if (!variant) return;
    setLoading(true);
    try {
      const order = await api.createOrder(token, variant.id);
      setPayment(await api.createPayment(token, order.id, method));
      success(t("checkout.review"));
    } finally { setLoading(false); }
  };
  const verify = async () => {
    if (!payment || !paymentId) return;
    setLoading(true);
    try {
      await api.verifyPayment(payment.payment_token, paymentId);
      setQueued(true);
      success(t("checkout.queued"));
    } finally { setLoading(false); }
  };

  return (
    <div className="mx-auto min-h-screen max-w-5xl px-4 pb-20 pt-28">
      <Link href={`/products/${product.slug}`} className="inline-flex items-center gap-2 text-sm text-muted-foreground transition hover:text-foreground"><ArrowLeft className="h-4 w-4" />{t("common.back")}</Link>
      <div className="mt-6 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
        <Card className="h-fit p-5">
          <Badge tone="violet">{t("checkout.review")}</Badge>
          <h1 className="mt-4 text-2xl font-semibold">{t(product.name_key)}</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{product.description_key ? t(product.description_key) : ""}</p>
          <div className="mt-6 text-2xl font-semibold">{variant ? money(variant.price_amount, variant.currency) : "—"}</div>
          <div className="mt-6 flex items-center gap-2 border-t border-border pt-4 text-xs text-emerald-300"><LockKeyhole className="h-4 w-4" />Encrypted reference · automatic fulfillment</div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-semibold">{payment ? t("checkout.verify") : t("checkout.method")}</h2><span className="text-xs text-muted-foreground">{Math.round(progress)}%</span></div>
          <div className="mt-4"><Progress value={progress} /></div>
          <AnimatePresence mode="wait">
            {!payment ? (
              <motion.div key="methods" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="mt-5 space-y-4">
                <div className="grid gap-2 sm:grid-cols-3">
                  {methods.map(({ value, key, icon: Icon }) => <button key={value} onClick={() => setMethod(value)} className={`rounded-md border p-3 text-left text-sm transition duration-200 ${method === value ? "border-violet-400/70 bg-violet-400/10 text-violet-100 shadow-glow" : "border-border bg-white/[.025] text-muted-foreground hover:border-white/20 hover:bg-white/[.05]"}`}><Icon className="mb-3 h-4 w-4" />{t(key)}</button>)}
                </div>
                <Button className="w-full" onClick={() => void create()} disabled={!variant || loading}>{loading ? t("common.loading") : t("checkout.create")}</Button>
              </motion.div>
            ) : queued ? (
              <motion.div key="queued" initial={{ opacity: 0, y: 10, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} className="mt-7 text-center">
                <motion.div initial={{ scale: .7 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 18 }} className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-emerald-400/20 bg-emerald-400/10"><CheckCircle2 className="h-7 w-7 text-emerald-300" /></motion.div>
                <p className="mx-auto mt-4 max-w-sm text-sm leading-6 text-muted-foreground">{t("checkout.queued")}</p>
                <Link href="/account?tab=orders" className="mt-5 block"><Button className="w-full">{t("account.orders")}</Button></Link>
              </motion.div>
            ) : (
              <motion.div key="payment" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-5 space-y-4">
                <div className="rounded-lg border border-border bg-white/[.025] p-4">
                  <div className="text-sm font-medium">{t("checkout.instructions", { amount: payment.payment.amount, currency: payment.payment.currency })}</div>
                  {payment.payment.payment_address ? <div className="mt-3 flex items-center gap-2 rounded-md border border-white/[.05] bg-black/25 p-3 font-mono text-xs"><span className="min-w-0 flex-1 break-all">{payment.payment.payment_address}</span><button className="rounded p-1 text-muted-foreground transition hover:bg-white/[.07] hover:text-foreground" aria-label="Copy address" onClick={() => void navigator.clipboard.writeText(payment.payment.payment_address ?? "")}><Copy className="h-4 w-4" /></button></div> : null}
                </div>
                <Input value={paymentId} onChange={(event) => setPaymentId(event.target.value)} placeholder={t("checkout.paymentId")} />
                <Button className="w-full" onClick={() => void verify()} disabled={!paymentId || loading}><Send className="h-4 w-4" />{loading ? t("common.loading") : t("checkout.submit")}</Button>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      </div>
      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} />
    </div>
  );
}
