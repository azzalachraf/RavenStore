"use client";

import { AlertTriangle, Ban, Bug, RadioTower, ShieldAlert } from "lucide-react";
import { DataTable, type Column } from "@/components/data/data-table";
import { PageHeading } from "@/components/page/page-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLiveResource } from "@/lib/hooks";
import { ravenApi } from "@/lib/api";
import type { SecurityOverview } from "@/lib/types";

type SecurityEvent = SecurityOverview["recent_events"][number];

const columns: Column<SecurityEvent>[] = [
  { key: "event", header: "Event", sortable: true, value: (row) => row.event_type, render: (row) => <span className="font-medium text-foreground">{row.event_type}</span> },
  { key: "severity", header: "Severity", sortable: true, value: (row) => row.severity, render: (row) => <Badge variant={row.severity === "critical" || row.severity === "high" ? "danger" : row.severity === "warning" ? "warning" : "default"}>{row.severity}</Badge> },
  { key: "outcome", header: "Outcome", sortable: true, value: (row) => row.outcome, render: (row) => row.outcome },
  { key: "trace", header: "Trace", value: (row) => row.trace_id ?? "", render: (row) => <code className="text-xs text-muted-foreground">{row.trace_id?.slice(0, 16) ?? "-"}</code> },
  { key: "time", header: "Time", sortable: true, value: (row) => row.created_at, render: (row) => new Date(row.created_at).toLocaleString() }
];

export default function SecurityPage() {
  const security = useLiveResource(() => ravenApi.securityOverview(), 15000, ["security"]);
  const data = security.data;
  const signals = [
    { label: "Failed logins", value: data?.failed_logins ?? 0, icon: Ban, danger: Boolean(data?.failed_logins) },
    { label: "Suspicious activity", value: data?.suspicious_events ?? 0, icon: ShieldAlert, danger: Boolean(data?.suspicious_events) },
    { label: "Webhook failures", value: data?.webhook_failures ?? 0, icon: RadioTower, danger: Boolean(data?.webhook_failures) },
    { label: "Payment anomalies", value: data?.payment_anomalies ?? 0, icon: AlertTriangle, danger: Boolean(data?.payment_anomalies) },
    { label: "System errors", value: data?.system_errors ?? 0, icon: Bug, danger: Boolean(data?.system_errors) }
  ];
  return (
    <div className="space-y-6">
      <PageHeading title="Security Operations" eyebrow="Authentication, fraud, webhook and service signals" actions={[{ label: "Hours", value: data?.window_hours ?? 24, icon: ShieldAlert }]} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {signals.map(({ label, value, icon: Icon, danger }) => (
          <Card key={label}>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-sm">{label}</CardTitle>
              <Icon className={danger ? "h-4 w-4 text-red-300" : "h-4 w-4 text-emerald-300"} />
            </CardHeader>
            <CardContent className="flex items-end justify-between">
              <span className="text-2xl font-semibold text-foreground">{value}</span>
              <Badge variant={danger ? "danger" : "success"}>{danger ? "Review" : "Clear"}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Card>
          <CardHeader><CardTitle>Worker Heartbeats</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(data?.workers ?? {}).map(([worker, state]) => (
              <div key={worker} className="flex items-center justify-between border-b border-border pb-3 last:border-0 last:pb-0">
                <span className="capitalize text-sm text-foreground">{worker}</span>
                <Badge variant={state === "healthy" || state === "development" ? "success" : "danger"}>{state}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>API Traffic</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {Object.entries(data?.api_metrics ?? {}).map(([metric, value]) => (
              <div key={metric} className="border-b border-border pb-3">
                <div className="text-xs text-muted-foreground">{metric.replaceAll("_", " ")}</div>
                <div className="mt-1 text-lg font-semibold text-foreground">{Number(value).toLocaleString()}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader><CardTitle>Recent Security Events</CardTitle></CardHeader>
        <CardContent><DataTable rows={data?.recent_events ?? []} columns={columns} loading={security.loading} empty="No security events in this window" pageSize={10} /></CardContent>
      </Card>
    </div>
  );
}
