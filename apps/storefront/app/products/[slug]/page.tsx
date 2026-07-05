import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { ProductDetailClient } from "@/components/product-detail-client";

export const revalidate = 15;

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const product = await api.product(slug, 15).catch(() => null);
  if (!product) return { title: "Product" };
  return { title: product.name_key, description: product.description_key ?? `Buy ${product.name_key} from RavenStore.`, openGraph: { images: product.images?.[0]?.url ? [product.images[0].url] : ["/images/ravenstore-hero.png"] } };
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await api.product(slug, 15).catch(() => null);
  if (!product) notFound();
  const recommendations = await api.products(`limit=8&offset=0&category_id=${product.category_id}`, 15).catch(() => []);
  const variant = product.variants.find((item) => item.is_active) ?? product.variants[0];
  const jsonLd = { "@context": "https://schema.org", "@type": "Product", name: product.name_key, description: product.description_key, image: product.images.map((image) => image.url), offers: variant ? { "@type": "Offer", price: variant.price_amount, priceCurrency: variant.currency, availability: "https://schema.org/InStock" } : undefined };
  return <><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /><ProductDetailClient initialProduct={product} recommendations={recommendations.filter((item) => item.id !== product.id)} /></>;
}
