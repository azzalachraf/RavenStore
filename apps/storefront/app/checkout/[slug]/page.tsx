import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { CheckoutClient } from "@/components/checkout-client";

export const metadata: Metadata = { title: "Secure Checkout", robots: { index: false, follow: false } };

export default async function CheckoutPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await api.product(slug, 0).catch(() => null);
  if (!product) notFound();
  return <CheckoutClient product={product} />;
}
