"use client";

import { Activity } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { ActivityLog } from "@/lib/types";

export default function AuditPage() {
  const logs = useLiveResource(() => ravenApi.activity(), 10000);
  return (
    <div className="space-y-6">
      <PageHeading title="Audit Logs" eyebrow="Immutable admin activity and operational history" actions={[{ label: "Events", value: logs.data?.length ?? 0, icon: Activity }]} />
      <Card>
        <CardHeader>
          <CardTitle>Activity trail</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable<ActivityLog>
            rows={logs.data ?? []}
            loading={logs.loading}
            empty="No audit events returned by the API."
            columns={[
              { key: "action", header: "Action", sortable: true, value: (row) => row.action, render: (row) => row.action },
              { key: "resource", header: "Resource", value: (row) => row.resource_type, render: (row) => row.resource_type },
              { key: "id", header: "Resource ID", value: (row) => row.resource_id ?? "", render: (row) => row.resource_id?.slice(0, 12) ?? "System" },
              { key: "time", header: "Time", value: (row) => row.created_at ?? "", render: (row) => row.created_at ? new Date(row.created_at).toLocaleString() : "Live" }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
