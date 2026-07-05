import { ProductCard } from "@/components/product-card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Product } from "@/lib/types";

export function ProductGrid({ products, loading = false }: { products: Product[]; loading?: boolean }) {
  if (loading) return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <div key={index} className="space-y-3"><Skeleton className="aspect-[4/3] w-full" /><Skeleton className="h-5 w-2/3" /><Skeleton className="h-4 w-1/3" /></div>)}</div>;
  return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{products.map((product) => <ProductCard key={product.id} product={product} />)}</div>;
}
