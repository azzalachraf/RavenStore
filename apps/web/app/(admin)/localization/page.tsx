"use client";

import { Languages } from "lucide-react";
import { LocalizationEditor } from "@/components/settings/settings-panels";
import { PageHeading } from "@/components/page/page-heading";
import { Button } from "@/components/ui/button";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";

export default function LocalizationPage() {
  const english = useLiveResource(() => ravenApi.translations("en"), 30000);
  const arabic = useLiveResource(() => ravenApi.translations("ar"), 30000);
  return (
    <div className="space-y-6">
      <PageHeading title="Localization" eyebrow="Edit English and Arabic translations from the API" actions={[{ label: "Languages", value: 2, icon: Languages }]} />
      <div className="flex gap-2">
        <Button variant="outline">English</Button>
        <Button variant="outline">Arabic</Button>
        <Button>Add language</Button>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <LocalizationEditor translations={english.data ?? {}} />
        <LocalizationEditor translations={arabic.data ?? {}} />
      </div>
    </div>
  );
}
