import { useEffect, useRef } from "react";

/**
 * Re-run `callback` periodically and when the tab regains focus/visibility, so
 * pages reflect server-side changes (pipeline advances, new submissions, score
 * updates) without the user manually refreshing. Polling pauses while the tab
 * is hidden to avoid wasted requests.
 */
export function useAutoRefresh(callback: () => void, intervalMs = 12000): void {
  const cbRef = useRef(callback);
  useEffect(() => {
    cbRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const runIfVisible = () => {
      if (document.visibilityState === "visible") cbRef.current();
    };
    const onFocus = () => cbRef.current();

    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", runIfVisible);
    const id = setInterval(runIfVisible, intervalMs);

    return () => {
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", runIfVisible);
      clearInterval(id);
    };
  }, [intervalMs]);
}
