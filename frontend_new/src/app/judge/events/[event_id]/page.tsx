"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft, Star, CheckCircle, Clock, ChevronDown, ChevronUp, Bell, ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEvent,
  getJudgeDashboard,
  getJudgeAssignments,
  listJudges,
  listRounds,
  markNotificationRead,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event, Round, Judge, JudgeDashboard } from "@/types";
import type { JudgeAssignmentDetail } from "@/lib/api";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";

const card: React.CSSProperties = {
  borderRadius: "0.75rem",
  border: "1px solid #222",
  background: "#111",
  padding: "1.5rem",
};

function StatusChip({ status }: { status: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    active: { bg: "rgba(34,197,94,0.12)", color: "#4ade80" },
    upcoming: { bg: "rgba(251,191,36,0.12)", color: "#fbbf24" },
    completed: { bg: "rgba(148,163,184,0.12)", color: "#94a3b8" },
  };
  const c = colors[status] ?? { bg: "rgba(148,163,184,0.12)", color: "#94a3b8" };
  return (
    <span style={{
      padding: "0.2rem 0.6rem", borderRadius: "9999px", fontSize: "0.7rem",
      fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em",
      background: c.bg, color: c.color,
    }}>
      {status}
    </span>
  );
}

type AssignmentByRound = {
  round: Round;
  assignments: JudgeAssignmentDetail[];
};

export default function JudgeEventDashboard() {
  const { event_id } = useParams<{ event_id: string }>();
  const router = useRouter();
  const { profile } = useAuth();

  const [event, setEvent] = useState<Event | null>(null);
  const [dashboard, setDashboard] = useState<JudgeDashboard | null>(null);
  const [assignments, setAssignments] = useState<JudgeAssignmentDetail[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [myJudge, setMyJudge] = useState<Judge | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedRounds, setExpandedRounds] = useState<Set<string>>(new Set());
  const [dismissedNotifs, setDismissedNotifs] = useState<Set<string>>(new Set());

  const fetchAll = useCallback(async () => {
    if (!event_id || !profile) return;
    setLoading(true);
    try {
      const [ev, dash, roundsData] = await Promise.all([
        getEvent(event_id),
        getJudgeDashboard(event_id).catch(() => null),
        listRounds(event_id).catch(() => [] as Round[]),
      ]);
      setEvent(ev);
      setDashboard(dash);
      setRounds(roundsData);

      // Find my judge record
      const judges = await listJudges(event_id).catch(() => [] as Judge[]);
      const me = judges.find(
        (j) => (j.email || "").toLowerCase() === (profile.email || "").toLowerCase()
      );
      setMyJudge(me ?? null);

      if (me) {
        const assgns = await getJudgeAssignments(event_id, me.id).catch(() => [] as JudgeAssignmentDetail[]);
        setAssignments(assgns);
        // Auto-expand rounds that have active assignments
        const activeRoundIds = new Set(
          assgns.filter((a) => !a.already_evaluated && a.submission_id).map((a) => a.round_id)
        );
        setExpandedRounds(activeRoundIds);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [event_id, profile]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const byRound: AssignmentByRound[] = rounds.map((r) => ({
    round: r,
    assignments: assignments.filter((a) => a.round_id === r.id),
  })).filter((r) => r.assignments.length > 0);

  const toggleRound = (id: string) =>
    setExpandedRounds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const dismissNotif = async (id: string) => {
    setDismissedNotifs((prev) => new Set([...prev, id]));
    await markNotificationRead(id).catch(() => null);
  };

  // Build activity log
  const activityLog: Array<{ date: string; label: string }> = [];
  if (myJudge?.created_at) {
    activityLog.push({ date: myJudge.created_at, label: "Invited as judge" });
  }
  if (dashboard?.completed_evaluations) {
    for (const ev of dashboard.completed_evaluations) {
      activityLog.push({
        date: ev.evaluated_at,
        label: `Evaluated ${ev.team_name} — Score: ${ev.score}`,
      });
    }
  }
  activityLog.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const unreadNotifs = (dashboard?.notifications ?? []).filter(
    (n) => !dismissedNotifs.has(n.id)
  );

  const pageWrap: React.CSSProperties = { minHeight: "100vh", background: "#0a0a0a" };
  const main: React.CSSProperties = {
    paddingLeft: "calc(var(--ekam-sb-width, 0px) + 1rem)",
    paddingRight: "1rem",
    paddingTop: "5rem",
    paddingBottom: "3rem",
    maxWidth: "56rem",
    margin: "0 auto",
    transition: "padding-left 0.25s",
  };

  if (loading) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <Sidebar />
        <div style={main}>
          <div className="shimmer" style={{ height: "2rem", width: "16rem", borderRadius: "0.5rem", marginBottom: "1rem" }} />
          <div className="shimmer" style={{ height: "12rem", borderRadius: "0.75rem" }} />
        </div>
      </div>
    );
  }

  if (!event) {
    return (
      <div style={pageWrap}>
        <Navbar />
        <Sidebar />
        <div style={{ ...main, display: "flex", alignItems: "center", justifyContent: "center", height: "80vh" }}>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>Event not found</p>
        </div>
      </div>
    );
  }

  return (
    <div style={pageWrap}>
      <Navbar />
      <Sidebar />
      <div style={main}>
        <button
          onClick={() => router.back()}
          style={{
            marginBottom: "1.5rem", display: "inline-flex", alignItems: "center",
            gap: "0.5rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)",
            background: "transparent", border: "none", cursor: "pointer", padding: 0,
          }}
        >
          <ArrowLeft size={16} /> Back
        </button>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

          {/* Event header */}
          <div style={card}>
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem" }}>
              <div>
                <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>
                  {event.name}
                </h1>
                <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
                  {event.type} · Stage: {event.stage.replace("_", " ")}
                  {myJudge && ` · Judge: ${myJudge.name}`}
                </p>
              </div>
              <StatusChip status={event.status} />
            </div>
          </div>

          {/* Summary stats */}
          {dashboard?.summary && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              {[
                { label: "Assigned", value: dashboard.summary.total_assigned, color: "#6366f1" },
                { label: "Pending", value: dashboard.summary.pending, color: "#f59e0b" },
                { label: "Completed", value: dashboard.summary.completed, color: "#4ade80" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ ...card, textAlign: "center" }}>
                  <p style={{ fontSize: "1.75rem", fontWeight: 900, color, margin: 0 }}>{value}</p>
                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", margin: "0.25rem 0 0" }}>{label}</p>
                </div>
              ))}
            </div>
          )}

          {/* Rounds pipeline */}
          <div style={card}>
            <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem" }}>
              Rounds Pipeline
            </h2>
            {byRound.length === 0 ? (
              <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.35)" }}>No assignments yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {byRound.map(({ round, assignments: rowAssigns }) => {
                  const isExpanded = expandedRounds.has(round.id);
                  const pending = rowAssigns.filter((a) => a.submission_id && !a.already_evaluated).length;
                  return (
                    <div key={round.id} style={{ borderRadius: "0.5rem", border: "1px solid #2a2a2a", overflow: "hidden" }}>
                      <button
                        onClick={() => toggleRound(round.id)}
                        style={{
                          width: "100%", display: "flex", alignItems: "center", gap: "0.75rem",
                          padding: "0.75rem 1rem", background: "#191919", border: "none", cursor: "pointer",
                          textAlign: "left",
                        }}
                      >
                        <span style={{ flex: 1, fontWeight: 600, color: "#fff", fontSize: "0.875rem" }}>
                          {round.name}
                        </span>
                        {pending > 0 && (
                          <span style={{
                            fontSize: "0.65rem", fontWeight: 700, padding: "0.15rem 0.5rem",
                            borderRadius: "9999px", background: "rgba(245,158,11,0.15)", color: "#f59e0b",
                          }}>
                            {pending} pending
                          </span>
                        )}
                        <StatusChip status={round.status} />
                        {isExpanded ? <ChevronUp size={14} color="rgba(255,255,255,0.4)" /> : <ChevronDown size={14} color="rgba(255,255,255,0.4)" />}
                      </button>

                      {isExpanded && (
                        <div style={{ padding: "0.75rem 1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                          {rowAssigns.map((a) => {
                            const evaluated = a.already_evaluated;
                            const hasSubmission = !!a.submission_id;
                            return (
                              <div key={a.assignment_id} style={{
                                display: "flex", alignItems: "center", gap: "0.75rem",
                                padding: "0.625rem 0.75rem", borderRadius: "0.375rem",
                                background: "rgba(255,255,255,0.03)",
                              }}>
                                <div style={{ flex: 1 }}>
                                  <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>
                                    {a.team_name}
                                  </p>
                                  <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>
                                    {!hasSubmission ? "No submission yet" : evaluated ? "Evaluated ✓" : "Needs grading"}
                                  </p>
                                </div>
                                {evaluated && (
                                  <span style={{ fontSize: "0.8rem", color: "#4ade80", fontWeight: 700 }}>
                                    <CheckCircle size={14} style={{ verticalAlign: "middle" }} />
                                  </span>
                                )}
                                {!evaluated && hasSubmission && (
                                  <span style={{
                                    width: "8px", height: "8px", borderRadius: "9999px",
                                    background: "#f59e0b", flexShrink: 0,
                                  }} />
                                )}
                                {hasSubmission && (
                                  <Link
                                    href={`/judge/evaluate/${a.submission_id}?team=${encodeURIComponent(a.team_name)}&round=${encodeURIComponent(a.round_name)}`}
                                    style={{
                                      padding: "0.375rem 0.75rem", borderRadius: "0.375rem",
                                      fontSize: "0.75rem", fontWeight: 600,
                                      background: evaluated ? "rgba(148,163,184,0.1)" : "rgba(232,80,58,0.15)",
                                      color: evaluated ? "#94a3b8" : "#e8503a",
                                      border: `1px solid ${evaluated ? "rgba(148,163,184,0.15)" : "rgba(232,80,58,0.2)"}`,
                                      textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "0.25rem",
                                    }}
                                  >
                                    {evaluated ? "View Score" : "Grade →"}
                                    <ExternalLink size={11} />
                                  </Link>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Activity log */}
          {activityLog.length > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem" }}>
                Activity Log
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
                {activityLog.map((entry, i) => (
                  <div key={i} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                    <div style={{
                      flexShrink: 0, marginTop: "0.25rem", width: "8px", height: "8px",
                      borderRadius: "9999px", background: "#e8503a",
                    }} />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.75)", margin: 0 }}>{entry.label}</p>
                      <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>
                        {new Date(entry.date).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notifications */}
          {unreadNotifs.length > 0 && (
            <div style={card}>
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: "0 0 1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Bell size={16} color="#e8503a" /> Notifications
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {unreadNotifs.map((n) => (
                  <div key={n.id} style={{
                    display: "flex", alignItems: "center", gap: "0.75rem",
                    padding: "0.75rem 1rem", borderRadius: "0.5rem",
                    background: "rgba(232,80,58,0.08)", border: "1px solid rgba(232,80,58,0.15)",
                  }}>
                    <Clock size={14} color="#e8503a" />
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", margin: 0 }}>{n.title}</p>
                      <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", margin: 0 }}>{n.message}</p>
                    </div>
                    <button
                      onClick={() => dismissNotif(n.id)}
                      style={{ background: "transparent", border: "none", color: "rgba(255,255,255,0.3)", cursor: "pointer", fontSize: "0.75rem" }}
                    >
                      Dismiss
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
