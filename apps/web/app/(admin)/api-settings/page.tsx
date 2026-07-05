import { KeyRound } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ApiSettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="API Settings" eyebrow="Service keys, webhook logs, rate limits and client contracts" actions={[{ label: "Scopes", value: 8, icon: KeyRound }]} />
      <Card>
        <CardHeader>
          <CardTitle>API key controls</CardTitle>
          <Button>Rotate key</Button>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Input placeholder="Key name" />
          <Input placeholder="Scopes" />
          <Input placeholder="Rate limit" />
          <Input placeholder="Expiration" />
        </CardContent>
      </Card>
    </div>
  );
}
