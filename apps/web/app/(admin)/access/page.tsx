import { Shield } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AccessPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Access" eyebrow="Admin users, roles, permissions and MFA readiness" actions={[{ label: "Roles", value: 5, icon: Shield }]} />
      <Card>
        <CardHeader>
          <CardTitle>RBAC matrix</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-5">
          {["Owner", "Admin", "Moderator", "Support", "Customer"].map((role) => (
            <div key={role} className="rounded-lg border border-border bg-white/[0.035] p-4">
              <Badge variant={role === "Owner" ? "violet" : "default"}>{role}</Badge>
              <div className="mt-3 text-xs text-muted-foreground">Permissions sync through the API role model.</div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
