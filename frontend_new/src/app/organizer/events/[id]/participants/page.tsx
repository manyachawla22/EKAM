"use client";

export const dynamic = "force-dynamic";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Users, Search, Trash2, Download } from "lucide-react";
import { toast } from "sonner";
import {
  listParticipants, deleteParticipant, uploadParticipantsCsv,
  downloadParticipantsSampleCsv,
  listTeams, listRounds, listSubmissions, getEvaluations,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Participant, Team, Round, Submission } from "@/types";
import CsvUploadButton from "@/components/ui/CsvUploadButton";
import Modal from "@/components/ui/Modal";

interface ParticipantDetail {
  participant: Participant;
  team: Team | null;
  submissions: Array<{ round: Round; submission: Submission | null; score: number | null }>;
}

export default function ParticipantsPage() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchFocus, setSearchFocus] = useState(false);
  const [detailModal, setDetailModal] = useState<ParticipantDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const openDetail = async (p: Participant) => {
    if (!id) return;
    setDetailLoading(true);
    setDetailModal({ participant: p, team: null, submissions: [] });
    try {
      const [teams, rounds] = await Promise.all([
        listTeams(id).catch(() => [] as Team[]),
        listRounds(id).catch(() => [] as Round[]),
      ]);
      const team = teams.find((t) => t.members?.some((m) => m.participant_id === p.id)) ?? null;
      const subs: ParticipantDetail["submissions"] = [];
      for (const round of rounds) {
        const roundSubs = await listSubmissions(round.id).catch(() => [] as Submission[]);
        const teamSub = team ? roundSubs.find((s) => s.team_id === team.id) ?? null : null;
        let score: number | null = null;
        if (teamSub) {
          const evals = await getEvaluations(teamSub.id).catch(() => []);
          const scores = evals.map((e) => e.total_score ?? e.score ?? 0).filter((s) => s > 0);
          if (scores.length > 0) score = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
        }
        subs.push({ round, submission: teamSub, score });
      }
      setDetailModal({ participant: p, team, submissions: subs });
    } catch {
      // keep whatever we loaded
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async (participantId: string) => {
    if (!id || !window.confirm("Remove this participant from the event?")) return;
    try {
      await deleteParticipant(id, participantId);
      setParticipants((prev) => prev.filter((p) => p.id !== participantId));
      toast.success("Participant removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to remove participant");
    }
  };

  const fetchParticipants = useCallback(() => {
    if (!id) return;
    return listParticipants(id)
      .then(setParticipants)
      .catch((err: Error) =>
        toast.error(err.message || "Failed to load participants")
      );
  }, [id]);

  useEffect(() => {
    if (authLoading) return;
    if (!user || !id) {
      setLoading(false);
      return;
    }
    fetchParticipants()?.finally(() => setLoading(false));
  }, [id, authLoading, user, fetchParticipants]);

  const filtered = participants.filter((p) => {
    const q = search.toLowerCase();
    return (
      p.name?.toLowerCase().includes(q) ||
      p.email?.toLowerCase().includes(q) ||
      p.institution?.toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ maxWidth: "80rem", margin: "0 auto", width: "100%" }}>
      <div
        style={{
          marginBottom: "2rem",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 900,
              fontStyle: "italic",
              color: "#fff",
              margin: 0,
            }}
          >
            Participants
          </h1>
          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.875rem",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            {participants.length} registered
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <button
            onClick={async () => {
              try {
                await downloadParticipantsSampleCsv(id);
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "Download failed");
              }
            }}
            disabled={!id}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.5rem 0.85rem",
              borderRadius: "0.5rem",
              border: "1px solid #222",
              background: "transparent",
              color: "rgba(255,255,255,0.7)",
              fontSize: "0.8rem",
              fontWeight: 600,
              cursor: id ? "pointer" : "not-allowed",
            }}
            title="Download a CSV template matching this event's registration fields"
          >
            <Download size={14} /> Sample CSV
          </button>
          <CsvUploadButton
            label="Bulk Import CSV"
            disabled={!id}
            onUpload={(file) => uploadParticipantsCsv(id, file)}
            onUploaded={fetchParticipants}
          />
        </div>
      </div>

      <div
        style={{
          marginBottom: "1.5rem",
          position: "relative",
          maxWidth: "24rem",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "0.875rem",
            top: "50%",
            transform: "translateY(-50%)",
            pointerEvents: "none",
            color: "rgba(255,255,255,0.3)",
            display: "flex",
          }}
        >
          <Search size={16} />
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onFocus={() => setSearchFocus(true)}
          onBlur={() => setSearchFocus(false)}
          placeholder="Search participants..."
          style={{
            width: "100%",
            borderRadius: "0.5rem",
            border: `1px solid ${searchFocus ? "#e8503a" : "#222"}`,
            background: "#111",
            padding: "0.625rem 1rem 0.625rem 2.5rem",
            fontSize: "0.875rem",
            color: "#fff",
            outline: "none",
            transition: "all 0.2s",
            fontFamily: "inherit",
            boxSizing: "border-box",
          }}
        />
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="shimmer"
              style={{ height: "3.5rem", borderRadius: "0.75rem" }}
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
            padding: "5rem 0",
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              height: "4rem",
              width: "4rem",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "1rem",
              background: "#111",
              border: "1px solid #222",
            }}
          >
            <Users size={32} color="rgba(255,255,255,0.2)" />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)" }}>
            {search ? "No participants match your search" : "No participants yet"}
          </p>
        </div>
      ) : (
        <div
          style={{
            borderRadius: "0.75rem",
            border: "1px solid #222",
            background: "#111",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr auto",
              gap: "1rem",
              borderBottom: "1px solid #222",
              padding: "0.75rem 1.25rem",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.3)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>Participant</span>
            <span>Institution</span>
            <span>Gender</span>
            <span>Skills</span>
            <span>Joined</span>
            <span />
          </div>
          {filtered.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr auto",
                gap: "1rem",
                alignItems: "center",
                borderBottom: i === filtered.length - 1 ? "none" : "1px solid rgba(34,34,34,0.5)",
                padding: "0.875rem 1.25rem",
                transition: "background 0.2s",
              }}
            >
              <button
                onClick={() => openDetail(p)}
                style={{ minWidth: 0, textAlign: "left", background: "transparent", border: "none", cursor: "pointer", padding: 0 }}
              >
                <p
                  style={{
                    fontWeight: 500,
                    color: "#fff",
                    fontSize: "0.875rem",
                    margin: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    textDecoration: "underline",
                    textDecorationColor: "rgba(255,255,255,0.15)",
                    textUnderlineOffset: "2px",
                  }}
                >
                  {p.name || "—"}
                </p>
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.4)",
                    margin: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p.email}
                </p>
              </button>
              <span
                style={{
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.6)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.institution || "—"}
              </span>
              <span
                style={{
                  fontSize: "0.875rem",
                  color: "rgba(255,255,255,0.6)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.gender || "—"}
              </span>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "rgba(255,255,255,0.5)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {p.skills && p.skills.length > 0 ? p.skills.join(", ") : "—"}
              </span>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "rgba(255,255,255,0.4)",
                }}
              >
                {p.created_at
                  ? new Date(p.created_at).toLocaleDateString()
                  : "—"}
              </span>
              <button
                onClick={() => handleDelete(p.id)}
                title="Remove participant"
                style={{
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: "transparent", border: "none", cursor: "pointer",
                  color: "rgba(255,255,255,0.2)", padding: "0.25rem",
                  borderRadius: "0.375rem", transition: "color 0.2s",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(255,255,255,0.2)")}
              >
                <Trash2 size={15} />
              </button>
            </motion.div>
          ))}
        </div>
      )}

      <Modal
        open={!!detailModal}
        onClose={() => setDetailModal(null)}
        title={detailModal ? `Participant: ${detailModal.participant.name || detailModal.participant.email}` : ""}
        size="lg"
      >
        {detailModal && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Profile */}
            <div style={{ padding: "1rem", borderRadius: "0.5rem", background: "#0d0d0d" }}>
              <p style={{ fontSize: "0.875rem", color: "#fff", fontWeight: 600, margin: "0 0 0.25rem" }}>
                {detailModal.participant.email}
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginTop: "0.5rem", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>
                {detailModal.participant.institution && <span>Institution: {detailModal.participant.institution}</span>}
                {detailModal.participant.age && <span>Age: {detailModal.participant.age}</span>}
                {detailModal.participant.phone && <span>Phone: {detailModal.participant.phone}</span>}
              </div>
              {(detailModal.participant.skills ?? []).length > 0 && (
                <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                  {(detailModal.participant.skills ?? []).map((s) => (
                    <span key={s} style={{ fontSize: "0.7rem", padding: "0.15rem 0.5rem", borderRadius: "9999px", background: "rgba(99,102,241,0.15)", color: "#818cf8" }}>{s}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Registration details (tailored form answers) */}
            {(() => {
              const data = detailModal.participant.registration_data;
              if (!data || typeof data !== "object") return null;
              const SKIP = new Set(["full_name", "name", "email"]);
              const entries = Object.entries(data).filter(
                ([k, v]) => !SKIP.has(k.toLowerCase()) && v !== null && v !== undefined && v !== "",
              );
              if (entries.length === 0) return null;
              const fmtKey = (k: string) =>
                k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              const fmtVal = (v: unknown) => (Array.isArray(v) ? v.join(", ") : String(v));
              return (
                <div>
                  <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Registration Details</p>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "0.4rem 1rem", padding: "0.75rem 1rem", borderRadius: "0.5rem", background: "#0d0d0d" }}>
                    {entries.map(([k, v]) => (
                      <div key={k} style={{ display: "contents" }}>
                        <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)" }}>{fmtKey(k)}</span>
                        <span style={{ fontSize: "0.8rem", color: "#fff", wordBreak: "break-word" }}>{fmtVal(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* Team */}
            <div>
              <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Team</p>
              {detailLoading ? (
                <div className="shimmer" style={{ height: "2.5rem", borderRadius: "0.375rem" }} />
              ) : detailModal.team ? (
                <p style={{ fontSize: "0.875rem", color: "#fff", margin: 0 }}>
                  {detailModal.team.name} · {detailModal.team.members?.length ?? 0} members
                </p>
              ) : (
                <p style={{ fontSize: "0.875rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>Not assigned to a team</p>
              )}
            </div>

            {/* Submission history */}
            {detailModal.submissions.length > 0 && (
              <div>
                <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Submission History</p>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
                  {detailModal.submissions.map(({ round, submission, score }) => (
                    <div key={round.id} style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.5rem 0.75rem", borderRadius: "0.375rem", background: "#0d0d0d" }}>
                      <span style={{ flex: 1, fontSize: "0.8rem", color: "#fff" }}>{round.name}</span>
                      {submission ? (
                        <>
                          <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)" }}>
                            {submission.submitted_at ? new Date(submission.submitted_at).toLocaleDateString() : "Submitted"}
                          </span>
                          {score !== null && <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "#4ade80" }}>{score}/100</span>}
                        </>
                      ) : (
                        <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)" }}>No submission</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Activity log */}
            <div>
              <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.5rem" }}>Participant Log</p>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {detailModal.participant.created_at && (
                  <div style={{ display: "flex", gap: "0.75rem" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#e8503a", flexShrink: 0, marginTop: "0.3rem" }} />
                    <div>
                      <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>Registered for event</p>
                      <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>{new Date(detailModal.participant.created_at).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</p>
                    </div>
                  </div>
                )}
                {detailModal.team && (
                  <div style={{ display: "flex", gap: "0.75rem" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#6366f1", flexShrink: 0, marginTop: "0.3rem" }} />
                    <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>Assigned to {detailModal.team.name}</p>
                  </div>
                )}
                {detailModal.submissions.filter((s) => s.submission).map(({ round, submission, score }) => (
                  <div key={round.id} style={{ display: "flex", gap: "0.75rem" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "9999px", background: "#4ade80", flexShrink: 0, marginTop: "0.3rem" }} />
                    <div>
                      <p style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", margin: 0 }}>
                        Submitted for {round.name}{score !== null ? ` · Score: ${score}/100` : ""}
                      </p>
                      {submission?.submitted_at && <p style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", margin: 0 }}>{new Date(submission.submitted_at).toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
