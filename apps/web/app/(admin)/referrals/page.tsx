import { TicketPercent } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ReferralsPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Referrals" eyebrow="Invited users, rewards and conversion loops" actions={[{ label: "Programs", value: 1, icon: TicketPercent }]} />
      <Card>
        <CardHeader>
          <CardTitle>Referral performance</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Referral records will appear when the API returns referral statistics.</CardContent>
      </Card>
    </div>
  );
}
