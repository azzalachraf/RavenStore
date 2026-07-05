"use client";

import { Boxes, Plus } from "lucide-react";
import { DataTable } from "@/components/data/data-table";
import { PageHeading } from "@/components/page/page-heading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ravenApi } from "@/lib/api";
import { useLiveResource } from "@/lib/hooks";
import type { Category } from "@/lib/types";

export default function CategoriesPage() {
  const categories = useLiveResource(() => ravenApi.categories(), 15000);
  return (
    <div className="space-y-6">
      <PageHeading title="Categories" eyebrow="Ordering, visibility and multilingual catalog groups" actions={[{ label: "Categories", value: categories.data?.length ?? 0, icon: Boxes }]} />
      <Card>
        <CardHeader>
          <CardTitle>Category management</CardTitle>
          <Button>
            <Plus className="h-4 w-4" />
            New category
          </Button>
        </CardHeader>
        <CardContent>
          <DataTable<Category>
            rows={categories.data ?? []}
            loading={categories.loading}
            empty="No categories returned by the API."
            columns={[
              { key: "name", header: "Name key", sortable: true, value: (row) => row.name_key, render: (row) => row.name_key },
              { key: "slug", header: "Slug", sortable: true, value: (row) => row.slug, render: (row) => row.slug },
              { key: "order", header: "Order", sortable: true, value: (row) => row.sort_order, render: (row) => row.sort_order },
              { key: "visible", header: "Visibility", value: (row) => String(row.is_active), render: (row) => <Badge variant={row.is_active ? "success" : "default"}>{row.is_active ? "Visible" : "Hidden"}</Badge> }
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
