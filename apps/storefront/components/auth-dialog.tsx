"use client";

import * as React from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { api } from "@/lib/api";
import { useAuth, useI18n, useToast } from "@/components/providers";
import { Modal } from "@/components/ui/modal";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function AuthDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { t, locale } = useI18n();
  const { setSession } = useAuth();
  const { success } = useToast();
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");

  const submit = async (mode: "login" | "register", form: HTMLFormElement) => {
    setLoading(true); setError("");
    const data = new FormData(form);
    try {
      const session = mode === "login"
        ? await api.login({ email: String(data.get("email")), password: String(data.get("password")) })
        : await api.register({ email: String(data.get("email")), password: String(data.get("password")), display_name: String(data.get("name") || ""), locale });
      await setSession(session.access_token, session.refresh_token);
      success(mode === "login" ? t("auth.signIn") : t("auth.create"));
      onOpenChange(false);
    } catch (value) { setError(value instanceof Error ? value.message : "error.unexpected"); }
    finally { setLoading(false); }
  };

  return <Modal open={open} onOpenChange={onOpenChange} title={t("auth.signIn")}><Tabs.Root defaultValue="login"><Tabs.List className="grid grid-cols-2 rounded-md bg-white/[.05] p-1"><Tabs.Trigger value="login" className="rounded-md px-3 py-2 text-sm text-muted-foreground data-[state=active]:bg-white/[.08] data-[state=active]:text-foreground">{t("auth.signIn")}</Tabs.Trigger><Tabs.Trigger value="register" className="rounded-md px-3 py-2 text-sm text-muted-foreground data-[state=active]:bg-white/[.08] data-[state=active]:text-foreground">{t("auth.create")}</Tabs.Trigger></Tabs.List><AuthForm value="login" loading={loading} error={error} onSubmit={(form) => void submit("login", form)} t={t} /><AuthForm value="register" register loading={loading} error={error} onSubmit={(form) => void submit("register", form)} t={t} /></Tabs.Root></Modal>;
}

function AuthForm({ value, register, loading, error, onSubmit, t }: { value: string; register?: boolean; loading: boolean; error: string; onSubmit: (form: HTMLFormElement) => void; t: (key: string) => string }) {
  return <Tabs.Content value={value}><form className="mt-4 space-y-3" onSubmit={(event) => { event.preventDefault(); onSubmit(event.currentTarget); }}>{register ? <Input name="name" placeholder={t("auth.name")} /> : null}<Input required name="email" type="email" placeholder={t("auth.email")} /><Input required minLength={12} name="password" type="password" placeholder={t("auth.password")} />{error ? <div className="text-sm text-red-300">{error}</div> : null}<Button className="w-full" disabled={loading}>{loading ? t("common.loading") : t(register ? "auth.create" : "auth.signIn")}</Button></form></Tabs.Content>;
}
