import { useEffect, useRef } from "react";
import { API_BASE, getEkamToken } from "./api";

export interface StreamMessage {
  type: string; // "notification" | "approval" | "anomaly" | "pipeline" | ...
  event_id?: string | null;
  [key: string]: unknown;
}

type Listener = { allowed: Set<string>; cb: (msg: StreamMessage) => void };

/**
 * Live push from the backend SSE stream (`GET /stream`), companion to the
 * polling `useAutoRefresh`.
 *
 * CRITICAL: there is exactly ONE shared `EventSource` per browser tab, multiplexed
 * across every component that calls this hook — NOT one connection per hook. Browsers
 * cap concurrent connections per host (~6 over HTTP/1.1) and each `EventSource` holds
 * one open for its whole lifetime. A page renders several stream consumers
 * (NotificationsBell, DynamicPipeline, ApprovalsPanel, …); opening one connection
 * each — times several open tabs — blows past the 6-connection limit, and every other
 * request (dashboard load, submit preference, file upload) then queues behind the
 * saturated pool and appears to hang. One connection per tab keeps that budget free.
 *
 * The connection is also closed while the tab is hidden (and reopened on focus),
 * and a synthetic `__resync__` is delivered on every (re)connect so a backgrounded
 * tab refetches the moment it becomes visible instead of waiting for a push.
 *
 * The token is passed as a query param because `EventSource` can't set headers.
 */

const listeners = new Set<Listener>();
let es: EventSource | null = null;
let esToken: string | null = null;
let globalsBound = false;

function dispatch(msg: StreamMessage): void {
  listeners.forEach((l) => {
    if (l.allowed.size === 0 || l.allowed.has(msg.type)) l.cb(msg);
  });
}

function resyncAll(): void {
  // Bypasses the per-listener type filter: every subscriber refetches on
  // (re)connect so a tab that just regained focus catches up immediately.
  listeners.forEach((l) => l.cb({ type: "__resync__" }));
}

function openStream(): void {
  if (typeof window === "undefined" || es) return;
  const token = getEkamToken();
  if (!token) return; // not logged in → polling fallback covers it
  esToken = token;
  es = new EventSource(`${API_BASE}/stream?token=${encodeURIComponent(token)}`);
  es.onopen = () => resyncAll();
  es.onmessage = (e: MessageEvent) => {
    try {
      dispatch(JSON.parse(e.data) as StreamMessage);
    } catch {
      // Ignore keepalive comments / unparseable frames.
    }
  };
  es.onerror = () => {
    // Native EventSource auto-reconnects; also fires on normal close.
  };
}

function closeStream(): void {
  if (es) {
    es.close();
    es = null;
    esToken = null;
  }
}

function syncStream(): void {
  if (typeof document === "undefined") return;
  // Don't hold a connection for a hidden tab or when nobody is listening.
  if (document.visibilityState === "hidden" || listeners.size === 0) {
    closeStream();
    return;
  }
  // Re-open if the auth token changed since we connected (e.g. re-login in tab).
  if (es && esToken !== getEkamToken()) closeStream();
  openStream();
}

export function useEventStream(
  types: string[],
  onEvent: (msg: StreamMessage) => void
): void {
  const cbRef = useRef(onEvent);
  cbRef.current = onEvent;

  // Stable key so the effect re-runs only when the set of types changes.
  const typesKey = types.join(",");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const listener: Listener = {
      allowed: new Set(typesKey ? typesKey.split(",") : []),
      cb: (msg) => cbRef.current(msg),
    };
    listeners.add(listener);

    if (!globalsBound) {
      document.addEventListener("visibilitychange", syncStream);
      window.addEventListener("focus", syncStream);
      globalsBound = true;
    }

    syncStream(); // open the shared stream if visible & authed

    return () => {
      listeners.delete(listener);
      if (listeners.size === 0) closeStream();
    };
  }, [typesKey]);
}
