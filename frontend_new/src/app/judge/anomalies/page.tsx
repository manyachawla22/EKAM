"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { listMyAnomalies, resolveMyAnomaly } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useEventStream } from "@/lib/useEventStream";
import type { MyAnomaly } from "@/types";
import Button from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import Navbar from "@/components/layout/Navbar";

const pageWrap: React.CSSProperties = { minHeight: "100vh", background: "#0a0a0a" };
const container: React.CSSProperties = {
  maxWidth: "44rem",
  margin: "0 auto",
  padding: "6rem 1.5rem 3rem",
};
const card: React.CSSProperties = {
  borderRadius: "0.75rem",
  border: "1px solid #222",
  background: "#111",
  padding: "1.5rem",
};

function severityLabel(s: number): { label: string; color: string } {
  if (s >= 0.66) return { label: "High", color: "#f87171" };
  if (s >= 0.33) return { label: "Medium", color: "#fbbf24" };
  return { label: "Low", color: "#60a5fa" };
}

/**
 * A judge's PRIVATE anomalies page: lists every evaluation of theirs that was
 * flagged, and lets them fix the per-criterion scores inline. Access is enforced
 * server-side (`GET/POST /anomalies/mine*` only ever return/accept anomalies
 * whose evaluation belongs to the authenticated judge), so this page can only
 * ever show the caller their own anomalies.
 */
export default function MyAnomaliesPage() {
  // Judges authenticate via magic link / OTP → EKAM JWT, so they have a `profile`
  // but never a Firebase `user`. Gate on `profile` (like every other judge page);
  // gating on `user` would always read null and wrongly show the login prompt.
  const { profile, loading: authLoading } = useAuth();
  const [items, setItems] = useState<MyAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"open" | "resolved" | "all">("open");
  const [edits, setEdits] = useState<Record<string, Record<string, number>>>({});
  const [feedbacks, setFeedbacks] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const data = await listMyAnomalies();
      setItems(data);
      // Seed the editable score state from each anomaly's current rubric.
      setEdits((prev) => {
        const next = { ...prev };
        for (const a of data) {
          if (!next[a.id]) {
            next[a.id] = Object.fromEntries(a.rubric.map((r) => [r.id, r.my_score]));
          }
        }
        return next;
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load your anomalies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!profile) {
      setLoading(false);
      return;
    }
    fetchAll();
  }, [authLoading, profile, fetchAll]);

  // Live push: refetch when a new anomaly is flagged for this judge.
  useEventStream(["anomaly"], fetchAll);

  const filtered = useMemo(
    () =>
      items.filter((a) =>
        filter === "all" ? true : filter === "resolved" ? a.is_resolved : !a.is_resolved
      ),
    [items, filter]
  );

  const openCount = items.filter((a) => !a.is_resolved).length;

  const setScore = (anomalyId: string, critId: string, value: number, max: number) => {
    const clamped = Math.max(0, Math.min(max, Number.isFinite(value) ? value : 0));
    setEdits((p) => ({ ...p, [anomalyId]: { ...(p[anomalyId] || {}), [critId]: clamped } }));
  };

  const handleSave = async (a: MyAnomaly) => {
    const rubric_scores = edits[a.id] || {};
    setSavingId(a.id);
    try {
      await resolveMyAnomaly(a.id, {
        rubric_scores,
        feedback: feedbacks[a.id] || undefined,
      });
      toast.success("Score updated — anomaly resolved.");
      await fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div style={pageWrap}>
      <Navbar />
      <div style={container}>
        <div style={{ marginBottom: "1.5rem" }}>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <ShieldAlert size={24} color="#e8503a" />
            My Flagged Evaluations
          </h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
            Evaluations of yours that our automated review flagged. Adjust the
            scores below to resolve each one. Only you can see this page.
          </p>
        </div>

        {/* Filter tabs */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
          {(["open", "resolved", "all"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "0.35rem 0.85rem",
                borderRadius: "9999px",
                border: "1px solid",
                borderColor: filter === f ? "#e8503a" : "#222",
                background: filter === f ? "rgba(232,80,58,0.12)" : "transparent",
                color: filter === f ? "#e8503a" : "rgba(255,255,255,0.55)",
                fontSize: "0.78rem",
                fontWeight: 600,
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {f}
              {f === "open" && openCount > 0 ? ` (${openCount})` : ""}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="shimmer" style={{ height: "12rem", borderRadius: "0.75rem" }} />
        ) : !profile ? (
          <div style={{ ...card, textAlign: "center", color: "rgba(255,255,255,0.5)" }}>
            Please log in as a judge to view your flagged evaluations.
          </div>
        ) : filtered.length === 0 ? (
          <div
            style={{
              ...card,
              textAlign: "center",
              color: "rgba(255,255,255,0.45)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "0.75rem",
            }}
          >
            <CheckCircle size={32} color="#4ade80" />
            {filter === "open"
              ? "No open anomalies — you're all clear."
              : "Nothing to show here."}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {filtered.map((a) => {
              const sev = severityLabel(a.severity);
              const myEdits = edits[a.id] || {};
              const editedTotal = a.rubric.reduce(
                (sum, r) => sum + (myEdits[r.id] ?? r.my_score),
                0
              );
              return (
                <motion.div
                  key={a.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={card}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: "0.75rem",
                    }}
                  >
                    <div>
                      <p style={{ margin: 0, fontSize: "1rem", fontWeight: 700, color: "#fff" }}>
                        {a.team_name || "Team"}{" "}
                        <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 500 }}>
                          · {a.round_name}
                        </span>
                      </p>
                      <p
                        style={{
                          margin: "0.3rem 0 0",
                          fontSize: "0.8rem",
                          color: "rgba(255,255,255,0.55)",
                          lineHeight: 1.45,
                        }}
                      >
                        {a.description}
                      </p>
                    </div>
                    <span
                      style={{
                        flexShrink: 0,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        fontSize: "0.7rem",
                        fontWeight: 700,
                        color: a.is_resolved ? "#4ade80" : sev.color,
                        border: `1px solid ${a.is_resolved ? "#4ade8055" : sev.color + "55"}`,
                        borderRadius: "9999px",
                        padding: "0.15rem 0.55rem",
                      }}
                    >
                      {a.is_resolved ? (
                        <>
                          <CheckCircle size={11} /> Resolved
                        </>
                      ) : (
                        <>
                          <AlertTriangle size={11} /> {sev.label}
                        </>
                      )}
                    </span>
                  </div>

                  {/* Score context */}
                  <div
                    style={{
                      display: "flex",
                      gap: "1.5rem",
                      margin: "0.85rem 0",
                      fontSize: "0.8rem",
                    }}
                  >
                    <span style={{ color: "rgba(255,255,255,0.45)" }}>
                      Your total:{" "}
                      <strong style={{ color: "#fff" }}>
                        {a.my_total_score?.toFixed(1) ?? "—"}
                      </strong>
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.45)" }}>
                      Panel average:{" "}
                      <strong style={{ color: "#fff" }}>
                        {a.panel_average?.toFixed(1) ?? "—"}
                      </strong>
                    </span>
                  </div>

                  {/* Per-criterion editing */}
                  {a.rubric.length === 0 ? (
                    <p style={{ fontSize: "0.8rem", color: "rgba(250,204,21,0.8)" }}>
                      This round has no rubric criteria to edit.
                    </p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                      {a.rubric.map((r) => {
                        const val = myEdits[r.id] ?? r.my_score;
                        return (
                          <div
                            key={r.id}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "0.75rem",
                              borderRadius: "0.5rem",
                              border: "1px solid #1e1e1e",
                              background: "rgba(255,255,255,0.02)",
                              padding: "0.6rem 0.75rem",
                            }}
                          >
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#fff" }}>
                                {r.name}
                              </span>
                              <span
                                style={{
                                  marginLeft: "0.4rem",
                                  fontSize: "0.72rem",
                                  color: "rgba(255,255,255,0.4)",
                                }}
                              >
                                max {r.max_score}
                              </span>
                            </div>
                            <input
                              type="range"
                              min={0}
                              max={r.max_score}
                              step={1}
                              value={val}
                              disabled={a.is_resolved}
                              onChange={(e) => setScore(a.id, r.id, Number(e.target.value), r.max_score)}
                              style={{ flex: 1, accentColor: "#e8503a", cursor: a.is_resolved ? "default" : "pointer" }}
                            />
                            <input
                              type="number"
                              min={0}
                              max={r.max_score}
                              value={val}
                              disabled={a.is_resolved}
                              onChange={(e) => setScore(a.id, r.id, Number(e.target.value), r.max_score)}
                              style={{
                                width: "3.5rem",
                                textAlign: "center",
                                borderRadius: "0.4rem",
                                border: "1px solid #222",
                                background: "#0d0d0d",
                                color: "#fff",
                                padding: "0.3rem",
                                fontSize: "0.85rem",
                              }}
                            />
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {!a.is_resolved && a.rubric.length > 0 && (
                    <>
                      <div style={{ marginTop: "0.85rem" }}>
                        <Textarea
                          label="Note (optional)"
                          value={feedbacks[a.id] || ""}
                          onChange={(e) =>
                            setFeedbacks((p) => ({ ...p, [a.id]: e.target.value }))
                          }
                          placeholder="Optional note about your revised scoring…"
                          fullWidth
                        />
                      </div>
                      <div
                        style={{
                          marginTop: "0.85rem",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: "0.75rem",
                        }}
                      >
                        <span style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.6)" }}>
                          New total:{" "}
                          <strong style={{ color: "#e8503a" }}>{editedTotal}</strong>
                        </span>
                        <Button
                          variant="primary"
                          onClick={() => handleSave(a)}
                          loading={savingId === a.id}
                        >
                          <CheckCircle size={15} /> Save &amp; Resolve
                        </Button>
                      </div>
                    </>
                  )}
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
