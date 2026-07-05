"use client";

import { motion } from "framer-motion";
import { CheckCircle2, UploadCloud } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function PaymentSettingsPanel() {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {["USDT TRC20", "USDT BEP20", "Binance Pay"].map((method) => (
        <Card key={method} className="p-4">
          <div className="flex items-center justify-between">
            <CardTitle>{method}</CardTitle>
            <Badge variant="success">Enabled</Badge>
          </div>
          <div className="mt-4 space-y-3">
            <Input placeholder={`${method} address or merchant key`} />
            <Input placeholder="Minimum confirmations" />
            <Button className="w-full">Save configuration</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function DeliveryUploadPanel() {
  const deliveryTypes = ["Accounts", "Invite links", "License keys", "ZIP files", "PDFs", "Credentials"];
  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Card>
        <CardHeader>
          <CardTitle>Delivery vault</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {deliveryTypes.map((type) => (
            <motion.div key={type} whileHover={{ x: 3 }} className="flex items-center justify-between rounded-md border border-border bg-white/[0.035] px-3 py-2">
              <span>{type}</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-300" />
            </motion.div>
          ))}
        </CardContent>
      </Card>
      <Card className="flex min-h-80 items-center justify-center border-dashed p-6 text-center text-muted-foreground">
        <div>
          <UploadCloud className="mx-auto mb-3 h-10 w-10 text-violet-200" />
          <div className="font-medium text-foreground">Drop fulfillment inventory</div>
          <div className="mt-1 text-sm">Credentials, keys, PDFs and ZIP files are sent to the API for encrypted storage.</div>
        </div>
      </Card>
    </div>
  );
}

export function LocalizationEditor({ translations }: { translations: Record<string, string> }) {
  const entries = Object.entries(translations);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Translation keys</CardTitle>
        <Button>Save translations</Button>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        {(entries.length ? entries : [["home.title", ""], ["checkout.title", ""], ["support.title", ""]]).map(([key, value]) => (
          <div key={key} className="space-y-1">
            <div className="text-xs text-muted-foreground">{key}</div>
            <Textarea defaultValue={value} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

