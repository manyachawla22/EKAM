"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Star, ChevronRight, CheckCircle, Clock, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { getMe, listEvents, listJudges, getJudgeAssignments } from "@/lib/api";
import type { JudgeAssignmentDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Event } from "@/types";
import Navbar from "@/components/layout/Navbar";
import { EventStatusBadge } from "@/components/ui/Badge";
import TeamDetailModal from "@/components/ui/TeamDetailModal";
import RefereeBracketCard from "@/components/bracket/RefereeBracketCard";

interface EventSection {
  event: Event;
  judgeId: string;
  assignments: JudgeAssignmentDetail[];
}

// Group assignments by round
function groupByRound(assignments: JudgeAssignmentDetail[]) {
  const map = new Map<string, { round_name: string; round_status: string; teams: JudgeAssignmentDetail[] }>();
  for (const a of assignments) {
    if (!map.has(a.round_id)) {
      map.set(a.round_id, { round_name: a.round_name, round_status: a.round_status, teams: [] });
    }
    map.get(a.round_id)!.teams.push(a);
  }
  return Array.from(map.values());
}

function SubmissionChip({ status, evaluated }: { status: string | null; evaluated: boolean }) {
  if (!status) {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: "0.3rem",
        fontSize: "0.7rem", fontWeight: 600, padding: "0.2rem 0.6rem",
        borderRadius: "9999px", background: "#1a1a1a", color: "rgba(255,255,255,0.3)",
        border: "1px solid #222",
      }}>
        <Clock size={10} /> No submission
      </span>
    );
  }
  if (evaluated) {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: "0.3rem",
        fontSize: "0.7rem", fontWeight: 600, padding: "0.2rem 0.6rem",
        borderRadius: "9999px", background: "rgba(34,197,94,0.1)", color: "#4ade80",
        border: "1px solid rgba(34,197,94,0.2)",
      }}>
        <CheckCircle size={10} /> Evaluated
      </span>
    );
  }
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: "0.3rem",
      fontSize: "0.7rem", fontWeight: 600, padding: "0.2rem 0.6rem",
      borderRadius: "9999px", background: "rgba(232,80,58,0.1)", color: "#e8503a",
      border: "1px solid rgba(232,80,58,0.2)",
    }}>
      <AlertCircle size={10} /> Needs grading
    </span>
  );
}

export default function JudgeAssignmentsPage() {
  const { profile, loading: authLoading } = useAuth();
  const [sections, setSections] = useState<EventSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [teamModal, setTeamModal] = useState<{ eventId: string; teamId: string; teamName: string } | null>(null);

  // Redirect event-scoped judges to their dashboard
  useEffect(() => {
    if (!authLoading && profile?.event_id) {
      window.location.replace(`/judge/events/${profile.event_id}`);
    }
  }, [authLoading, profile]);

  useEffect(() => {
    if (authLoading) return;
    if (!profile) {
      setLoading(false);
      return;
    }
    if (profile.event_id) return; // will redirect above

    (async () => {
      try {
        const me = await getMe();
        const myEmail = (me.email || "").toLowerCase();
        const events = await listEvents().catch(() => []);

        const built: EventSection[] = [];

        for (const ev of events) {
          // Find this judge's record in the event (matched by email)
          const eventJudges = await listJudges(ev.id).catch(() => []);
          const myRecord = eventJudges.find(
            (j) => (j.email || "").toLowerCase() === myEmail
          );
          if (!myRecord) continue;

          // Fetch detailed team assignments for this judge
          const assignments = await getJudgeAssignments(ev.id, myRecord.id).catch(() => []);
          built.push({ event: ev, judgeId: myRecord.id, assignments });
        }

        setSections(built);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load assignments");
      } finally {
        setLoading(false);
      }
    })();
  }, [authLoading, profile]);

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a" }}>
      <Navbar />
      <div style={{ maxWidth: "56rem", margin: "0 auto", padding: "6rem 1.5rem 3rem" }}>
        <div style={{ marginBottom: "2rem" }}>
          <h1 style={{ fontSize: "1.875rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>
            My Assignments
          </h1>
          <p style={{ marginTop: "0.25rem", fontSize: "0.875rem", color: "rgba(255,255,255,0.4)" }}>
            Teams you&apos;re assigned to grade
          </p>
        </div>

        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="shimmer" style={{ height: "8rem", borderRadius: "0.75rem" }} />
            ))}
          </div>
        ) : sections.length === 0 ? (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            gap: "1rem", padding: "5rem 0", textAlign: "center",
          }}>
            <div style={{
              display: "flex", height: "4rem", width: "4rem", alignItems: "center",
              justifyContent: "center", borderRadius: "1rem", background: "#111", border: "1px solid #222",
            }}>
              <Star size={32} color="rgba(255,255,255,0.2)" />
            </div>
            <p style={{ color: "rgba(255,255,255,0.4)", margin: 0 }}>No assignments yet</p>
            <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.25)", maxWidth: "26rem", margin: 0 }}>
              An organizer needs to add you to an event using your email ({profile?.email}) before assignments appear here.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {sections.map(({ event, assignments }, si) => {
              // Bracket rounds are scored through the referee bracket card below,
              // not via a submission — exclude them from the submission rows so the
              // judge isn't shown "awaiting submission" for a live match.
              const submissionAssignments = assignments.filter((a) => !a.is_bracket);
              const hasBracket = assignments.some((a) => a.is_bracket);
              const rounds = groupByRound(submissionAssignments);
              const pendingCount = submissionAssignments.filter(
                (a) => a.submission_id && !a.already_evaluated
              ).length;

              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: si * 0.08 }}
                  style={{ borderRadius: "0.75rem", border: "1px solid #222", background: "#111", overflow: "hidden" }}
                >
                  {/* Event header */}
                  <div style={{
                    padding: "1rem 1.25rem",
                    borderBottom: "1px solid #1a1a1a",
                    display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <div style={{
                        display: "flex", height: "2rem", width: "2rem", alignItems: "center",
                        justifyContent: "center", borderRadius: "0.5rem",
                        background: "rgba(168,85,247,0.15)", color: "#c084fc", flexShrink: 0,
                      }}>
                        <Star size={14} />
                      </div>
                      <span style={{ fontWeight: 700, color: "#fff", fontSize: "1rem" }}>{event.name}</span>
                      <EventStatusBadge status={event.status} />
                    </div>
                    {pendingCount > 0 && (
                      <span style={{
                        fontSize: "0.75rem", fontWeight: 600, padding: "0.2rem 0.6rem",
                        borderRadius: "9999px", background: "rgba(232,80,58,0.15)", color: "#e8503a",
                        border: "1px solid rgba(232,80,58,0.3)",
                      }}>
                        {pendingCount} pending
                      </span>
                    )}
                  </div>

                  {/* Rounds + teams */}
                  {rounds.length === 0 ? (
                    hasBracket ? null : (
                    <div style={{ padding: "1.25rem", color: "rgba(255,255,255,0.3)", fontSize: "0.875rem" }}>
                      No team assignments yet for this event.
                    </div>
                    )
                  ) : (
                    rounds.map((round, ri) => (
                      <div key={round.round_name + ri}>
                        {/* Round label */}
                        <div style={{
                          padding: "0.5rem 1.25rem",
                          background: "rgba(255,255,255,0.02)",
                          borderTop: ri > 0 ? "1px solid #1a1a1a" : undefined,
                          display: "flex", alignItems: "center", gap: "0.5rem",
                        }}>
                          <span style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "rgba(255,255,255,0.3)" }}>
                            {round.round_name}
                          </span>
                          <span style={{
                            fontSize: "0.65rem", padding: "0.1rem 0.4rem", borderRadius: "9999px",
                            background: "#1a1a1a", color: "rgba(255,255,255,0.3)", border: "1px solid #222",
                          }}>
                            {round.round_status}
                          </span>
                        </div>

                        {/* Team rows */}
                        {round.teams.map((a, ti) => (
                          <div
                            key={a.assignment_id}
                            style={{
                              display: "flex", alignItems: "center", gap: "1rem",
                              padding: "0.875rem 1.25rem",
                              borderTop: "1px solid #1a1a1a",
                              background: ti % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
                            }}
                          >
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <button
                                onClick={() => setTeamModal({ eventId: event.id, teamId: a.team_id, teamName: a.team_name })}
                                style={{
                                  background: "transparent", border: "none", cursor: "pointer",
                                  padding: 0, textAlign: "left",
                                  fontWeight: 600, color: "#fff", fontSize: "0.9rem",
                                  textDecoration: "underline", textDecorationColor: "rgba(255,255,255,0.15)",
                                  textUnderlineOffset: "3px",
                                }}
                                onMouseEnter={(e) => (e.currentTarget.style.color = "#e8503a")}
                                onMouseLeave={(e) => (e.currentTarget.style.color = "#fff")}
                              >
                                {a.team_name}
                              </button>
                              <div style={{ marginTop: "0.3rem" }}>
                                <SubmissionChip status={a.submission_status} evaluated={a.already_evaluated} />
                              </div>
                            </div>

                            {a.submission_id ? (
                              <Link
                                href={`/judge/evaluate/${a.submission_id}`}
                                style={{
                                  display: "inline-flex", alignItems: "center", gap: "0.25rem",
                                  fontSize: "0.8rem", fontWeight: 600,
                                  color: a.already_evaluated ? "rgba(255,255,255,0.3)" : "#e8503a",
                                  textDecoration: "none", whiteSpace: "nowrap",
                                }}
                              >
                                {a.already_evaluated ? "View score" : "Grade"}
                                <ChevronRight size={14} />
                              </Link>
                            ) : (
                              <span style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.2)" }}>
                                Awaiting submission
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    ))
                  )}

                  {/* Tournament referee: score the bracket matches (renders only
                      when this event has a bracket). */}
                  <div style={{ padding: "0 1.25rem 1.25rem" }}>
                    <RefereeBracketCard eventId={event.id} />
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {teamModal && (
        <TeamDetailModal
          open={!!teamModal}
          onClose={() => setTeamModal(null)}
          eventId={teamModal.eventId}
          teamId={teamModal.teamId}
          teamName={teamModal.teamName}
        />
      )}
    </div>
  );
}
