"use client";

import { motion, Reorder } from "framer-motion";
import { BarChart3, CreditCard, DollarSign, PackageCheck, Percent, ReceiptText, Send, Users } from "lucide-react";
import * as React from "react";
import { MetricCard } from "@/components/dashboard/metric-card";
import type { AnalyticsSummary } from "@/lib/types";
import { compactNumber, formatCurrency, percentage } from "@/lib/utils";

const defaultOrder = ["revenue", "profit", "orders", "telegram", "website", "conversion", "payments", "pending"];

export function WidgetGrid({ summary, pendingOrders = 0 }: { summary: AnalyticsSummary | null; pendingOrders?: number }) {
  const [order, setOrder] = React.useState(defaultOrder);
  const metrics = {
    revenue: <MetricCard label="Live revenue" value={Number(summary?.revenue ?? 0)} formatter={(v) => formatCurrency(v)} icon={DollarSign} delta="Live API" />,
    profit: <MetricCard label="Profit" value={Number(summary?.profit ?? 0)} formatter={(v) => formatCurrency(v)} icon={BarChart3} tone="cyan" />,
    orders: <MetricCard label="Orders" value={Number(summary?.orders ?? 0)} formatter={compactNumber} icon={ReceiptText} tone="success" />,
    telegram: <MetricCard label="Telegram users" value={Number(summary?.telegram_users ?? 0)} formatter={compactNumber} icon={Send} tone="violet" />,
    website: <MetricCard label="Website users" value={Number(summary?.website_users ?? 0)} formatter={compactNumber} icon={Users} tone="cyan" />,
    conversion: <MetricCard label="Conversion rate" value={Number(summary?.conversion_rate ?? 0)} formatter={percentage} icon={Percent} tone="success" />,
    payments: <MetricCard label="Successful payments" value={Number(summary?.payment_statistics?.confirmed ?? 0)} formatter={compactNumber} icon={CreditCard} tone="success" />,
    pending: <MetricCard label="Pending orders" value={pendingOrders} formatter={compactNumber} icon={PackageCheck} tone="warning" />
  };
  return (
    <Reorder.Group
      axis="y"
      values={order}
      onReorder={setOrder}
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      {order.map((key) => (
        <Reorder.Item key={key} value={key} as="div">
          <motion.div layout>{metrics[key as keyof typeof metrics]}</motion.div>
        </Reorder.Item>
      ))}
    </Reorder.Group>
  );
}

