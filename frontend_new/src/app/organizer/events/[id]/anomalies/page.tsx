"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle, Clock, Filter } from "lucide-react";
import { toast } from "sonner";
import { listAnomalies, resolveAnomaly } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useEventStream } from "@/lib/useEventStream";
import type { Anomaly, AnomalyType } from "@/types";
import Button from "@/components/ui/Button";

const TYPE_LABEL: Record<AnomalyType, string> = {
  score_variance: "Score Variance",
  bias_detected: "Bias Detected",
  time_anomaly: "Time Anomaly",
};

const TYPE_TINT: Record<AnomalyType, { background: string; color: string; border: string }> = {
  score_variance: {
    background: "rgba(234,179,8,0.12)",
    color: "#fbbf24",
    border: "rgba(234,179,8,0.3)",
  },
  bias_detected: {
    background: "rgba(239,68,68,0.12)",
    color: "#f87171",
    border: "rgba(239,68,68,0.3)",
  },
  time_anomaly: {
    background: "rgba(99,102,241,0.12)",
    color: "#a5b4fc",
    border: "rgba(99,102,241,0.3)",
  },
};

function severityLabel(s: number): { label: string; color: string } {
  if (s >= 0.75) return { label: "High", color: "#f87171" };
  if (s >= 0.4) return { label: "Medium", color: "#fbbf24" };
  return { label: "Low", color: "#a5b4fc" };
}

// A tiny inline SVG bar showing severity (0-1).
function SeverityBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const lbl = severityLabel(value);
  return (
    <div style={{ width: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.65rem",
          color: "rgba(255,255,255,0.4)",
          marginBottom: "0.25rem",
        }}
      >
        <span>Severity</span>
        <span style={{ color: lbl.color, fontWeight: 600 }}>
          {lbl.label} · {value.toFixed(2)}
        </span>
      </div>
      <div
        style={{
          height: "0.45rem",
          width: "100%",
          background: "#222",
          borderRadius: "9999px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: lbl.color,
            transition: "width 0.3s",
          }}
        />
      </div>
    </div>
  );
}

export default function AnomaliesPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [items, setItems] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"open" | "resolved" | "all">("open");
  const [resolving, setResolving] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    try {
      const data = await listAnomalies(id);
      setItems(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load anomalies");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setLoading(false);
      return;
    }
    fetchAll();
  }, [authLoading, user, fetchAll]);

  // Live push: refetch when an anomaly is flagged for this event.
  useEventStream(["anomaly"], fetchAll);

  const filtered = items.filter((a) => {
    if (filter === "open") return !a.is_resolved;
    if (filter === "resolved") return a.is_resolved;
    return true;
  });

  const openCount = items.filter((a) => !a.is_resolved).length;
  const resolvedCount = items.length - openCount;

  const handleResolve = async (a: Anomaly) => {
    if (!id) return;
    setResolving(a.id);
    try {
      await resolveAnomaly(id, a.id);
      toast.success("Anomaly resolved");
      await fetchAll();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to resolve");
    } finally {
      setResolving(null);
    }
  };

  const card: React.CSSProperties = {
    borderRadius: "0.75rem",
    border: "1px solid #222",
    background: "#111",
    padding: "1.25rem",
  };

  return (
    <div style={{ maxWidth: "60rem", margin: "0 auto", width: "100%" }}>
      <div style={{ marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.5rem",
            fontWeight: 900,
            fontStyle: "italic",
            color: "#fff",
            margin: 0,
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
          }}
        >
          <AlertTriangle size={22} color="#fbbf24" />
          Anomalies
        </h1>
        <p
          style={{
            marginTop: "0.25rem",
            fontSize: "0.875rem",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          Flagged evaluations — score variance between judges, suspected bias,
          and timing irregularities. Resolve once investigated.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "0.4rem",
          marginBottom: "1.5rem",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <Filter size={14} color="rgba(255,255,255,0.4)" />
        {(
          [
            { key: "open" as const, label: "Open", count: openCount },
            { key: "resolved" as const, label: "Resolved", count: resolvedCount },
            { key: "all" as const, label: "All", count: items.length },
          ]
        ).map((t) => {
          const active = filter === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setFilter(t.key)}
              style={{
                background: active ? "rgba(232,80,58,0.1)" : "transparent",
                color: active ? "#e8503a" : "rgba(255,255,255,0.6)",
                border: "1px solid",
                borderColor: active ? "rgba(232,80,58,0.25)" : "#222",
                padding: "0.35rem 0.75rem",
                borderRadius: "0.5rem",
                fontSize: "0.8rem",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              {t.label}{" "}
              <span
                style={{
                  fontSize: "0.7rem",
                  color: active ? "#e8503a" : "rgba(255,255,255,0.35)",
                  marginLeft: "0.25rem",
                }}
              >
                ({t.count})
              </span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "6rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.75rem",
            padding: "4rem 0",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              height: "3.5rem",
              width: "3.5rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "1rem",
              background: "#111",
              border: "1px solid #222",
            }}
          >
            <CheckCircle size={26} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>
            {filter === "open"
              ? "No open anomalies — evaluations look healthy."
              : filter === "resolved"
              ? "No resolved anomalies yet."
              : "No anomalies detected yet."}
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {filtered.map((a, i) => {
            const tint = TYPE_TINT[a.anomaly_type];
            return (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                style={card}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: "1rem",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ flex: 1, minWidth: "16rem" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        flexWrap: "wrap",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "0.7rem",
                          fontWeight: 600,
                          padding: "0.2rem 0.55rem",
                          borderRadius: "9999px",
                          background: tint.background,
                          color: tint.color,
                          border: `1px solid ${tint.border}`,
                          textTransform: "uppercase",
                          letterSpacing: "0.02em",
                        }}
                      >
                        {TYPE_LABEL[a.anomaly_type] || a.anomaly_type}
                      </span>
                      {a.is_resolved && (
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.25rem",
                            fontSize: "0.7rem",
                            color: "#4ade80",
                          }}
                        >
                          <CheckCircle size={12} /> Resolved
                        </span>
                      )}
                    </div>
                    <p
                      style={{
                        marginTop: "0.5rem",
                        marginBottom: 0,
                        fontSize: "0.875rem",
                        color: "rgba(255,255,255,0.85)",
                        lineHeight: 1.5,
                      }}
                    >
                      {a.description}
                    </p>
                    <div
                      style={{
                        marginTop: "0.45rem",
                        display: "flex",
                        gap: "0.75rem",
                        fontSize: "0.7rem",
                        color: "rgba(255,255,255,0.4)",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "0.25rem",
                        }}
                      >
                        <Clock size={11} />
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                      <span
                        style={{
                          fontFamily: "ui-monospace, monospace",
                          background: "rgba(255,255,255,0.04)",
                          padding: "0.1rem 0.4rem",
                          borderRadius: "0.25rem",
                        }}
                      >
                        eval: {String(a.evaluation_id).slice(0, 8)}…
                      </span>
                    </div>
                    <div style={{ marginTop: "0.75rem" }}>
                      <SeverityBar value={a.severity} />
                    </div>
                  </div>
                  {!a.is_resolved && (
                    <Button
                      size="sm"
                      variant="primary"
                      loading={resolving === a.id}
                      onClick={() => handleResolve(a)}
                    >
                      <CheckCircle size={14} /> Resolve
                    </Button>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
