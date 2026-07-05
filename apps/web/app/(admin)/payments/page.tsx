"use client";

import { CreditCard } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { PaymentSettingsPanel } from "@/components/settings/settings-panels";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { Payment } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export default function PaymentsPage() {
  const payments = useLiveResource(() => ravenApi.payments(), 7000);
  return (
    <div className="space-y-6">
      <PageHeading title="Payments" eyebrow="USDT TRC20, USDT BEP20 and Binance requests" actions={[{ label: "Payments", value: payments.data?.length ?? 0, icon: CreditCard }]} />
      <PaymentSettingsPanel />
      <Card>
        <CardHeader>
          <CardTitle>Verification queue</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable<Payment>
            rows={payments.data ?? []}
            loading={payments.loading}
            empty="No payments returned by the API."
            columns={[
              { key: "provider", header: "Provider", sortable: true, value: (row) => row.provider, render: (row) => row.provider },
              { key: "network", header: "Network", value: (row) => row.network, render: (row) => row.network },
              { key: "status", header: "Status", value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              { key: "amount", header: "Amount", value: (row) => row.amount, render: (row) => formatCurrency(row.amount, row.currency === "USDT" ? "USD" : row.currency) }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
