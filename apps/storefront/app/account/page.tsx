import type { Metadata } from "next";
import { AccountClient } from "@/components/account-client";

export const metadata: Metadata = { title: "Customer Portal", robots: { index: false, follow: false } };

export default async function AccountPage({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  const { tab } = await searchParams;
  return <AccountClient initialTab={tab ?? "profile"} />;
}
