"use client";

import { ReceiptText } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { Order } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export default function OrdersPage() {
  const orders = useLiveResource(() => ravenApi.adminOrders(), 7000);
  return (
    <div className="space-y-6">
      <PageHeading title="Orders" eyebrow="Search, verification, fulfillment and delivery logs" actions={[{ label: "Orders", value: orders.data?.length ?? 0, icon: ReceiptText }]} />
      <Card>
        <CardHeader>
          <CardTitle>Order queue</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable<Order>
            rows={orders.data ?? []}
            loading={orders.loading}
            empty="No orders returned by the API."
            columns={[
              { key: "order", header: "Order", sortable: true, value: (row) => row.order_number, render: (row) => row.order_number },
              { key: "customer", header: "Customer", value: (row) => row.user_id, render: (row) => row.user_id.slice(0, 8) },
              { key: "status", header: "Status", sortable: true, value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              { key: "total", header: "Total", value: (row) => row.total_amount, render: (row) => formatCurrency(row.total_amount, row.currency) }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
