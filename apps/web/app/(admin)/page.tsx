 "use client";

import { CreditCard, PackageCheck } from "lucide-react";
import { RevenueChart, PaymentChart } from "@/components/dashboard/charts";
import { WidgetGrid } from "@/components/dashboard/widget-grid";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { ActivityLog, Order } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export default function DashboardPage() {
  const summary = useLiveResource(() => ravenApi.analyticsSummary(), 8000);
  const orders = useLiveResource(() => ravenApi.adminOrders(), 8000);
  const activity = useLiveResource(() => ravenApi.activity(), 12000);
  const pendingOrders = orders.data?.filter((order) => order.status.includes("pending")).length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeading
        title="Dashboard"
        eyebrow="Live RavenStore control plane"
        actions={[
          { label: "Pending orders", value: pendingOrders, icon: PackageCheck },
          { label: "Payments", value: Object.values(summary.data?.payment_statistics ?? {}).reduce((a, b) => a + b, 0), icon: CreditCard }
        ]}
      />
      <WidgetGrid summary={summary.data} pendingOrders={pendingOrders} />
      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <RevenueChart />
        <PaymentChart stats={summary.data?.payment_statistics ?? {}} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Orders</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable<Order>
              rows={orders.data ?? []}
              loading={orders.loading}
              empty="No orders returned by the API."
              columns={[
                { key: "order", header: "Order", sortable: true, value: (row) => row.order_number, render: (row) => row.order_number },
                { key: "status", header: "Status", sortable: true, value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
                { key: "total", header: "Total", value: (row) => row.total_amount, render: (row) => formatCurrency(row.total_amount, row.currency) }
              ]}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Activity History</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable<ActivityLog>
              rows={activity.data ?? []}
              loading={activity.loading}
              empty="No activity has been logged yet."
              columns={[
                { key: "action", header: "Action", sortable: true, value: (row) => row.action, render: (row) => row.action },
                { key: "resource", header: "Resource", value: (row) => row.resource_type, render: (row) => row.resource_type },
                { key: "time", header: "Time", value: (row) => row.created_at ?? "", render: (row) => row.created_at ? new Date(row.created_at).toLocaleString() : "Live" }
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

