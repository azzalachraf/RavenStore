"use client";

import { Users } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { User } from "@/lib/types";

export default function CustomersPage() {
  const customers = useLiveResource(() => ravenApi.customers(), 12000);
  return (
    <div className="space-y-6">
      <PageHeading title="Customers" eyebrow="Telegram identity, purchases, referrals and support history" actions={[{ label: "Customers", value: customers.data?.length ?? 0, icon: Users }]} />
      <Card>
        <CardHeader>
          <CardTitle>Customer directory</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable<User>
            rows={customers.data ?? []}
            loading={customers.loading}
            empty="No customers returned by the API."
            columns={[
              { key: "email", header: "Email", sortable: true, value: (row) => row.email, render: (row) => row.email },
              { key: "name", header: "Name", value: (row) => row.display_name ?? "", render: (row) => row.display_name ?? "Telegram customer" },
              { key: "language", header: "Language", value: (row) => row.locale, render: (row) => row.locale },
              { key: "status", header: "Status", value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
