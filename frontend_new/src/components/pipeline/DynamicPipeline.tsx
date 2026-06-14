"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { getPipelineState } from "@/lib/api";
import { useAutoRefresh } from "@/lib/useAutoRefresh";
import { useEventStream } from "@/lib/useEventStream";
import type { PipelineState } from "@/types";

/**
 * The event's dynamic, per-round pipeline rendered in the node/connector style:
 * a row of status dots with labels beneath and connecting lines, adapting to the
 * number of rounds. Done = green + check, active = accent with a pulse, upcoming
 * = grey. Horizontally scrollable for events with many round steps.
 */
export default function DynamicPipeline({ eventId }: { eventId: string }) {
  const [state, setState] = useState<PipelineState | null>(null);

  const load = useCallback(() => {
    if (!eventId) return;
    getPipelineState(eventId)
      .then(setState)
      .catch(() => setState(null));
  }, [eventId]);

  useEffect(() => {
    load();
  }, [load]);

  // Live push: a pipeline advance or an approval action reloads the pipeline
  // instantly. The poll below is now just a slow safety net.
  useEventStream(["pipeline", "approval"], load);

  // Slow polling fallback for dropped streams / sessions without an EKAM JWT.
  useAutoRefresh(load, 60000);

  if (!state || state.steps.length === 0) return null;

  const activeLabel = state.steps.find((s) => s.status === "active")?.label;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", overflowX: "auto", paddingBottom: "0.5rem" }}>
        {state.steps.map((step, i) => {
          const isPast = step.status === "done";
          const isActive = step.status === "active";
          const dotColor = isPast ? "#4ade80" : isActive ? "#e8503a" : "#333";
          const borderColor = isPast ? "#4ade80" : isActive ? "#e8503a" : "#555";
          return (
            <div
              key={step.id}
              style={{
                display: "flex",
                alignItems: "flex-start",
                flex: i < state.steps.length - 1 ? "1 0 auto" : "0 0 auto",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.375rem", minWidth: "64px" }}>
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {isActive && (
                    <div
                      style={{
                        position: "absolute",
                        width: "24px",
                        height: "24px",
                        borderRadius: "9999px",
                        border: "2px solid #e8503a",
                        opacity: 0.5,
                        animation: "pulse 2s infinite",
                      }}
                    />
                  )}
                  <div
                    style={{
                      width: "14px",
                      height: "14px",
                      borderRadius: "9999px",
                      flexShrink: 0,
                      background: dotColor,
                      border: `2px solid ${borderColor}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {isPast && <CheckCircle2 size={8} color="#0a0a0a" />}
                  </div>
                </div>
                <span
                  style={{
                    fontSize: "0.6rem",
                    fontWeight: isActive ? 700 : 500,
                    color: isActive ? "#e8503a" : isPast ? "#4ade80" : "rgba(255,255,255,0.3)",
                    textAlign: "center",
                    maxWidth: "72px",
                    lineHeight: 1.2,
                  }}
                >
                  {step.label}
                </span>
              </div>
              {i < state.steps.length - 1 && (
                <div
                  style={{
                    flex: 1,
                    minWidth: "12px",
                    height: "2px",
                    background: isPast ? "#4ade80" : "#333",
                    margin: "6px 0.25rem 0",
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
      {(activeLabel || state.ready_to_advance) && (
        <p style={{ marginTop: "0.5rem", fontSize: "0.72rem", color: state.ready_to_advance ? "#fbbf24" : "rgba(255,255,255,0.45)" }}>
          {state.ready_to_advance
            ? `✓ "${activeLabel}" is complete — a transition has been proposed for approval.`
            : `Current step: ${activeLabel}`}
        </p>
      )}
    </div>
  );
}
