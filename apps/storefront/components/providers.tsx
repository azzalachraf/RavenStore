"use client";

import * as React from "react";
import * as Toast from "@radix-ui/react-toast";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import { api } from "@/lib/api";
import { eventHub } from "@/lib/events";
import { formatMessage, type Locale, uiMessages } from "@/lib/i18n";
import type { User } from "@/lib/types";

type I18nContextValue = { locale: Locale; setLocale: (locale: Locale) => void; t: (key: string, params?: Record<string, string | number>) => string; dir: "ltr" | "rtl" };
const I18nContext = React.createContext<I18nContextValue | null>(null);

type AuthContextValue = { token: string | null; user: User | null; setSession: (token: string, refreshToken: string) => Promise<void>; signOut: () => void; refreshUser: () => Promise<void> };
const AuthContext = React.createContext<AuthContextValue | null>(null);

type ToastTone = "success" | "error" | "info";
const ToastContext = React.createContext<{ success: (title: string) => void; error: (title: string) => void; info: (title: string) => void } | null>(null);

export function Providers({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = React.useState<Locale>("en");
  const [remote, setRemote] = React.useState<Record<string, string>>({});
  const [token, setToken] = React.useState<string | null>(null);
  const [refreshToken, setRefreshToken] = React.useState<string | null>(null);
  const [user, setUser] = React.useState<User | null>(null);
  const [toasts, setToasts] = React.useState<Array<{ id: string; title: string; tone: ToastTone }>>([]);

  React.useEffect(() => {
    const storedLocale = window.localStorage.getItem("raven_locale") as Locale | null;
    const storedToken = window.sessionStorage.getItem("raven_access_token");
    const storedRefresh = window.sessionStorage.getItem("raven_refresh_token");
    if (storedLocale === "ar" || storedLocale === "en") setLocaleState(storedLocale);
    if (storedToken) setToken(storedToken);
    if (storedRefresh) setRefreshToken(storedRefresh);
  }, []);

  React.useEffect(() => {
    void api.translations(locale, 0).then(setRemote).catch(() => setRemote({}));
    document.documentElement.lang = locale;
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
  }, [locale]);

  const refreshUser = React.useCallback(async () => {
    if (!token) { setUser(null); return; }
    try { setUser(await api.me(token)); } catch { setUser(null); }
  }, [token]);

  React.useEffect(() => { void refreshUser(); }, [refreshUser]);

  React.useEffect(() => {
    eventHub.setToken(token);
    return eventHub.subscribe((event) => {
      if (!event.cache_tags.includes("translations")) return;
      void api.translations(locale, 0).then(setRemote).catch(() => undefined);
    });
  }, [locale, token]);

  const setLocale = React.useCallback((value: Locale) => {
    window.localStorage.setItem("raven_locale", value);
    setLocaleState(value);
  }, []);

  const t = React.useCallback((key: string, params?: Record<string, string | number>) => formatMessage(remote[key] ?? uiMessages[locale][key] ?? uiMessages.en[key] ?? key, params), [locale, remote]);
  const setSession = React.useCallback(async (value: string, nextRefreshToken: string) => {
    window.sessionStorage.setItem("raven_access_token", value);
    window.sessionStorage.setItem("raven_refresh_token", nextRefreshToken);
    setToken(value);
    setRefreshToken(nextRefreshToken);
    setUser(await api.me(value));
  }, []);
  const signOut = React.useCallback(() => {
    if (refreshToken) void api.logout(refreshToken).catch(() => undefined);
    window.sessionStorage.removeItem("raven_access_token");
    window.sessionStorage.removeItem("raven_refresh_token");
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  }, [refreshToken]);

  React.useEffect(() => {
    if (!refreshToken) return;
    const rotate = async () => {
      try {
        const next = await api.refresh(refreshToken);
        window.sessionStorage.setItem("raven_access_token", next.access_token);
        window.sessionStorage.setItem("raven_refresh_token", next.refresh_token);
        setToken(next.access_token);
        setRefreshToken(next.refresh_token);
      } catch {
        signOut();
      }
    };
    const timer = window.setTimeout(() => void rotate(), 10 * 60 * 1000);
    return () => window.clearTimeout(timer);
  }, [refreshToken, signOut]);
  const pushToast = React.useCallback((tone: ToastTone, title: string) => {
    const id = crypto.randomUUID();
    setToasts((items) => [...items, { id, title, tone }]);
    window.setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 3200);
  }, []);
  const success = React.useCallback((title: string) => pushToast("success", title), [pushToast]);
  const error = React.useCallback((title: string) => pushToast("error", title), [pushToast]);
  const info = React.useCallback((title: string) => pushToast("info", title), [pushToast]);

  return (
    <I18nContext.Provider value={{ locale, setLocale, t, dir: locale === "ar" ? "rtl" : "ltr" }}>
      <AuthContext.Provider value={{ token, user, setSession, signOut, refreshUser }}>
        <ToastContext.Provider value={{ success, error, info }}>
          <Toast.Provider swipeDirection="right">
            {children}
            <Toast.Viewport className="fixed bottom-4 right-4 z-[100] flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
            <AnimatePresence>
              {toasts.map((item) => (
                <Toast.Root key={item.id} asChild open>
                  <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className="glass flex items-center gap-3 rounded-lg p-4">
                    {item.tone === "success" ? <CheckCircle2 className="h-5 w-5 text-emerald-300" /> : item.tone === "error" ? <AlertCircle className="h-5 w-5 text-red-300" /> : <Info className="h-5 w-5 text-cyan-300" />}
                    <Toast.Title className="text-sm font-medium">{item.title}</Toast.Title>
                  </motion.div>
                </Toast.Root>
              ))}
            </AnimatePresence>
          </Toast.Provider>
        </ToastContext.Provider>
      </AuthContext.Provider>
    </I18nContext.Provider>
  );
}

export function useI18n() { const value = React.useContext(I18nContext); if (!value) throw new Error("I18n provider missing"); return value; }
export function useAuth() { const value = React.useContext(AuthContext); if (!value) throw new Error("Auth provider missing"); return value; }
export function useToast() { const value = React.useContext(ToastContext); if (!value) throw new Error("Toast provider missing"); return value; }
