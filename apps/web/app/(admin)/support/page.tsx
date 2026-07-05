import { LifeBuoy } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function SupportPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Support" eyebrow="Tickets, conversation history and admin replies" actions={[{ label: "Queues", value: 3, icon: LifeBuoy }]} />
      <Card>
        <CardHeader>
          <CardTitle>Support inbox</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          {["Open", "Waiting customer", "Resolved"].map((status) => (
            <div key={status} className="rounded-lg border border-border bg-white/[0.035] p-4">
              <Badge variant={status === "Open" ? "warning" : "default"}>{status}</Badge>
              <div className="mt-4 text-sm text-muted-foreground">Ticket stream appears here when the API returns support threads.</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
