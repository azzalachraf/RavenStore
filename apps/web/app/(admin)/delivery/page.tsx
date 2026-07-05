import { Truck } from "lucide-react";
import { PageHeading } from "@/components/page/page-heading";
import { DeliveryUploadPanel } from "@/components/settings/settings-panels";

export default function DeliveryPage() {
  return (
    <div className="space-y-6">
      <PageHeading title="Delivery" eyebrow="Automatic fulfillment inventory and encrypted delivery assets" actions={[{ label: "Strategies", value: 6, icon: Truck }]} />
      <DeliveryUploadPanel />
    </div>
  );
}
