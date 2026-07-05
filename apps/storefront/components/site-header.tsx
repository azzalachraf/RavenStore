"use client";

import * as React from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  Feather,
  Languages,
  Menu,
  Search,
  Send,
  UserRound,
  X,
} from "lucide-react";
import { AuthDialog } from "@/components/auth-dialog";
import { useAuth, useI18n } from "@/components/providers";
import { Button } from "@/components/ui/button";
import { usePathname } from "next/navigation";

const telegramUrl =
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/RavenStoreBot";

export function SiteHeader() {
  const { t, locale, setLocale } = useI18n();
  const { user } = useAuth();
  const [authOpen, setAuthOpen] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const pathname = usePathname();
  const links = [
    ["/", "nav.home"],
    ["/store", "nav.store"],
    ["/account?tab=orders", "nav.orders"],
    ["/account?tab=support", "nav.support"],
  ] as const;
  return (
    <>
      <header dir="ltr" className="fixed inset-x-0 top-0 z-40 px-3 pt-3">
        <div className="glass mx-auto flex h-16 max-w-7xl items-center gap-2 rounded-lg px-3 md:gap-3 md:px-4">
          <Link href="/" className="me-auto flex shrink-0 items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-md border border-violet-300/20 bg-primary text-primary-foreground shadow-glow">
              <Feather className="h-4 w-4" />
            </span>
            <span className="hidden text-sm font-semibold sm:block">
              RavenStore
            </span>
          </Link>
          <nav className="mx-auto hidden items-center gap-1 lg:flex">
            {links.map(([href, key]) => (
              <Link
                key={href}
                href={href}
                className={`rounded-md px-3 py-2 text-sm transition ${pathname === href ? "bg-violet-400/[.1] text-violet-100" : "text-muted-foreground hover:bg-white/[.06] hover:text-foreground"}`}
              >
                {t(key)}
              </Link>
            ))}
          </nav>
          <Link
            href="/store"
            aria-label={t("nav.search")}
            className="hidden h-10 min-w-0 flex-1 items-center gap-2 rounded-md border border-border bg-white/[.04] px-3 text-sm text-muted-foreground transition hover:bg-white/[.07] md:flex lg:max-w-[270px]"
          >
            <Search className="h-4 w-4" />
            <span className="truncate">{t("nav.search")}</span>
          </Link>
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={t("nav.language")}
              >
                <Languages className="h-4 w-4" />
              </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="end"
                className="glass z-50 min-w-40 rounded-lg p-1"
              >
                <DropdownMenu.Item
                  onSelect={() => setLocale("en")}
                  className="cursor-pointer rounded-md px-3 py-2 text-sm outline-none focus:bg-white/[.07]"
                >
                  🇬🇧 English {locale === "en" ? "✓" : ""}
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  onSelect={() => setLocale("ar")}
                  className="cursor-pointer rounded-md px-3 py-2 text-sm outline-none focus:bg-white/[.07]"
                >
                  🇩🇿 العربية {locale === "ar" ? "✓" : ""}
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
          <Link
            href="/account?tab=notifications"
            aria-label={t("account.notifications")}
            className="hidden h-10 w-10 items-center justify-center rounded-md text-muted-foreground transition hover:bg-white/[.06] hover:text-foreground sm:flex"
          >
            <Bell className="h-4 w-4" />
          </Link>
          {user ? (
            <Link
              href="/account"
              aria-label={t("nav.account")}
              className="flex h-10 w-10 items-center justify-center rounded-md border border-border bg-white/[.05] text-foreground transition hover:bg-white/[.09]"
            >
              <UserRound className="h-4 w-4" />
            </Link>
          ) : (
            <Button
              variant="secondary"
              size="icon"
              aria-label={t("nav.account")}
              onClick={() => setAuthOpen(true)}
            >
              <UserRound className="h-4 w-4" />
            </Button>
          )}
          <a
            href={telegramUrl}
            target="_blank"
            rel="noreferrer"
            className="hidden md:block"
          >
            <Button>
              <Send className="h-4 w-4" />
              {t("nav.telegram")}
            </Button>
          </a>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Menu"
            onClick={() => setMobileOpen((value) => !value)}
          >
            {mobileOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </Button>
        </div>
        <AnimatePresence>
          {mobileOpen ? (
            <motion.nav
              dir={locale === "ar" ? "rtl" : "ltr"}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="glass mx-auto mt-2 grid max-w-7xl gap-1 rounded-lg p-2 lg:hidden"
            >
              {links.map(([href, key]) => (
                <Link
                  onClick={() => setMobileOpen(false)}
                  key={href}
                  href={href}
                  className="rounded-md px-3 py-3 text-sm text-muted-foreground hover:bg-white/[.06] hover:text-foreground"
                >
                  {t(key)}
                </Link>
              ))}
              <a
                href={telegramUrl}
                target="_blank"
                rel="noreferrer"
                className="rounded-md bg-primary px-3 py-3 text-center text-sm font-semibold text-primary-foreground"
              >
                <Send className="me-2 inline h-4 w-4" />
                {t("nav.telegram")}
              </a>
            </motion.nav>
          ) : null}
        </AnimatePresence>
      </header>
      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} />
    </>
  );
}
