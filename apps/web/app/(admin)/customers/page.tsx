"use client";

import * as React from "react";
import { Users } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { User } from "@/lib/types";

export default function CustomersPage() {
  const customers = useLiveResource(() => ravenApi.customers(), 12000);
  const [adjustingUser, setAdjustingUser] = React.useState<User | null>(null);
  const [adjustAmount, setAdjustAmount] = React.useState("");
  const [adjustDescription, setAdjustDescription] = React.useState("");
  const [updating, setUpdating] = React.useState(false);

  const adjustBalance = async () => {
    if (!adjustingUser) return;
    setUpdating(true);
    try {
      await ravenApi.adjustWallet(adjustingUser.id, {
        amount: Number(adjustAmount),
        description: adjustDescription || undefined
      });
      setAdjustingUser(null);
      setAdjustAmount("");
      setAdjustDescription("");
      void customers.refresh();
    } catch (err) {
      alert("Failed to adjust wallet balance");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeading title="Customers" eyebrow="Telegram identity, purchases, referrals and support history" actions={[{ label: "Customers", value: customers.data?.length ?? 0, icon: Users }]} />
      <Card>
        <CardHeader>
          <CardTitle>Customer directory</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable<User>
            rows={customers.data ?? []}
            loading={customers.loading}
            empty="No customers returned by the API."
            columns={[
              { key: "email", header: "Email", sortable: true, value: (row) => row.email, render: (row) => row.email },
              { key: "name", header: "Name", value: (row) => row.display_name ?? "", render: (row) => row.display_name ?? "Telegram customer" },
              { key: "language", header: "Language", value: (row) => row.locale, render: (row) => row.locale },
              { key: "wallet_balance", header: "Wallet Balance", value: (row) => row.wallet_balance ?? 0, render: (row) => `$${(row.wallet_balance ?? 0).toFixed(2)}` },
              { key: "status", header: "Status", value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              {
                key: "actions",
                header: "Actions",
                value: () => "",
                render: (row) => (
                  <Button
                    size="sm"
                    className="bg-violet-600 hover:bg-violet-700 text-white"
                    onClick={() => {
                      setAdjustingUser(row);
                      setAdjustAmount("");
                      setAdjustDescription("");
                    }}
                  >
                    Adjust Wallet
                  </Button>
                ),
              },
            ]}
          />
        </CardContent>
      </Card>

      {adjustingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <Card className="w-[450px] p-6 border-white/10 bg-[#0a0d14]/95 text-foreground shadow-panel">
            <h2 className="text-lg font-semibold mb-2">Adjust User Wallet</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Enter a positive value to add money, or a negative value to deduct money from <b>{adjustingUser.email}</b>.
            </p>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Adjustment Amount (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="e.g. 10.00 or -5.00"
                  value={adjustAmount}
                  onChange={(e) => setAdjustAmount(e.target.value)}
                  className="w-full h-10 rounded-md border border-border bg-white/[0.04] px-3 text-sm text-foreground outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Reason/Description</label>
                <input
                  type="text"
                  placeholder="e.g. Compensation, Manual Top-up"
                  value={adjustDescription}
                  onChange={(e) => setAdjustDescription(e.target.value)}
                  className="w-full h-10 rounded-md border border-border bg-white/[0.04] px-3 text-sm text-foreground outline-none focus:border-violet-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <Button variant="secondary" onClick={() => setAdjustingUser(null)}>
                  Cancel
                </Button>
                <Button
                  className="bg-violet-600 hover:bg-violet-700 text-white"
                  onClick={adjustBalance}
                  disabled={updating || !adjustAmount}
                >
                  {updating ? "Saving..." : "Apply Adjustment"}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
