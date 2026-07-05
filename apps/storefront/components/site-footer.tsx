"use client";

import Link from "next/link";
import { Send } from "lucide-react";
import { useI18n } from "@/components/providers";

export function SiteFooter() {
  const { t } = useI18n();
  return <footer className="border-t border-border bg-black/20"><div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 md:grid-cols-[1.3fr_1fr_1fr]"><div><div className="flex items-center gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary font-black">R</span><span className="font-semibold">RavenStore</span></div><p className="mt-4 max-w-sm text-sm leading-6 text-muted-foreground">{t("footer.copy")}</p></div><div><div className="text-sm font-semibold">RavenStore</div><div className="mt-3 grid gap-2 text-sm text-muted-foreground"><Link href="/store">{t("nav.store")}</Link><Link href="/account">{t("nav.account")}</Link><Link href="/account?tab=support">{t("nav.support")}</Link></div></div><div><div className="text-sm font-semibold">Telegram</div><a className="mt-3 inline-flex items-center gap-2 text-sm text-violet-200" href={process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/RavenStoreBot"}><Send className="h-4 w-4" />{t("nav.telegram")}</a></div></div><div className="border-t border-border px-4 py-5 text-center text-xs text-muted-foreground">© {new Date().getFullYear()} RavenStore. {t("footer.rights")}</div></footer>;
}
