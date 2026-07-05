"use client";

export type RavenEvent = {
  event_id: string;
  event_type: string;
  topic: string;
  audience: "public" | "customer" | "admin" | "internal";
  cache_tags: string[];
  payload: Record<string, unknown>;
};

type Listener = (event: RavenEvent) => void;

class EventHub {
  private listeners = new Set<Listener>();
  private controller: AbortController | null = null;
  private token: string | null = null;
  private lastEventId: string | null = null;
  private running = false;
  private seenEventIds = new Set<string>();

  setToken(token: string | null) {
    if (this.token === token) return;
    this.token = token;
    this.controller?.abort();
    this.controller = null;
    if (this.listeners.size) this.start();
  }

  subscribe(listener: Listener) {
    this.listeners.add(listener);
    this.start();
    return () => {
      this.listeners.delete(listener);
      if (!this.listeners.size) this.controller?.abort();
    };
  }

  private start() {
    if (this.running || typeof window === "undefined") return;
    this.running = true;
    void this.run().finally(() => { this.running = false; });
  }

  private async run() {
    let retryMs = 1000;
    while (this.listeners.size) {
      this.controller = new AbortController();
      try {
        const headers: Record<string, string> = { Accept: "text/event-stream" };
        if (this.token) headers.Authorization = `Bearer ${this.token}`;
        if (this.lastEventId) headers["Last-Event-ID"] = this.lastEventId;
        const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
        const response = await fetch(`${base}/events/stream`, { headers, cache: "no-store", signal: this.controller.signal });
        if (!response.ok || !response.body) throw new Error(`event_stream_${response.status}`);
        retryMs = 1000;
        await this.read(response.body);
      } catch (error) {
        if (this.controller.signal.aborted) continue;
        await new Promise((resolve) => window.setTimeout(resolve, retryMs));
        retryMs = Math.min(30000, retryMs * 2);
      }
    }
  }

  private async read(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (this.listeners.size) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) this.dispatch(frame);
    }
  }

  private dispatch(frame: string) {
    let data = "";
    for (const line of frame.split("\n")) {
      if (line.startsWith("id:")) this.lastEventId = line.slice(3).trim();
      if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (!data) return;
    const event = JSON.parse(data) as RavenEvent;
    if (this.seenEventIds.has(event.event_id)) return;
    this.seenEventIds.add(event.event_id);
    if (this.seenEventIds.size > 1000) this.seenEventIds.delete(this.seenEventIds.values().next().value!);
    for (const listener of this.listeners) listener(event);
  }
}

export const eventHub = new EventHub();
