"use client";

import { BarChart3, Download } from "lucide-react";
import { PaymentChart, RevenueChart } from "@/components/dashboard/charts";
import { WidgetGrid } from "@/components/dashboard/widget-grid";
import { PageHeading } from "@/components/page/page-heading";
import { Button } from "@/components/ui/button";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";

export default function AnalyticsPage() {
  const summary = useLiveResource(() => ravenApi.analyticsSummary(), 8000);
  return (
    <div className="space-y-6">
      <PageHeading title="Analytics" eyebrow="Revenue, conversion, category and payment intelligence" actions={[{ label: "Reports", value: 4, icon: BarChart3 }]} />
      <div className="flex flex-wrap gap-2">
        <Button variant="outline">Today</Button>
        <Button variant="outline">7 days</Button>
        <Button variant="outline">30 days</Button>
        <Button>
          <Download className="h-4 w-4" />
          Export
        </Button>
      </div>
      <WidgetGrid summary={summary.data} />
      <div className="grid gap-4 xl:grid-cols-2">
        <RevenueChart />
        <PaymentChart stats={summary.data?.payment_statistics ?? {}} />
      </div>
    </div>
  );
}
