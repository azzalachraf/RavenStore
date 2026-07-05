"use client";

import * as React from "react";
import { eventHub } from "@/lib/events";

export function useLiveResource<T>(loader: () => Promise<T>, intervalMs = 60000, tags: string[] = []) {
  const [data, setData] = React.useState<T | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);
  const loaderRef = React.useRef(loader);
  loaderRef.current = loader;
  const refresh = React.useCallback(async () => {
    try { setData(await loaderRef.current()); setError(null); } catch (value) { setError(value as Error); } finally { setLoading(false); }
  }, []);
  React.useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), intervalMs);
    let debounce: number | undefined;
    const unsubscribe = eventHub.subscribe((event) => {
      if (tags.length && !event.cache_tags.some((tag) => tags.includes(tag))) return;
      window.clearTimeout(debounce);
      debounce = window.setTimeout(() => void refresh(), 75);
    });
    return () => { window.clearInterval(timer); window.clearTimeout(debounce); unsubscribe(); };
  }, [intervalMs, refresh, tags.join("|")]);
  return { data, loading, error, refresh };
}
