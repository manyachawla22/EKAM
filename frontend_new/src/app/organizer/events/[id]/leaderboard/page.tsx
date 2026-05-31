"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Award, Trophy, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import {
  listRounds,
  getLeaderboard,
  listTeams,
  getEvent,
  proposeStageTransition,
} from "@/lib/api";
import type { Round, Submission, Team, Event, EventStage } from "@/types";
import Button from "@/components/ui/Button";

const card: React.CSSProperties = {
  borderRadius: "0.75rem",
  border: "1px solid #222",
  background: "#111",
  padding: "1.5rem",
};

const inputBase: React.CSSProperties = {
  borderRadius: "0.5rem",
  border: "1px solid #222",
  background: "#0d0d0d",
  padding: "0.5rem 0.75rem",
  fontSize: "0.875rem",
  color: "#fff",
  outline: "none",
};

const STAGES: EventStage[] = ["submission", "evaluation", "results", "completed"];

export default function LeaderboardPage() {
  const { id } = useParams<{ id: string }>();

  const [event, setEvent] = useState<Event | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedRound, setSelectedRound] = useState<string>("");
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loadingBoard, setLoadingBoard] = useState(false);
  const [loading, setLoading] = useState(true);

  const [cutoffScore, setCutoffScore] = useState(60);
  const [targetStage, setTargetStage] = useState<EventStage>("results");
  const [proposing, setProposing] = useState(false);

  const fetchBase = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [ev, roundsData, teamsData] = await Promise.all([
        getEvent(id),
        listRounds(id).catch(() => [] as Round[]),
        listTeams(id).catch(() => [] as Team[]),
      ]);
      setEvent(ev);
      setRounds(roundsData);
      setTeams(teamsData);
      if (roundsData.length > 0) setSelectedRound(roundsData[0].id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchBase(); }, [fetchBase]);

  useEffect(() => {
    if (!selectedRound) return;
    setLoadingBoard(true);
    getLeaderboard(selectedRound)
      .then(setSubmissions)
      .catch(() => setSubmissions([]))
      .finally(() => setLoadingBoard(false));
  }, [selectedRound]);

  const teamName = (teamId: string) =>
    teams.find((t) => t.id === teamId)?.name ?? `Team ${teamId.slice(0, 6)}`;

  const handlePropose = async () => {
    if (!id) return;
    setProposing(true);
    try {
      const result = await proposeStageTransition(id, targetStage, cutoffScore);
      toast.success(`${result.message} Approval created.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to propose");
    } finally {
      setProposing(false);
    }
  };

  const pageWrap: React.CSSProperties = {
    minHeight: "100vh",
    background: "#0a0a0a",
    paddingLeft: "calc(var(--ekam-sb-width, 15rem) + 1.5rem)",
    paddingRight: "1.5rem",
    paddingTop: "5.5rem",
    paddingBottom: "3rem",
    transition: "padding-left 0.25s",
  };

  if (loading) {
    return (
      <div style={pageWrap}>
        <div className="shimmer" style={{ height: "2rem", width: "14rem", borderRadius: "0.5rem", marginBottom: "1rem" }} />
        <div className="shimmer" style={{ height: "16rem", borderRadius: "0.75rem" }} />
      </div>
    );
  }

  return (
    <div style={pageWrap}>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ maxWidth: "52rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Award size={24} color="#e8503a" />
          <h1 style={{ fontSize: "1.5rem", fontWeight: 900, fontStyle: "italic", color: "#fff", margin: 0 }}>
            Leaderboard
          </h1>
        </div>

        {/* Round tabs */}
        {rounds.length > 0 && (
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {rounds.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedRound(r.id)}
                style={{
                  padding: "0.4rem 1rem", borderRadius: "0.5rem", border: "1px solid",
                  fontSize: "0.8rem", fontWeight: 600, cursor: "pointer",
                  background: selectedRound === r.id ? "rgba(232,80,58,0.15)" : "transparent",
                  borderColor: selectedRound === r.id ? "rgba(232,80,58,0.3)" : "#333",
                  color: selectedRound === r.id ? "#e8503a" : "rgba(255,255,255,0.6)",
                }}
              >
                {r.name}
              </button>
            ))}
          </div>
        )}

        {/* Table */}
        <div style={card}>
          {loadingBoard ? (
            <div className="shimmer" style={{ height: "12rem", borderRadius: "0.5rem" }} />
          ) : submissions.length === 0 ? (
            <p style={{ textAlign: "center", color: "rgba(255,255,255,0.35)", fontSize: "0.875rem" }}>
              No submissions yet for this round.
            </p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #222" }}>
                  {["Rank", "Team", "Score", "Panel Avg", "Status"].map((h) => (
                    <th key={h} style={{ padding: "0.625rem 0.75rem", textAlign: "left", color: "rgba(255,255,255,0.4)", fontWeight: 600, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub, idx) => {
                  const aboveCutoff = (sub.final_score ?? 0) >= cutoffScore;
                  const isCutoffLine = idx > 0 && (submissions[idx - 1].final_score ?? 0) >= cutoffScore && !aboveCutoff;
                  return (
                    <>
                      {isCutoffLine && (
                        <tr key="cutoff-line">
                          <td colSpan={5} style={{ padding: "0.25rem 0" }}>
                            <div style={{ borderTop: "1px dashed rgba(251,191,36,0.5)", position: "relative" }}>
                              <span style={{
                                position: "absolute", top: "-0.6rem", left: "0.5rem",
                                fontSize: "0.65rem", color: "#fbbf24", background: "#111", padding: "0 0.3rem",
                              }}>
                                ┄ Cutoff Line ({cutoffScore}) ┄
                              </span>
                            </div>
                          </td>
                        </tr>
                      )}
                      <tr key={sub.id} style={{ borderBottom: "1px solid #1a1a1a", opacity: aboveCutoff ? 1 : 0.6 }}>
                        <td style={{ padding: "0.75rem", fontWeight: 700, color: idx < 3 ? "#e8503a" : "#fff" }}>
                          #{idx + 1}
                          {idx === 0 && " 🥇"}
                          {idx === 1 && " 🥈"}
                          {idx === 2 && " 🥉"}
                        </td>
                        <td style={{ padding: "0.75rem", color: "#fff", fontWeight: 500 }}>
                          {teamName(sub.team_id)}
                        </td>
                        <td style={{ padding: "0.75rem", color: "#fff", fontWeight: 700 }}>
                          {sub.final_score ?? "—"}
                        </td>
                        <td style={{ padding: "0.75rem", color: "rgba(255,255,255,0.6)" }}>
                          {sub.panel_average?.toFixed(1) ?? "—"}
                        </td>
                        <td style={{ padding: "0.75rem" }}>
                          <span style={{
                            padding: "0.15rem 0.5rem", borderRadius: "9999px", fontSize: "0.7rem", fontWeight: 600,
                            background: aboveCutoff ? "rgba(34,197,94,0.12)" : "rgba(239,68,68,0.12)",
                            color: aboveCutoff ? "#4ade80" : "#f87171",
                          }}>
                            {sub.status}
                          </span>
                        </td>
                      </tr>
                    </>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Stage transition panel */}
        {event?.stage === "evaluation" && (
          <div style={{ ...card, border: "1px solid rgba(232,80,58,0.2)", background: "rgba(232,80,58,0.05)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
              <Trophy size={18} color="#e8503a" />
              <h2 style={{ fontSize: "1rem", fontWeight: 700, color: "#fff", margin: 0 }}>
                Propose Stage Transition
              </h2>
            </div>
            <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.5)", marginBottom: "1.25rem" }}>
              Teams above the cutoff score will advance. This creates an approval request.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
              <div>
                <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>
                  Cutoff Score
                </label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={cutoffScore}
                  onChange={(e) => setCutoffScore(Number(e.target.value))}
                  style={{ ...inputBase, width: "100%" }}
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: "0.375rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.6)" }}>
                  Advance to Stage
                </label>
                <select
                  value={targetStage}
                  onChange={(e) => setTargetStage(e.target.value as EventStage)}
                  style={{ ...inputBase, width: "100%" }}
                >
                  {STAGES.map((s) => (
                    <option key={s} value={s}>{s.replace("_", " ")}</option>
                  ))}
                </select>
              </div>
            </div>
            <Button variant="primary" onClick={handlePropose} loading={proposing}>
              <ChevronRight size={16} /> Propose Transition
            </Button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
