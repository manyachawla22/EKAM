"use client";

import { useEffect, useRef } from "react";

interface TurnstileApi {
  render: (el: HTMLElement, opts: { sitekey: string; callback: (t: string) => void; "expired-callback"?: () => void; theme?: string }) => string;
  reset: (id?: string) => void;
}

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY || "";
const SCRIPT_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js";

/**
 * Cloudflare Turnstile widget. Renders only when NEXT_PUBLIC_TURNSTILE_SITE_KEY
 * is set; otherwise it no-ops (captcha disabled in dev/demo — the backend also
 * skips verification when its secret is unset, so the two stay in sync).
 */
export default function TurnstileWidget({ onToken }: { onToken: (token: string | null) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);

  useEffect(() => {
    if (!SITE_KEY) return;

    const renderWidget = () => {
      if (!ref.current || !window.turnstile) return;
      widgetId.current = window.turnstile.render(ref.current, {
        sitekey: SITE_KEY,
        theme: "dark",
        callback: (t) => onToken(t),
        "expired-callback": () => onToken(null),
      });
    };

    if (window.turnstile) {
      renderWidget();
    } else if (!document.querySelector(`script[src="${SCRIPT_SRC}"]`)) {
      const s = document.createElement("script");
      s.src = SCRIPT_SRC;
      s.async = true;
      s.defer = true;
      s.onload = renderWidget;
      document.head.appendChild(s);
    } else {
      const iv = setInterval(() => {
        if (window.turnstile) {
          clearInterval(iv);
          renderWidget();
        }
      }, 200);
      return () => clearInterval(iv);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!SITE_KEY) return null;
  return <div ref={ref} className="my-2" />;
}
