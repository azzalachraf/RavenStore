"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDownUp, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { EmptyState } from "@/components/ui/empty-state";

export type Column<T> = {
  key: string;
  header: string;
  sortable?: boolean;
  render: (row: T) => React.ReactNode;
  value?: (row: T) => string | number;
};

export function DataTable<T>({
  rows,
  columns,
  loading,
  empty,
  pageSize = 8
}: {
  rows: T[];
  columns: Column<T>[];
  loading?: boolean;
  empty: string;
  pageSize?: number;
}) {
  const [query, setQuery] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [sortKey, setSortKey] = React.useState<string | null>(null);
  const [direction, setDirection] = React.useState<"asc" | "desc">("asc");
  const [selected, setSelected] = React.useState<Set<number>>(new Set());

  const filtered = React.useMemo(() => {
    const normalized = query.toLowerCase();
    let next = rows.filter((row) =>
      columns.some((column) => String(column.value?.(row) ?? column.render(row)).toLowerCase().includes(normalized))
    );
    if (sortKey) {
      const column = columns.find((item) => item.key === sortKey);
      next = [...next].sort((a, b) => {
        const aValue = String(column?.value?.(a) ?? "");
        const bValue = String(column?.value?.(b) ?? "");
        return direction === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
      });
    }
    return next;
  }, [columns, direction, query, rows, sortKey]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-full" />
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={query} onChange={(event) => setQuery(event.target.value)} className="pl-9" placeholder="Search table..." />
        </div>
        <Button variant="outline" disabled={selected.size === 0}>
          Bulk actions
        </Button>
      </div>
      <div className="overflow-hidden rounded-lg border border-border">
        <Table>
          <THead>
            <TR>
              <TH className="w-10">
                <input
                  aria-label="Select visible rows"
                  type="checkbox"
                  onChange={(event) => {
                    setSelected(event.target.checked ? new Set(visible.map((_, index) => index)) : new Set());
                  }}
                />
              </TH>
              {columns.map((column) => (
                <TH key={column.key}>
                  <button
                    className="inline-flex items-center gap-1"
                    onClick={() => {
                      if (!column.sortable) return;
                      setSortKey(column.key);
                      setDirection((value) => (value === "asc" ? "desc" : "asc"));
                    }}
                  >
                    {column.header}
                    {column.sortable ? <ArrowDownUp className="h-3 w-3" /> : null}
                  </button>
                </TH>
              ))}
            </TR>
          </THead>
          <TBody>
            {visible.length ? (
              <AnimatePresence initial={false}>
              {visible.map((row, index) => (
                <motion.tr key={index} layout initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: .16 }} className="border-b border-border transition-colors hover:bg-white/[0.035]">
                  <TD>
                    <input
                      aria-label="Select row"
                      type="checkbox"
                      checked={selected.has(index)}
                      onChange={(event) => {
                        setSelected((current) => {
                          const next = new Set(current);
                          if (event.target.checked) next.add(index);
                          else next.delete(index);
                          return next;
                        });
                      }}
                    />
                  </TD>
                  {columns.map((column) => (
                    <TD key={column.key}>{column.render(row)}</TD>
                  ))}
                </motion.tr>
              ))}
              </AnimatePresence>
            ) : (
              <TR>
                <TD colSpan={columns.length + 1} className="p-0">
                  <EmptyState title={empty} description="Try adjusting your search or filters." />
                </TD>
              </TR>
            )}
          </TBody>
        </Table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {filtered.length} records · {selected.size} selected
        </span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span>
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="icon"
            disabled={page >= totalPages}
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
