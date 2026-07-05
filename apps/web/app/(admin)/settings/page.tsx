import { Settings } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Settings" eyebrow="Global marketplace configuration" actions={[{ label: "Sections", value: 6, icon: Settings }]} />
      <Card>
        <CardHeader>
          <CardTitle>Marketplace settings</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Input placeholder="Store name" defaultValue="RavenStore" />
          <Input placeholder="Default currency" defaultValue="USD" />
          <Input placeholder="Default locale" defaultValue="en" />
          <Input placeholder="Support SLA" defaultValue="24h" />
        </CardContent>
      </Card>
    </div>
  );
}
