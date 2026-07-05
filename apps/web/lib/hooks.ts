"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ravenApi, type ApiError } from "@/lib/api";
import { eventHub } from "@/lib/events";

type LiveState<T> = {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  refresh: () => Promise<void>;
};

export function useLiveResource<T>(loader: () => Promise<T>, intervalMs = 60000, tags: string[] = []): LiveState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const refresh = useCallback(async () => {
    try {
      const next = await loaderRef.current();
      setData(next);
      setError(null);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), intervalMs);
    let debounce: number | undefined;
    const unsubscribe = eventHub.subscribe((event) => {
      if (tags.length && !event.cache_tags.some((tag) => tags.includes(tag))) return;
      window.clearTimeout(debounce);
      debounce = window.setTimeout(() => void refresh(), 75);
    });
    return () => { window.clearInterval(id); window.clearTimeout(debounce); unsubscribe(); };
  }, [intervalMs, refresh, tags.join("|")]);

  return { data, loading, error, refresh };
}

export function useAdminToken() {
  const [token, setTokenState] = useState<string | null>(null);
  useEffect(() => {
    const stored = window.localStorage.getItem("raven_admin_token");
    if (stored) {
      ravenApi.setToken(stored);
      eventHub.setToken(stored);
      setTokenState(stored);
    }
  }, []);
  const setToken = useCallback((value: string | null) => {
    if (value) window.localStorage.setItem("raven_admin_token", value);
    else window.localStorage.removeItem("raven_admin_token");
    ravenApi.setToken(value);
    eventHub.setToken(value);
    setTokenState(value);
  }, []);
  return useMemo(() => ({ token, setToken }), [token, setToken]);
}
