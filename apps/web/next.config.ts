import type { NextConfig } from "next";

const isVercelProduction = process.env.VERCEL_ENV === "production";

function publicEnv(name: string, developmentFallback: string) {
  const value = process.env[name];
  if (isVercelProduction && !value) throw new Error(`Missing required production environment variable: ${name}`);
  return value ?? developmentFallback;
}

const apiOrigin = new URL(publicEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1")).origin;
publicEnv("NEXT_PUBLIC_ADMIN_SITE_URL", "http://localhost:3000");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "Content-Security-Policy", value: `default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; form-action 'self'; img-src 'self' data: https:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' ${apiOrigin} ws: wss:` }
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  outputFileTracingRoot: process.cwd(),
  poweredByHeader: false,
  compress: true,
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  experimental: { optimizePackageImports: ["lucide-react", "framer-motion", "recharts"] },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  }
};

export default nextConfig;
