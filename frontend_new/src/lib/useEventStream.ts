import { useEffect, useRef } from "react";
import { API_BASE, getEkamToken } from "./api";

export interface StreamMessage {
  type: string; // "notification" | "approval" | "anomaly" | "pipeline"
  event_id?: string | null;
  [key: string]: unknown;
}

/**
 * Subscribe to the backend SSE stream (`GET /stream`) and invoke `onEvent` when
 * a message whose `type` is in `types` arrives. This is the live-push companion
 * to `useAutoRefresh`: pages keep a slow polling fallback, but react instantly
 * to pushed signals (new notification, approval, anomaly, pipeline advance).
 *
 * The token is passed as a query param because `EventSource` can't set an
 * `Authorization` header. Native `EventSource` auto-reconnects on transient
 * drops. If no token is available (not logged in) the stream is simply not
 * opened and the polling fallback covers it.
 */
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
    const token = getEkamToken();
    if (!token) return; // fall back to polling for sessions without an EKAM JWT

    const allowed = new Set(typesKey ? typesKey.split(",") : []);
    const url = `${API_BASE}/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.onmessage = (e: MessageEvent) => {
      try {
        const msg = JSON.parse(e.data) as StreamMessage;
        if (allowed.size === 0 || allowed.has(msg.type)) {
          cbRef.current(msg);
        }
      } catch {
        // Ignore keepalive comments / unparseable frames.
      }
    };

    es.onerror = () => {
      // EventSource retries automatically; nothing to do. Errors also fire on
      // normal close during navigation.
    };

    return () => es.close();
  }, [typesKey]);
}
