"use client";

import { HeartPulse } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";

export default function HealthPage() {
  const health = useLiveResource(() => ravenApi.eventHealth(), 30000, ["health"]);
  const data = health.data;
  const systems = [
    { name: "Redis event transport", value: data?.redis ?? (health.loading ? "checking" : "unavailable"), healthy: data?.redis === "healthy" },
    { name: "Outbox backlog", value: String(data?.outbox_pending ?? 0), healthy: (data?.outbox_pending ?? 0) < 100 },
    { name: "Dead-letter queue", value: String(data?.dead_letters ?? 0), healthy: (data?.dead_letters ?? 0) === 0 },
    { name: "Failed deliveries", value: String(data?.failed_deliveries ?? 0), healthy: (data?.failed_deliveries ?? 0) === 0 },
    { name: "Consumer heartbeats", value: `${data?.stale_consumers ?? 0} stale`, healthy: (data?.stale_consumers ?? 0) === 0 },
    { name: "Published events", value: String(data?.transport_metrics?.events?.published_total ?? 0), healthy: Boolean(data) },
  ];
  return (
    <div className="space-y-6">
      <PageHeading title="System Health" eyebrow="Event delivery, cache, workers and consumer telemetry" actions={[{ label: "Signals", value: systems.length, icon: HeartPulse }]} />
      <div className="grid gap-4 md:grid-cols-3">
        {systems.map((service) => (
          <Card key={service.name}>
            <CardHeader>
              <CardTitle>{service.name}</CardTitle>
              <Badge variant={service.healthy ? "success" : "warning"}>{service.healthy ? "Healthy" : "Attention"}</Badge>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{service.value}</CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
