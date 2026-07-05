import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots { const site = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3001"; return { rules: { userAgent: "*", allow: "/", disallow: ["/account", "/checkout"] }, sitemap: `${site}/sitemap.xml` }; }
