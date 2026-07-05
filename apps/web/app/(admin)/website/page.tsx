import { Globe2 } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function WebsitePage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Website Preview" eyebrow="Browser client preview consuming the same API catalog" actions={[{ label: "Surfaces", value: 2, icon: Globe2 }]} />
      <Card>
        <CardHeader>
          <CardTitle>Live website preview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border bg-white/[0.035] p-6">
            <div className="text-2xl font-semibold">RavenStore</div>
            <div className="mt-2 text-sm text-muted-foreground">The browser storefront reads the same API state as Telegram.</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
