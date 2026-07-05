import { Bell, Send } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function NotificationsPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Notifications" eyebrow="Telegram, email and in-app notification campaigns" actions={[{ label: "Channels", value: 3, icon: Bell }]} />
      <Card>
        <CardHeader>
          <CardTitle>Broadcast composer</CardTitle>
          <Button>
            <Send className="h-4 w-4" />
            Queue notification
          </Button>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2">
          <Input placeholder="Title translation key" />
          <Input placeholder="Audience filter" />
          <Textarea className="md:col-span-2" placeholder="Body translation key or campaign note" />
        </CardContent>
      </Card>
    </div>
  );
}
