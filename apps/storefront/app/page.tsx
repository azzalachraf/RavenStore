import { api } from "@/lib/api";
import { LandingPage } from "@/components/landing-page";

export const revalidate = 15;

export default async function HomePage() {
  const [products, categories] = await Promise.all([
    api.products("limit=8&offset=0&filter=featured", 15).catch(() => []),
    api.categories(30).catch(() => [])
  ]);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "RavenStore",
    url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3001",
    description: "Premium digital subscription marketplace built around Telegram."
  };
  return <><script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} /><LandingPage initialProducts={products} categories={categories} /></>;
}
