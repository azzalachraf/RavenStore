"use client";

import * as React from "react";
import { Plus, Sparkles } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading, StatusBadge } from "@/components/page/page-heading";
import { ProductEditor } from "@/components/product/product-editor";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { Product } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

export default function ProductsPage() {
  const products = useLiveResource(() => ravenApi.products(), 7000);
  const categories = useLiveResource(() => ravenApi.categories(), 20000);
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [selected, setSelected] = React.useState<Product | null>(null);

  return (
    <div className="space-y-6">
      <PageHeading title="Products" eyebrow="API-owned catalog management" actions={[{ label: "Products", value: products.data?.length ?? 0, icon: Sparkles }]} />
      <Card>
        <CardHeader>
          <CardTitle>Catalog</CardTitle>
          <Button
            onClick={() => {
              setSelected(null);
              setEditorOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            New product
          </Button>
        </CardHeader>
        <CardContent>
          <DataTable<Product>
            rows={products.data ?? []}
            loading={products.loading}
            empty="No products returned by the API."
            columns={[
              {
                key: "product",
                header: "Product",
                sortable: true,
                value: (row) => row.name_key,
                render: (row) => (
                  <button
                    className="text-left font-medium hover:text-violet-200"
                    onClick={() => {
                      setSelected(row);
                      setEditorOpen(true);
                    }}
                  >
                    {row.name_key}
                    <div className="text-xs text-muted-foreground">{row.slug}</div>
                  </button>
                )
              },
              { key: "status", header: "Visibility", sortable: true, value: (row) => row.status, render: (row) => <StatusBadge status={row.status} /> },
              {
                key: "price",
                header: "Price",
                value: (row) => row.variants[0]?.price_amount ?? "",
                render: (row) => row.variants[0] ? formatCurrency(row.variants[0].price_amount, row.variants[0].currency) : <Badge>Not priced</Badge>
              },
              { key: "delivery", header: "Delivery", value: (row) => row.variants[0]?.delivery_type ?? "", render: (row) => row.variants[0]?.delivery_type ?? "Not configured" }
            ]}
          />
        </CardContent>
      </Card>
      <ProductEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        product={selected}
        categories={categories.data ?? []}
        onSaved={() => void products.refresh()}
      />
    </div>
  );
}
