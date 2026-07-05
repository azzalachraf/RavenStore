import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { PageTransition } from "@/components/page-transition";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3001";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "RavenStore | Premium Digital Subscriptions", template: "%s | RavenStore" },
  description: "Premium AI, design, VPN, streaming and developer subscriptions delivered through RavenStore and Telegram.",
  keywords: ["digital subscriptions", "AI tools", "Telegram store", "VPN", "developer tools", "streaming"],
  openGraph: {
    title: "RavenStore",
    description: "Premium digital subscriptions, built around Telegram.",
    type: "website",
    url: siteUrl,
    images: [{ url: "/images/ravenstore-hero.png", width: 1692, height: 961, alt: "RavenStore Telegram-first digital marketplace" }]
  },
  twitter: { card: "summary_large_image", title: "RavenStore", description: "Premium digital subscriptions, delivered fast.", images: ["/images/ravenstore-hero.png"] }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en" className="dark"><body><Providers><SiteHeader /><main><PageTransition>{children}</PageTransition></main><SiteFooter /></Providers></body></html>;
}
